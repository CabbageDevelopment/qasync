import httpx

from PySide6.QtCore import QObject, Signal, Property, Slot
from qasync import asyncSlot


class ExampleService(QObject):
    valueChanged = Signal(str, arguments=["value"])
    loadingChanged = Signal(bool, arguments=["loading"])

    def __init__(self, parent=None):
        QObject.__init__(self, parent)

        self._value = None
        self._loading = False

    def _set_value(self, value):
        if self._value != value:
            self._value = value
            self.valueChanged.emit(value)

    def _set_loading(self, value):
        if self._loading != value:
            self._loading = value
            self.loadingChanged.emit(value)

    @Property(str, notify=valueChanged)
    def value(self) -> str:
        return self._value

    @Property(bool, notify=loadingChanged)
    def isLoading(self) -> bool:
        return self._loading

    @asyncSlot(str)
    async def fetch(self, endpoint: str):
        if not endpoint:
            return

        self._set_loading(True)
        async with httpx.AsyncClient() as client:
            resp = await client.get(endpoint)
            self._set_value(resp.text)
            self._set_loading(False)
