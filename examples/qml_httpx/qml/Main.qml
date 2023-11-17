import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: root
    title: "qasync"
    visible: true
    width: 420
    height: 240

    Loader {
        id: mainLoader
        anchors.fill: parent
        source: "Page.qml"
    }
}
