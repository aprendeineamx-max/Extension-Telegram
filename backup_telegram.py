#!/usr/bin/env python
"""
Backup completo de chats/grupos/canales/bots de Telegram con Telethon.

Guarda mensajes en JSONL y multimedia en carpetas separadas. Por defecto usa
`~/Desktop/TelegramBackups` como destino y persiste la sesión para que solo
se pida el código de Telegram la primera vez.
"""
import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.utils import get_peer_id


def load_env() -> None:
    """Carga variables desde .env si existe."""
    load_dotenv()


def sanitize_name(name: str) -> str:
    """Limpia nombres para usarlos como carpeta/archivo en Windows."""
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', "_", name.strip()) or "chat"
    return cleaned[:80]


def default_output_dir() -> Path:
    desktop = Path.home() / "Desktop"
    return desktop / "TelegramBackups" if desktop.exists() else Path.cwd() / "TelegramBackups"


def message_to_dict(msg) -> Dict[str, Any]:
    """Convierte un mensaje de Telethon en un dict JSON-friendly."""
    data: Dict[str, Any] = {
        "id": msg.id,
        "date": msg.date.isoformat() if msg.date else None,
        "message": msg.message,
        "sender_id": msg.sender_id,
        "chat_id": get_peer_id(msg.peer_id) if msg.peer_id else None,
        "reply_to_msg_id": getattr(msg, "reply_to_msg_id", None),
        "via_bot_id": getattr(msg, "via_bot_id", None),
        "views": getattr(msg, "views", None),
        "forwards": getattr(msg, "forwards", None),
        "reactions": [r.to_dict() for r in msg.reactions.results] if getattr(msg, "reactions", None) else None,
        "fwd_from": msg.fwd_from.to_dict() if msg.fwd_from else None,
        "action": msg.action.to_dict() if getattr(msg, "action", None) else None,
        "media_type": msg.media.__class__.__name__ if msg.media else None,
    }
    return data


async def export_dialog(client: TelegramClient, dialog, base_dir: Path, limit: Optional[int], skip_media: bool) -> Dict[str, Any]:
    """Exporta un diálogo entero (mensajes + multimedia)."""
    chat_id = dialog.id
    chat_title = sanitize_name(dialog.name or f"chat_{chat_id}")
    chat_dir = base_dir / f"{chat_id}_{chat_title}"
    media_dir = chat_dir / "media"
    chat_dir.mkdir(parents=True, exist_ok=True)

    # Guarda info básica del chat
    meta_path = chat_dir / "chat.json"
    meta = {
        "id": chat_id,
        "title": dialog.name,
        "entity_type": dialog.entity.__class__.__name__,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    messages_path = chat_dir / "messages.jsonl"
    written = 0
    downloaded_media = 0

    # Orden cronológico: reverse=True recorre del más antiguo al más nuevo.
    async for msg in client.iter_messages(dialog.entity, limit=limit, reverse=True):
        payload = message_to_dict(msg)

        if not skip_media and msg.media:
            media_dir.mkdir(parents=True, exist_ok=True)
            file_path = await msg.download_media(file=media_dir)
            if file_path:
                # Guardamos ruta relativa para enlazar mensaje con archivo
                payload["media_file"] = os.path.relpath(file_path, chat_dir)
                downloaded_media += 1

        with messages_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        written += 1

    return {
        "chat_id": chat_id,
        "title": dialog.name,
        "messages": written,
        "media": downloaded_media,
        "path": str(chat_dir),
    }


async def run_backup(
    api_id: int,
    api_hash: str,
    phone: Optional[str],
    session_name: str,
    output_dir: Path,
    limit: Optional[int],
    chats: Optional[Iterable[str]],
    skip_media: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    session_path = output_dir / "sessions" / session_name
    session_path.parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(session_path), api_id, api_hash)

    await client.connect()
    if not await client.is_user_authorized():
        if not phone:
            raise RuntimeError("Necesitas proporcionar --phone o la variable TG_PHONE para iniciar sesión.")
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, input("Código de Telegram: "))
        except SessionPasswordNeededError:
            await client.sign_in(password=input("Tu contraseña 2FA: "))

    dialogs = []
    async for d in client.iter_dialogs():
        if chats:
            # Permite filtrar por ID o parte del nombre
            match = str(d.id) in chats or any(q.lower() in (d.name or "").lower() for q in chats)
            if not match:
                continue
        dialogs.append(d)

    print(f"Se encontraron {len(dialogs)} chats/diálogos para exportar.")

    results = []
    for dialog in dialogs:
        print(f"- Exportando: {dialog.name} (id={dialog.id}) ...")
        info = await export_dialog(client, dialog, output_dir, limit, skip_media)
        results.append(info)
        print(f"  > Mensajes: {info['messages']}, multimedia: {info['media']}, carpeta: {info['path']}")

    await client.disconnect()

    summary_path = output_dir / "resumen.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRespaldo finalizado. Resumen guardado en: {summary_path}")


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(
        description="Exporta todos tus chats/grupos/canales de Telegram (mensajes + multimedia)."
    )
    parser.add_argument("--api-id", type=int, default=int(os.getenv("TG_API_ID", "0")), help="API_ID de https://my.telegram.org/apps")
    parser.add_argument("--api-hash", default=os.getenv("TG_API_HASH", ""), help="API_HASH de https://my.telegram.org/apps")
    parser.add_argument("--phone", default=os.getenv("TG_PHONE"), help="Teléfono con prefijo país, ej: +34123456789")
    parser.add_argument("--session", default="tg_backup", help="Nombre del archivo de sesión Telethon")
    parser.add_argument("--output", type=Path, default=None, help="Ruta de salida (por defecto: Escritorio/TelegramBackups)")
    parser.add_argument("--limit", type=int, default=0, help="Máx. mensajes por chat (0 = todos)")
    parser.add_argument("--skip-media", action="store_true", help="No descargar multimedia, solo mensajes")
    parser.add_argument("--chats", nargs="*", help="Filtrar por ID o parte del nombre (por defecto: todos)")

    args = parser.parse_args()

    if not args.api_id or not args.api_hash:
        raise SystemExit("Faltan API_ID/API_HASH. Consíguelos en https://my.telegram.org/apps y pásalos por argumentos o variables.")

    output_dir = args.output or default_output_dir()
    limit = None if args.limit == 0 else args.limit

    asyncio.run(
        run_backup(
            api_id=args.api_id,
            api_hash=args.api_hash,
            phone=args.phone,
            session_name=args.session,
            output_dir=output_dir,
            limit=limit,
            chats=args.chats,
            skip_media=args.skip_media,
        )
    )


if __name__ == "__main__":
    main()
