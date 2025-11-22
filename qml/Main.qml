import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Qt.labs.platform 1.1

Window {
    visible: true
    width: 1200
    height: 820
    minimumWidth: 900
    minimumHeight: 700
    title: "Visor de Telegram - " + chatTitle
    color: backgroundColor

    property int messageSpacing: 14
    property string toastText: ""
    property int messageFontSize: 17
    property color messageFontColor: "white"
    property bool allowSelection: true
    property var colorOptionsPrimary: ["#ffffff", "#c7d9ff", "#ffd166", "#8fc1ff", "#a0f0c5"]
    property var colorOptionsMore: ["#ff8fa3", "#d3b8ff", "#ffcf9f", "#9df3ff", "#e3e3e3"]
    property bool showMoreColors: false
    property color backgroundColor: "#0b1422"
    property real backgroundOpacity: 1.0
    property var backgroundPalette: ["#0b1422", "#0f1d2f", "#111c2d", "#1b2435", "#22324c"]

    Rectangle {
        anchors.fill: parent
        color: backgroundColor
        opacity: backgroundOpacity
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

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
                    ToolButton {
                        id: settingsBtn
                        text: "\u2699"
                        onClicked: settingsPopup.open()
                        background: Rectangle { radius: 6; color: settingsBtn.down ? "#2f486b" : (settingsBtn.hovered ? "#253652" : "transparent") }
                        contentItem: Text {
                            text: "\u2699"
                            color: "#8fc1ff"
                            font.pixelSize: 16
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    TextField {
                        id: textFilter
                        placeholderText: "Buscar en mensaje"
                        Layout.fillWidth: true
                        onTextChanged: applyFilters()
                        background: Rectangle { radius: 8; color: "#0f1d2f"; border.color: "#1f3250" }
                        color: "#e6edf7"
                        placeholderTextColor: "#5f6f8c"
                    }
                    TextField {
                        id: senderFilter
                        placeholderText: "Sender ID"
                        Layout.preferredWidth: 150
                        onTextChanged: applyFilters()
                        background: Rectangle { radius: 8; color: "#0f1d2f"; border.color: "#1f3250" }
                        color: "#e6edf7"
                        placeholderTextColor: "#5f6f8c"
                    }
                    TextField {
                        id: dateFilter
                        placeholderText: "YYYY-MM-DD"
                        Layout.preferredWidth: 140
                        onTextChanged: applyFilters()
                        background: Rectangle { radius: 8; color: "#0f1d2f"; border.color: "#1f3250" }
                        color: "#e6edf7"
                        placeholderTextColor: "#5f6f8c"
                    }
                    ComboBox {
                        id: mediaCombo
                        Layout.preferredWidth: 140
                        model: ["Todos", "Solo media", "Solo texto"]
                        onCurrentIndexChanged: applyFilters()
                        background: Rectangle { radius: 8; color: "#0f1d2f"; border.color: "#1f3250" }
                        contentItem: Text {
                            text: mediaCombo.displayText
                            color: "#e6edf7"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 8
                        }
                    }
                }
            }
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: messageSpacing
            model: messageModel
            cacheBuffer: 4000
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: listView.width
                property bool hasContent: (message && message.length > 0) || (hasMediaDir && media_abs)
                visible: hasContent
                height: hasContent ? bubble.implicitHeight : 0

                Rectangle {
                    id: bubble
                    anchors.horizontalCenter: parent.horizontalCenter
                    radius: 14
                    color: "#16243a"
                    border.color: "#2e4b70"
                    width: Math.min(listView.width * 0.85, 900)
                    implicitHeight: contentColumn.implicitHeight + 20

                    Column {
                        id: contentColumn
                        spacing: 8
                        anchors.fill: parent
                        anchors.margins: 14
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
                            Item { Layout.fillWidth: true; width: 1 }
                            Text {
                                text: date_display + " " + time_display
                                color: "#9ab"
                                wrapMode: Text.NoWrap
                            }
                            ToolButton {
                                id: copyBtn
                                implicitWidth: 28
                                implicitHeight: 28
                                property bool copied: false
                                background: Rectangle {
                                    radius: 6
                                    color: copyBtn.down ? "#2f486b" : (copyBtn.hovered ? "#253652" : "transparent")
                                    border.color: "#3c5a82"
                                }
                                contentItem: Text {
                                    text: copyBtn.copied ? "✔" : "\u2398"
                                    color: "#8fc1ff"
                                    font.pixelSize: 16
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                Timer { id: copyReset; interval: 1200; repeat: false; running: false; onTriggered: copyBtn.copied = false }
                                onClicked: {
                                    copyMessage(sender, date_display, time_display, message, media_file, media_abs);
                                    copyBtn.copied = true;
                                    copyReset.restart();
                                }
                            }
                        }

                        TextEdit {
                            width: parent.width
                            visible: message && message.length > 0
                            text: message
                            color: messageFontColor
                            wrapMode: TextEdit.Wrap
                            font.pixelSize: messageFontSize
                            readOnly: true
                            selectByMouse: allowSelection
                            selectByKeyboard: allowSelection
                        }

                        Rectangle {
                            visible: hasMediaDir && media_abs
                            radius: 8
                            color: "#22324c"
                            border.color: "#30486b"
                            width: parent.width
                            implicitHeight: mediaRow.implicitHeight + 14
                            Row {
                                id: mediaRow
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 12
                                Text {
                                    id: mediaText
                                    text: "Archivo: " + media_file
                                    color: "#8fc1ff"
                                    wrapMode: Text.Wrap
                                    width: parent.width - openBtn.implicitWidth - 20
                                }
                                Button {
                                    id: openBtn
                                    text: "Abrir"
                                    onClicked: Qt.openUrlExternally("file:///" + media_abs.replace(/\\/g, "/"))
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
        messageModel.applyFilters(textFilter.text, senderFilter.text, dateFilter.text, mediaVal);
    }

    function copyMessage(sender, date_display, time_display, message, media_file, media_abs) {
        let parts = [];
        if (sender) parts.push("Sender: " + sender);
        let dt = (date_display || "") + (time_display ? " " + time_display : "");
        if (dt.trim().length > 0) parts.push(dt.trim());
        if (message && message.length > 0) parts.push(message);
        if (hasMediaDir && media_file) parts.push("Archivo: " + media_file);
        let txt = parts.join("\n");
        var ok = false;
        if (typeof clipboardHelper !== "undefined" && clipboardHelper.copy) {
            ok = clipboardHelper.copy(txt);
        }
        if (!ok && Qt && Qt.application && Qt.application.clipboard) {
            try { Qt.application.clipboard.setText(txt); ok = true; } catch (e) { ok = false; }
        }
        showToast(ok ? "Copiado" : "Error al copiar");
    }

    Popup {
        id: settingsPopup
        modal: true
        focus: true
        x: parent.width - width - 20
        y: topColumn.height + 30
        background: Rectangle { color: "#111c2d"; radius: 10; border.color: "#1d2f49" }

        contentItem: ColumnLayout {
            anchors.margins: 12
            anchors.fill: parent
            spacing: 10

            Label { text: "Espaciado entre mensajes (px)"; color: "white"; font.pixelSize: 14 }
            Slider { id: spacingSlider; from: 4; to: 60; value: messageSpacing; onValueChanged: messageSpacing = Math.round(value) }
            Label { text: messageSpacing + " px"; color: "#8fc1ff" }

            Label { text: "Tamaño de fuente"; color: "white"; font.pixelSize: 14 }
            Slider { id: fontSlider; from: 12; to: 28; value: messageFontSize; onValueChanged: messageFontSize = Math.round(value) }
            Label { text: messageFontSize + " px"; color: "#8fc1ff" }

            Label { text: "Color de fuente"; color: "white"; font.pixelSize: 14 }
            Grid {
                columns: 5
                spacing: 6
                Repeater {
                    model: showMoreColors ? colorOptionsPrimary.concat(colorOptionsMore) : colorOptionsPrimary
                    delegate: Rectangle {
                        width: 26; height: 26; radius: 6
                        color: modelData
                        border.color: messageFontColor === modelData ? "#8fc1ff" : "#1d2f49"
                        border.width: 2
                        MouseArea { anchors.fill: parent; onClicked: messageFontColor = modelData }
                    }
                }
            }
            Button { text: showMoreColors ? "Ver menos colores" : "Ver más colores"; onClicked: showMoreColors = !showMoreColors }

            Label { text: "Color de fondo"; color: "white"; font.pixelSize: 14 }
            Grid {
                columns: 5
                spacing: 6
                Repeater {
                    model: backgroundPalette
                    delegate: Rectangle {
                        width: 26; height: 26; radius: 6
                        color: modelData
                        border.color: backgroundColor === modelData ? "#8fc1ff" : "#1d2f49"
                        border.width: 2
                        MouseArea { anchors.fill: parent; onClicked: backgroundColor = modelData }
                    }
                }
            }
            CheckBox { text: "Fondo translúcido"; checked: backgroundOpacity < 1.0; onCheckedChanged: backgroundOpacity = checked ? 0.82 : 1.0 }
            Button { text: "Restablecer fondo por defecto"; onClicked: { backgroundColor = "#0b1422"; backgroundOpacity = 1.0; } }

            CheckBox { id: selectionToggle; text: "Permitir seleccionar texto"; checked: allowSelection; onCheckedChanged: allowSelection = checked }

            Button { text: "Cerrar"; onClicked: settingsPopup.close() }
        }
    }

    Rectangle {
        id: toast
        visible: false
        opacity: 0
        z: 999
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 16
        radius: 8
        color: "#111c2d"
        border.color: "#1d2f49"
        implicitWidth: toastLabel.implicitWidth + 20
        implicitHeight: toastLabel.implicitHeight + 12
        Behavior on opacity { NumberAnimation { duration: 150 } }
        Text {
            id: toastLabel
            anchors.centerIn: parent
            color: "#8fc1ff"
            text: toastText
            font.pixelSize: 14
        }
    }

    Timer {
        id: toastTimer
        interval: 1200
        running: false
        repeat: false
        onTriggered: { toast.opacity = 0; toast.visible = false }
    }

    Connections {
        target: clipboardHelper
        function onCopied() { showToast("Copiado"); }
    }

    function showToast(text) {
        toastText = text;
        toast.visible = true;
        toast.opacity = 1;
        toastTimer.restart();
    }
}
