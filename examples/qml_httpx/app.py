import sys
import asyncio
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from qasync import QEventLoop, QApplication

from service import ExampleService

QML_PATH = Path(__file__).parent.absolute().joinpath("qml")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    engine = QQmlApplicationEngine()
    engine.addImportPath(QML_PATH)

    app.aboutToQuit.connect(engine.deleteLater)
    engine.quit.connect(app.quit)

    # register our service, making it usable directly in QML
    qmlRegisterType(ExampleService, "qasync", 1, 0, ExampleService.__name__)

    # alternatively, instantiate the service and inject it into the QML engine
    # service = ExampleService()
    # engine.rootContext().setContextProperty("service", service)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    engine.quit.connect(app_close_event.set)

    qml_entry = QUrl.fromLocalFile(str(QML_PATH.joinpath("Main.qml")))
    engine.load(qml_entry)

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())
