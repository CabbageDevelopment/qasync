# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License

"""UNIX specific Quamash functionality."""

import asyncio
import selectors
import collections

from . import QtCore, with_logger


EVENT_READ = (1 << 0)
EVENT_WRITE = (1 << 1)


def _fileobj_to_fd(fileobj):
    """
    Return a file descriptor from a file object.

    Parameters:
    fileobj -- file object or file descriptor

    Returns:
    corresponding file descriptor

    Raises:
    ValueError if the object is invalid

    """
    if isinstance(fileobj, int):
        fd = fileobj
    else:
        try:
            fd = int(fileobj.fileno())
        except (AttributeError, TypeError, ValueError) as ex:
            raise ValueError("Invalid file object: {!r}".format(fileobj)) from ex
    if fd < 0:
        raise ValueError("Invalid file descriptor: {}".format(fd))
    return fd


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
    def __init__(self, parent):
        # this maps file descriptors to keys
        self._fd_to_key = {}
        # read-only mapping returned by get_map()
        self.__map = _SelectorMapping(self)
        self.__read_notifiers = {}
        self.__write_notifiers = {}
        self.__parent = parent

    def select(self, *args, **kwargs):
        """Implement abstract method even though we don't need it."""
        raise NotImplementedError

    def _fileobj_lookup(self, fileobj):
        """Return a file descriptor from a file object.

        This wraps _fileobj_to_fd() to do an exhaustive search in case
        the object is invalid but we still have it in our map.  This
        is used by unregister() so we can unregister an object that
        was previously registered even if it is closed.  It is also
        used by _SelectorMapping.
        """
        try:
            return _fileobj_to_fd(fileobj)
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

        key = selectors.SelectorKey(fileobj, self._fileobj_lookup(fileobj), events, data)

        if key.fd in self._fd_to_key:
            raise KeyError("{!r} (FD {}) is already registered".format(fileobj, key.fd))

        self._fd_to_key[key.fd] = key

        if events & EVENT_READ:
            notifier = QtCore.QSocketNotifier(key.fd, QtCore.QSocketNotifier.Read)
            notifier.activated['int'].connect(self.__on_read_activated)
            self.__read_notifiers[key.fd] = notifier
        if events & EVENT_WRITE:
            notifier = QtCore.QSocketNotifier(key.fd, QtCore.QSocketNotifier.Write)
            notifier.activated['int'].connect(self.__on_write_activated)
            self.__write_notifiers[key.fd] = notifier

        return key

    def __on_read_activated(self, fd):
        self._logger.debug('File {} ready to read'.format(fd))
        key = self._key_from_fd(fd)
        if key:
            self.__parent._process_event(key, EVENT_READ & key.events)

    def __on_write_activated(self, fd):
        self._logger.debug('File {} ready to write'.format(fd))
        key = self._key_from_fd(fd)
        if key:
            self.__parent._process_event(key, EVENT_WRITE & key.events)

    def unregister(self, fileobj):
        def drop_notifier(notifiers):
            try:
                notifier = notifiers.pop(key.fd)
            except KeyError:
                pass
            else:
                notifier.activated['int'].disconnect()

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
        self._logger.debug('Closing')
        self._fd_to_key.clear()
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


class _SelectorEventLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        self._signal_safe_callbacks = []

        selector = _Selector(self)
        asyncio.SelectorEventLoop.__init__(self, selector)

    def _before_run_forever(self):
        pass

    def _after_run_forever(self):
        pass

    def _process_event(self, key, mask):
        """Selector has delivered us an event."""
        self._logger.debug('Processing event with key {} and mask {}'.format(key, mask))
        fileobj, (reader, writer) = key.fileobj, key.data
        if mask & selectors.EVENT_READ and reader is not None:
            if reader._cancelled:
                self.remove_reader(fileobj)
            else:
                self._logger.debug('Invoking reader callback: {}'.format(reader))
                reader._run()
        if mask & selectors.EVENT_WRITE and writer is not None:
            if writer._cancelled:
                self.remove_writer(fileobj)
            else:
                self._logger.debug('Invoking writer callback: {}'.format(writer))
                writer._run()
