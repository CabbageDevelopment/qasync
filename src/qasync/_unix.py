"""
UNIX specific qasync functionality.

Copyright (c) 2018 Gerard Marull-Paretas <gerard@teslabs.com>
Copyright (c) 2014 Mark Harviston <mark.harviston@gmail.com>
Copyright (c) 2014 Arve Knudsen <arve.knudsen@gmail.com>

BSD License
"""

import asyncio
import collections
import itertools
import selectors

from . import QtCore, _fileno, with_logger

EVENT_READ = 1 << 0
EVENT_WRITE = 1 << 1

# Qt5/Qt6 compatibility
NotifierEnum = getattr(QtCore.QSocketNotifier, "Type", QtCore.QSocketNotifier)


class _SelectorMapping(collections.abc.Mapping):
    """Mapping of file objects to selector keys."""

    def __init__(self, selector):
        self._selector = selector

    def __len__(self):
        return len(self._selector._fd_to_key)

    def __getitem__(self, fileobj):
        try:
            fd = self._selector._fileobj_lookup(fileobj)
            return self._selector._fd_to_key[fd]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None

    def __iter__(self):
        return iter(self._selector._fd_to_key)


@with_logger
class _Selector(selectors.BaseSelector):
    def __init__(self, parent, qtparent=None):
        # this maps file descriptors to keys
        self._fd_to_key = {}
        # read-only mapping returned by get_map()
        self.__map = _SelectorMapping(self)
        self.__read_notifiers = {}
        self.__write_notifiers = {}
        self.__parent = parent
        self.__qtparent = qtparent

    def select(self, *args, **kwargs):
        """Implement abstract method even though we don't need it."""
        raise NotImplementedError

    def _fileobj_lookup(self, fileobj):
        """Return a file descriptor from a file object.

        This wraps _fileno() to do an exhaustive search in case
        the object is invalid but we still have it in our map.  This
        is used by unregister() so we can unregister an object that
        was previously registered even if it is closed.  It is also
        used by _SelectorMapping.
        """
        try:
            return _fileno(fileobj)
        except ValueError:
            # Do an exhaustive search.
            for key in self._fd_to_key.values():
                if key.fileobj is fileobj:
                    return key.fd
            # Raise ValueError after all.
            raise

    def register(self, fileobj, events, data=None):
        if (not events) or (events & ~(EVENT_READ | EVENT_WRITE)):
            raise ValueError("Invalid events: {!r}".format(events))

        key = selectors.SelectorKey(
            fileobj, self._fileobj_lookup(fileobj), events, data
        )

        if key.fd in self._fd_to_key:
            raise KeyError("{!r} (FD {}) is already registered".format(fileobj, key.fd))

        self._fd_to_key[key.fd] = key

        if events & EVENT_READ:
            notifier = QtCore.QSocketNotifier(
                key.fd, NotifierEnum.Read, self.__qtparent
            )
            notifier.setEnabled(True)
            notifier.activated["int"].connect(self.__on_read_activated)
            self.__read_notifiers[key.fd] = notifier
        if events & EVENT_WRITE:
            notifier = QtCore.QSocketNotifier(
                key.fd, NotifierEnum.Write, self.__qtparent
            )
            notifier.setEnabled(True)
            notifier.activated["int"].connect(self.__on_write_activated)
            self.__write_notifiers[key.fd] = notifier

        return key

    def __on_read_activated(self, fd):
        self._logger.debug("File %s ready to read", fd)
        key = self._key_from_fd(fd)
        if key:
            self.__parent._process_event(key, EVENT_READ & key.events)

    def __on_write_activated(self, fd):
        self._logger.debug("File %s ready to write", fd)
        key = self._key_from_fd(fd)
        if key:
            self.__parent._process_event(key, EVENT_WRITE & key.events)

    def unregister(self, fileobj):
        def drop_notifier(notifiers):
            try:
                notifier = notifiers.pop(key.fd)
            except KeyError:  # pragma: no cover
                pass
            else:
                self._delete_notifier(notifier)

        try:
            key = self._fd_to_key.pop(self._fileobj_lookup(fileobj))
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None

        drop_notifier(self.__read_notifiers)
        drop_notifier(self.__write_notifiers)

        return key

    def modify(self, fileobj, events, data=None):
        try:
            key = self._fd_to_key[self._fileobj_lookup(fileobj)]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        if events != key.events:
            self.unregister(fileobj)
            key = self.register(fileobj, events, data)
        elif data != key.data:
            # Use a shortcut to update the data.
            key = key._replace(data=data)
            self._fd_to_key[key.fd] = key
        return key

    def close(self):
        self._logger.debug("Closing")
        self._fd_to_key.clear()
        for notifier in itertools.chain(
            self.__read_notifiers.values(), self.__write_notifiers.values()
        ):
            self._delete_notifier(notifier)
        self.__read_notifiers.clear()
        self.__write_notifiers.clear()

    def get_map(self):
        return self.__map

    def _key_from_fd(self, fd):
        """
        Return the key associated to a given file descriptor.

        Parameters:
        fd -- file descriptor

        Returns:
        corresponding key, or None if not found

        """
        try:
            return self._fd_to_key[fd]
        except KeyError:
            return None

    @staticmethod
    def _delete_notifier(notifier):
        notifier.setEnabled(False)
        try:
            notifier.activated["int"].disconnect()
        except Exception:  # pragma: no cover
            pass
        try:
            notifier.deleteLater()
        except Exception:  # pragma: no cover
            pass


class _SelectorEventLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        self._signal_safe_callbacks = []

        try:
            qtparent = self.get_qtparent()
        except AttributeError:  # pragma: no cover
            qtparent = None
        self._qtselector = _Selector(self, qtparent=qtparent)
        asyncio.SelectorEventLoop.__init__(self, self._qtselector)

    def close(self):
        self._qtselector.close()
        super().close()

    def _before_run_forever(self):
        pass

    def _after_run_forever(self):
        pass

    def _process_event(self, key, mask):
        """Selector has delivered us an event."""
        self._logger.debug("Processing event with key %s and mask %s", key, mask)
        fileobj, (reader, writer) = key.fileobj, key.data
        if mask & selectors.EVENT_READ and reader is not None:
            if reader._cancelled:
                self.remove_reader(fileobj)
            else:
                self._logger.debug("Invoking reader callback: %s", reader)
                reader._run()
        if mask & selectors.EVENT_WRITE and writer is not None:
            if writer._cancelled:
                self.remove_writer(fileobj)
            else:
                self._logger.debug("Invoking writer callback: %s", writer)
                writer._run()
