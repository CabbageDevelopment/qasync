import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

Item {
    ExampleService {
        id: service

        // handle value changes inside the service object
        onValueChanged: {
            // use value
        }
    }

    Connections {
        target: service

        // handle value changes with an external Connection
        function onValueChanged(value) {
            // use value
        }
    }

    ColumnLayout {
        anchors {
            fill: parent
            margins: 10
        }

        RowLayout {
            Layout.fillWidth: true

            Button {
                id: button
                Layout.preferredWidth: 100
                enabled: !service.isLoading

                text: {
                    return service.isLoading ? qsTr("Loading...") : qsTr("Fetch")
                }
                onClicked: function() {
                    service.fetch(url.text)
                }
            }

            TextField {
                id: url
                Layout.fillWidth: true
                enabled: !service.isLoading
                text: qsTr("https://jsonplaceholder.typicode.com/todos/1")
            }
        }

        TextEdit {
            id: text
            Layout.fillHeight: true
            Layout.fillWidth: true

            // react to value changes from other widgets
            text: service.value
        }
    }

}
