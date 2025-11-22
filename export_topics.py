#!/usr/bin/env python
"""
Exporta todos los temas (forum topics) de un grupo/canal con foros y guarda cada tema en su carpeta.

Uso:
  python export_topics.py --link https://web.telegram.org/k/#-3146600095

O con chat_id directo:
  python export_topics.py --chat-id -1003146600095

Parámetros:
  --output     Ruta base de salida (por defecto Escritorio/TelegramBackupsTopics)
  --limit      Límite de mensajes por tema (0 = todos)
  --skip-media No descargar multimedia
"""
import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import GetForumTopicsRequest


def parse_link(link: str) -> Optional[int]:
    m = re.search(r"#-?(\d+)", link) or re.search(r"=(\-?\d+)", link)
    if not m:
        return None
    raw = int(m.group(1))
    # Normaliza a -100 prefix si es necesario
    return raw if str(raw).startswith("-100") else int(f"-100{abs(raw)}")


def sanitize_name(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[<>:\"/\\\\|?*]+", "_", name)
    return name[:80] or "tema"


async def export_topic(client, entity, topic, base_dir: Path, limit: Optional[int], skip_media: bool):
    folder = base_dir / f"topic_{topic.id}_{sanitize_name(topic.title or 'tema')}"
    media_dir = folder / "media"
    folder.mkdir(parents=True, exist_ok=True)

    meta = {
        "topic_id": topic.id,
        "title": topic.title,
        "messages_count": topic.total_messages,
    }
    (folder / "topic.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    messages_path = folder / "messages.jsonl"
    written = 0
    downloaded = 0
    async for msg in client.iter_messages(entity, reply_to=topic.id, reverse=True, limit=limit):
        payload = {
            "id": msg.id,
            "date": msg.date.isoformat() if msg.date else None,
            "message": msg.message,
            "sender_id": msg.sender_id,
            "reply_to_msg_id": getattr(msg, "reply_to_msg_id", None),
            "views": getattr(msg, "views", None),
            "forwards": getattr(msg, "forwards", None),
            "media_type": msg.media.__class__.__name__ if msg.media else None,
        }
        if not skip_media and msg.media:
            media_dir.mkdir(parents=True, exist_ok=True)
            file_path = await msg.download_media(file=media_dir)
            if file_path:
                payload["media_file"] = os.path.relpath(file_path, folder)
                downloaded += 1
        with messages_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        written += 1

    return {"topic_id": topic.id, "title": topic.title, "messages": written, "media": downloaded, "path": str(folder)}


async def run(link: Optional[str], chat_id: Optional[int], output: Path, limit: Optional[int], skip_media: bool, session_name: str):
    load_dotenv()
    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    phone = os.getenv("TG_PHONE")
    if not api_id or not api_hash:
        raise SystemExit("Faltan TG_API_ID / TG_API_HASH en .env o argumentos.")

    if link and not chat_id:
        chat_id = parse_link(link)
    if not chat_id:
        raise SystemExit("Necesitas --link o --chat-id válido.")

    output.mkdir(parents=True, exist_ok=True)
    session_dir = output / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(session_dir / session_name), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        if not phone:
            raise RuntimeError("Proporciona TG_PHONE o --phone para iniciar sesión.")
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, input("Código de Telegram: "))
        except SessionPasswordNeededError:
            await client.sign_in(password=input("Tu contraseña 2FA: "))

    entity = await client.get_entity(chat_id)
    base_dir = output / sanitize_name(str(chat_id))
    base_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    offset_topic = 0
    while True:
        res = await client(GetForumTopicsRequest(entity, offset_date=None, offset_id=0, offset_topic=offset_topic, limit=100))
        if not res.topics:
            break
        for t in res.topics:
            info = await export_topic(client, entity, t, base_dir, limit, skip_media)
            summary.append(info)
        offset_topic = res.topics[-1].id

    (base_dir / "resumen_topics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    await client.disconnect()
    print(f"Exportados {len(summary)} temas. Ver {base_dir}")


def main():
    parser = argparse.ArgumentParser(description="Exporta todos los topics de un grupo/canal con foros.")
    parser.add_argument("--link", help="Enlace web.telegram.org o t.me del grupo/canal")
    parser.add_argument("--chat-id", type=int, help="Chat id numérico (ej: -1003146600095)")
    parser.add_argument("--output", type=Path, default=None, help="Ruta de salida base (defecto Escritorio/TelegramBackupsTopics)")
    parser.add_argument("--limit", type=int, default=0, help="Máx. mensajes por tema (0 = todos)")
    parser.add_argument("--skip-media", action="store_true", help="No descargar multimedia")
    parser.add_argument("--session", default="topics_session", help="Nombre de archivo de sesión")
    args = parser.parse_args()

    desktop = Path.home() / "Desktop"
    default_out = desktop / "TelegramBackupsTopics" if desktop.exists() else Path.cwd() / "TelegramBackupsTopics"
    out = args.output or default_out
    limit = None if args.limit == 0 else args.limit

    asyncio.run(run(args.link, args.chat_id, out, limit, args.skip_media, args.session))


if __name__ == "__main__":
    main()
