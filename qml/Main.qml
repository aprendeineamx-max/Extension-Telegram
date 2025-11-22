import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    visible: true
    width: 1200
    height: 820
    minimumWidth: 900
    minimumHeight: 700
    title: "Visor de Telegram - " + chatTitle
    color: "#0b1422"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b1422" }
            GradientStop { position: 1.0; color: "#0f1d2f" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // Barra de filtros y título
        Rectangle {
            Layout.fillWidth: true
            radius: 12
            color: "#111c2d"
            border.color: "#1d2f49"
            implicitHeight: topColumn.implicitHeight + 16

            ColumnLayout {
                id: topColumn
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Label {
                        text: chatTitle
                        color: "white"
                        font.pixelSize: 22
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Label { text: "Total: " + messageModel.totalCount(); color: "#8fc1ff" }
                    Label { text: "Filtrados: " + messageModel.filteredCount(); color: "#8fc1ff" }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    TextField {
                        id: textFilter
                        placeholderText: "Buscar en mensaje"
                        Layout.fillWidth: true
                        onTextChanged: applyFilters()
                    }
                    TextField {
                        id: senderFilter
                        placeholderText: "Sender ID"
                        Layout.preferredWidth: 150
                        onTextChanged: applyFilters()
                    }
                    TextField {
                        id: dateFilter
                        placeholderText: "YYYY-MM-DD"
                        Layout.preferredWidth: 140
                        onTextChanged: applyFilters()
                    }
                    ComboBox {
                        id: mediaCombo
                        Layout.preferredWidth: 140
                        model: ["Todos", "Solo media", "Solo texto"]
                        onCurrentIndexChanged: applyFilters()
                    }
                }
            }
        }

        // Lista de mensajes estilo burbuja
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 14
            model: messageModel
            cacheBuffer: 4000
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: listView.width
                height: bubble.implicitHeight + 8

                Item {
                    id: bubble
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    implicitHeight: card.implicitHeight

                    Rectangle {
                        id: card
                        radius: 14
                        color: "#16243a"
                        border.color: "#2e4b70"
                        anchors.left: parent.left
                        width: Math.min(listView.width * 0.85, 900)
                        anchors.horizontalCenter: undefined
                        implicitHeight: contentColumn.implicitHeight + 28

                        Column {
                            id: contentColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            width: parent.width - 28

                            Row {
                                width: parent.width
                                spacing: 8
                                Text {
                                    text: sender ? ("Sender: " + sender) : "Sender: (desconocido)"
                                    color: "#d8e6ff"
                                    font.bold: true
                                    wrapMode: Text.NoWrap
                                }
                                Item { width: 1; Layout.fillWidth: true }
                                Text {
                                    text: date_display + " " + time_display
                                    color: "#9ab"
                                    wrapMode: Text.NoWrap
                                }
                            }

                            Text {
                                width: parent.width
                                text: (message && message.length > 0) ? message
                                      : (media_type ? ("Media: " + media_type) : "(sin texto)")
                                color: "white"
                                wrapMode: Text.Wrap
                                font.pixelSize: 17
                                maximumLineCount: 0
                            }

                            Rectangle {
                                visible: media_file !== undefined && media_file !== null
                                radius: 8
                                color: "#22324c"
                                border.color: "#30486b"
                                width: parent.width
                                implicitHeight: mediaText.implicitHeight + 14
                                Text {
                                    id: mediaText
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    text: "Archivo: " + media_file
                                    color: "#8fc1ff"
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function applyFilters() {
        let mediaVal = "";
        if (mediaCombo.currentIndex === 1) mediaVal = "media";
        else if (mediaCombo.currentIndex === 2) mediaVal = "nomedia";
        messageModel.applyFilters(
                    textFilter.text,
                    senderFilter.text,
                    dateFilter.text,
                    mediaVal);
    }
}
