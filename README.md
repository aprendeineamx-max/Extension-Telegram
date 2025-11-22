# Respaldo de chats de Telegram (mensajes + multimedia)

Script basado en Telethon para descargar todos tus chats, grupos, canales y bots de Telegram, incluyendo el contenido multimedia, en carpetas locales (por defecto en tu Escritorio).

## Requisitos
- Python 3.9+ instalado.
- Credenciales de API de Telegram: crea una app en https://my.telegram.org/apps y obtén `api_id` y `api_hash`.
- Un número de teléfono con sesión en Telegram (se pedirá el código/2FA la primera vez).

## Instalación rápida
```bash
git clone <este-repo> telegram-backup
cd telegram-backup
python -m pip install -r requirements.txt
```

Opcional: crea un archivo `.env` (basado en `.env.example`) para no pasar credenciales por línea de comandos:
```
TG_API_ID=123456
TG_API_HASH=abcdef1234567890
TG_PHONE=+34123456789
```

## Uso
Por defecto guardará todo en `~/Desktop/TelegramBackups`. Ejemplo completo:
```bash
python backup_telegram.py ^
  --api-id 123456 ^
  --api-hash abcdef1234567890 ^
  --phone +34123456789
```

Parámetros útiles:
- `--output PATH` cambia la ruta de salida (ej: `"C:\\Users\\Administrator\\Desktop\\TelegramBackups"`).
- `--limit N` limita mensajes por chat (0 = todos, valor por defecto).
- `--skip-media` salta la descarga de multimedia.
- `--chats ...` filtra por IDs o fragmentos del nombre (por defecto exporta todo).
- `--session NOMBRE` cambia el archivo de sesión (se guarda en `sessions/`).

La primera ejecución pedirá el código de inicio de sesión (y contraseña 2FA si aplica). Las siguientes usarán el archivo de sesión guardado.

## Visor de mensajes (Qt + QML)
Instala PySide6 (ya en `requirements.txt`) y ejecuta el visor apuntando a un chat exportado:
```bash
python viewer.py --chat-dir "C:\Users\Administrador\Desktop\TelegramBackups\-1003146600095_METODOS ANGEL"
```
Permite filtrar por texto, sender_id, fecha (YYYY-MM-DD) y si tiene multimedia. Lee `messages.jsonl` y muestra los archivos asociados (ruta relativa).

## Exportar temas de un grupo/canal con foros
Si tu grupo usa topics (como los "chats" internos de un foro), puedes exportarlos todos con:
```bash
python export_topics.py --link https://web.telegram.org/k/#-3146600095
```
Esto creará una carpeta `TelegramBackupsTopics/<chat_id>/topic_<id>_<titulo>/` con `messages.jsonl` y media por cada topic. Ajustes opcionales:
- `--limit 500` para limitar mensajes por topic.
- `--skip-media` para no descargar archivos.
- `--output <ruta>` para cambiar la carpeta base de salida.
- `--chat-id -1003146600095` si prefieres pasar el id directamente.

## Salida
- `TelegramBackups/sessions/`: archivo de sesión de Telethon.
- `TelegramBackups/<id>_<nombre>/chat.json`: metadatos básicos del chat.
- `TelegramBackups/<id>_<nombre>/messages.jsonl`: mensajes en formato JSONL (una línea por mensaje).
- `TelegramBackups/<id>_<nombre>/media/`: archivos multimedia descargados.
- `TelegramBackups/resumen.json`: resumen con conteos por chat.

## Notas y buenas prácticas
- Si tienes canales/grupos enormes, la primera descarga puede tardar; puedes probar primero con `--limit 500`.
- El script recorre mensajes en orden cronológico (antiguo → nuevo) para facilitar reanudaciones.
- Mantén tus `api_id`, `api_hash` y archivo de sesión en un lugar seguro: dan acceso a tu cuenta.
