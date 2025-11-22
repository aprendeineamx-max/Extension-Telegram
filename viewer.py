#!/usr/bin/env python
"""
Visor QML para navegar mensajes exportados.

Uso:
  python viewer.py --chat-dir "C:\\Users\\Administrador\\Desktop\\TelegramBackups\\-1003146600095_METODOS ANGEL"

Filtra por texto, sender_id, fecha (YYYY-MM-DD) y tipo de multimedia.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QByteArray, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class MessageModel(QAbstractListModel):
    """Modelo de solo lectura para QML con filtros en memoria."""

    ROLE_MAP = {
        "id": Qt.UserRole + 1,
        "date": Qt.UserRole + 2,
        "message": Qt.UserRole + 3,
        "sender": Qt.UserRole + 4,
        "media_type": Qt.UserRole + 5,
        "media_file": Qt.UserRole + 6,
        "date_display": Qt.UserRole + 7,
        "time_display": Qt.UserRole + 8,
    }

    def __init__(self, messages: List[dict]) -> None:
        super().__init__()
        self._all = messages
        self._filtered = list(messages)

    def rowCount(self, parent=QModelIndex()) -> int:  # type: ignore[override]
        return len(self._filtered)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
        if not index.isValid():
            return None
        msg = self._filtered[index.row()]
        for key, role_id in self.ROLE_MAP.items():
            if role == role_id:
                return msg.get(key)
        if role == Qt.DisplayRole:
            return msg.get("message")
        return None

    def roleNames(self):  # type: ignore[override]
        return {role: QByteArray(name.encode()) for name, role in self.ROLE_MAP.items()}

    @Slot(str, str, str, str)
    def applyFilters(self, text_filter: str, sender_filter: str, date_filter: str, media_filter: str) -> None:
        """
        text_filter: substring en message.
        sender_filter: substring en sender_id.
        date_filter: YYYY-MM-DD (fecha exacta) o vacío.
        media_filter: "", "media", "nomedia".
        """
        self.beginResetModel()
        self._filtered = []
        text = text_filter.lower().strip()
        sender = sender_filter.strip()
        date_val = date_filter.strip()
        media = media_filter.strip()
        for msg in self._all:
            if text and text not in (msg.get("message") or "").lower():
                continue
            if sender and sender not in str(msg.get("sender", "")):
                continue
            if date_val:
                if not msg.get("date", "").startswith(date_val):
                    continue
            if media == "media" and not msg.get("media_file") and not msg.get("media_type"):
                continue
            if media == "nomedia" and (msg.get("media_file") or msg.get("media_type")):
                continue
            self._filtered.append(msg)
        self.endResetModel()

    @Slot(result=int)
    def totalCount(self) -> int:
        return len(self._all)

    @Slot(result=int)
    def filteredCount(self) -> int:
        return len(self._filtered)


def load_messages(chat_dir: Path) -> List[dict]:
    messages_path = chat_dir / "messages.jsonl"
    if not messages_path.exists():
        raise FileNotFoundError(f"No se encontró {messages_path}")
    messages: List[dict] = []
    with messages_path.open(encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            dt = obj.get("date")
            date_disp = ""
            time_disp = ""
            if dt:
                try:
                    parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    date_disp = parsed.strftime("%Y-%m-%d")
                    time_disp = parsed.strftime("%H:%M")
                except Exception:
                    date_disp = dt[:10]
                    time_disp = dt[11:16] if len(dt) >= 16 else ""
            messages.append(
                {
                    "id": obj.get("id"),
                    "date": obj.get("date"),  # ISO string
                    "date_display": date_disp,
                    "time_display": time_disp,
                    "message": obj.get("message"),
                    "sender": obj.get("sender_id"),
                    "media_type": obj.get("media_type"),
                    "media_file": obj.get("media_file"),
                }
            )
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Visor QML de mensajes exportados")
    parser.add_argument(
        "--chat-dir",
        required=True,
        type=Path,
        help="Carpeta del chat exportado (contiene messages.jsonl y media/)",
    )
    args = parser.parse_args()
    chat_dir = args.chat_dir.expanduser()
    messages = load_messages(chat_dir)

    app = QGuiApplication([])
    engine = QQmlApplicationEngine()

    model = MessageModel(messages)
    engine.rootContext().setContextProperty("messageModel", model)
    engine.rootContext().setContextProperty("chatTitle", chat_dir.name)
    engine.rootContext().setContextProperty("mediaBasePath", str(chat_dir))

    qml_path = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise SystemExit("No se pudo cargar QML")
    app.exec()


if __name__ == "__main__":
    main()
