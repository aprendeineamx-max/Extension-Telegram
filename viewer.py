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
import subprocess
from typing import List, Dict, Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QByteArray, Slot, QUrl, QObject, Signal
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
        "media_abs": Qt.UserRole + 7,
        "date_display": Qt.UserRole + 8,
        "time_display": Qt.UserRole + 9,
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

    @Slot(str, result=bool)
    def loadFromPath(self, chat_dir: str) -> bool:
        try:
            path = Path(chat_dir)
            media_dir = path / "media"
            has_media_dir = media_dir.exists() and any(media_dir.rglob("*"))
            messages = load_messages(path, has_media_dir)
        except Exception as e:
            print(f"loadFromPath error: {e}")
            return False
        self.beginResetModel()
        self._all = messages
        self._filtered = list(messages)
        self.endResetModel()
        return True

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
        seen_ids = set()
        text = text_filter.lower().strip()
        sender = sender_filter.strip()
        date_val = date_filter.strip()
        media = media_filter.strip()
        for msg in self._all:
            has_media = bool(msg.get("media_abs"))
            if text and text not in (msg.get("message") or "").lower():
                continue
            if sender and sender not in str(msg.get("sender", "")):
                continue
            if date_val:
                if not msg.get("date", "").startswith(date_val):
                    continue
            if media == "media" and not has_media:
                continue
            if media == "nomedia" and has_media:
                continue
            msg_id = msg.get("id")
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)
            self._filtered.append(msg)
        self.endResetModel()

    @Slot(result=int)
    def totalCount(self) -> int:
        return len(self._all)

    @Slot(result=int)
    def filteredCount(self) -> int:
        return len(self._filtered)


def load_messages(chat_dir: Path, has_media_dir: bool) -> List[dict]:
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

            media_file = obj.get("media_file")
            media_abs = None
            if has_media_dir and media_file:
                candidate = chat_dir / media_file
                if candidate.exists():
                    media_abs = str(candidate.resolve())

            # Evita agregar mensajes sin texto y sin media real (para que no aparezcan huecos)
            text = obj.get("message")
            if not text and not media_abs:
                continue

            messages.append(
                {
                    "id": obj.get("id"),
                    "date": obj.get("date"),  # ISO string
                    "date_display": date_disp,
                    "time_display": time_disp,
                    "message": text,
                    "sender": obj.get("sender_id"),
                    "media_type": obj.get("media_type"),
                    "media_file": media_file,
                    "media_abs": media_abs,
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
    media_dir = chat_dir / "media"
    has_media_dir = media_dir.exists() and any(media_dir.rglob("*"))
    messages = load_messages(chat_dir, has_media_dir)

    app = QGuiApplication([])
    engine = QQmlApplicationEngine()

    class ClipboardHelper(QObject):
        copied = Signal()

        @Slot(str, result=bool)
        def copy(self, text: str) -> bool:
            try:
                QGuiApplication.clipboard().setText(text)
                try:
                    QGuiApplication.clipboard().setText(text, QGuiApplication.clipboard().Selection)
                except Exception:
                    pass
                ok = True
            except Exception:
                ok = False
            if not ok:
                try:
                    subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
                    ok = True
                except Exception:
                    ok = False
            try:
                log_path = Path.cwd() / "copy_log.txt"
                log_path.write_text(text, encoding="utf-8")
            except Exception:
                pass
            if ok:
                self.copied.emit()
            return ok

    class ChatLoader(QObject):
        chatsUpdated = Signal(list)
        currentTitleChanged = Signal(str)

        def __init__(self, message_model: MessageModel, config_path: Path, engine_ref):
            super().__init__()
            self.message_model = message_model
            self.config_path = config_path
            self.engine_ref = engine_ref
            cfg = self._load_config()
            self.base_dir = cfg.get("base_dir") or self.default_base_dir()
            self.current_title = cfg.get("last_chat_title") or ""
            self.current_path = cfg.get("last_chat_path") or ""

        @Slot(str, result=bool)
        def setBaseDir(self, path: str) -> bool:
            p = Path(path).expanduser()
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"setBaseDir error: {e}")
                return False
            self.base_dir = str(p)
            self._save_config()
            self.refreshChats()
            return True

        @Slot(result=str)
        def getBaseDir(self) -> str:
            return self.base_dir

        @Slot()
        def refreshChats(self) -> None:
            chats = self._scan_chats()
            self.chatsUpdated.emit(chats)

        @Slot(str, result=bool)
        def loadChat(self, path: str) -> bool:
            ok = self.message_model.loadFromPath(path)
            if ok:
                self.current_path = path
                self.current_title = Path(path).name
                self.currentTitleChanged.emit(self.current_title)
                try:
                    self.engine_ref.rootContext().setContextProperty("chatTitle", self.current_title)
                except Exception:
                    pass
                self._save_config()
            return ok

        def _scan_chats(self) -> List[Dict[str, Any]]:
            base = Path(self.base_dir) if self.base_dir else Path(self.default_base_dir())
            chats: List[Dict[str, Any]] = []
            if not base.exists():
                return chats
            for d in base.iterdir():
                if not d.is_dir():
                    continue
                msg_file = d / "messages.jsonl"
                if msg_file.exists():
                    chats.append({"title": d.name, "path": str(d)})
                for sub in d.glob("topic_*"):
                    if (sub / "messages.jsonl").exists():
                        chats.append({"title": f"{d.name} / {sub.name}", "path": str(sub)})
            return chats

        def _load_config(self) -> Dict[str, Any]:
            if self.config_path.exists():
                try:
                    return json.loads(self.config_path.read_text(encoding="utf-8"))
                except Exception:
                    return {}
            return {}

        def _save_config(self) -> None:
            try:
                data = {
                    "base_dir": self.base_dir,
                    "last_chat_title": self.current_title,
                    "last_chat_path": self.current_path,
                }
                self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"save_config error: {e}")

        @staticmethod
        def default_base_dir() -> str:
            desktop = Path.home() / "Desktop"
            return str(desktop / "TelegramBackups") if desktop.exists() else str(Path.cwd() / "TelegramBackups")

    model = MessageModel(messages)
    engine.rootContext().setContextProperty("messageModel", model)
    engine.rootContext().setContextProperty("chatTitle", chat_dir.name)
    engine.rootContext().setContextProperty("mediaBasePath", str(chat_dir))
    engine.rootContext().setContextProperty("hasMediaDir", has_media_dir)
    engine.rootContext().setContextProperty("clipboardHelper", ClipboardHelper())
    chat_loader = ChatLoader(model, Path(__file__).parent / "config.json", engine)
    engine.rootContext().setContextProperty("chatLoader", chat_loader)

    qml_path = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise SystemExit("No se pudo cargar QML")
    app.exec()


if __name__ == "__main__":
    main()
