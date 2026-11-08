import os
import asyncio
import logging
import secrets
import tempfile
import shutil
from pathlib import Path

import yt_dlp
import imageio_ffmpeg

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
PORT = int(os.getenv("PORT", "10000"))

WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "telegram")
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    secrets.token_urlsafe(32)
)
COOKIE_FILE = "/etc/secrets/youtube_cookies.txt"
DENO_PATH = str(Path.home() / ".deno" / "bin" / "deno")
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
MAX_FILE_SIZE = 49 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def load_cookies(options, folder):
    if not os.path.isfile(COOKIE_FILE):
        logger.warning("YouTube cookies NOT FOUND: %s", COOKIE_FILE)
        return

    temp_cookie = os.path.join(folder, "cookies.txt")
    shutil.copyfile(COOKIE_FILE, temp_cookie)

    cookie_size = os.path.getsize(temp_cookie)

    if cookie_size == 0:
        logger.error("YouTube cookie file is EMPTY")
        return

    options["cookiefile"] = temp_cookie

    logger.info(
        "YouTube cookies loaded successfully. Size: %s bytes",
        cookie_size
    )
# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 🚀\n\n"
        "به Trendify Media Downloader خوش آمدی.\n\n"
        "لینک ویدیو را ارسال کن:\n"
        "YouTube | Instagram | TikTok | Facebook | X\n\n"
        "سایر سایت‌های پشتیبانی‌شده توسط yt-dlp نیز قابل بررسی هستند."
    )


# ================= DOWNLOAD INFO =================
def extract_info(url):
    with tempfile.TemporaryDirectory() as temp_dir:
        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 45,
            "extract_flat": False,
            "js_runtimes": {
                "deno": {
                    "path": DENO_PATH
                }
            },
        }

        load_cookies(options, temp_dir)

        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(url, download=False)

    

# ================= MESSAGE HANDLER =================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()

    if not url.startswith(("https://", "http://")):
        await update.message.reply_text(
            "❌ لطفاً لینک معتبر ارسال کن."
        )
        return

    msg = await update.message.reply_text(
        "⏳ در حال بررسی لینک..."
    )

    try:
        info = await asyncio.to_thread(
            extract_info,
            url
        )

        title = info.get("title") or "Media"

        context.user_data["url"] = url

        keyboard = [
            [
                InlineKeyboardButton(
                    "1080p", callback_data="1080"
                ),
                InlineKeyboardButton(
                    "720p", callback_data="720"
                ),
                InlineKeyboardButton(
                    "480p", callback_data="480"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 دانلود MP3",
                    callback_data="mp3"
                )
            ]
        ]

        await msg.edit_text(
            f"📌 {title}\n\n"
            "کیفیت مورد نظر را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.exception("Media extraction failed")

        await msg.edit_text(
            f"❌ خطای استخراج:\n\n{str(e)[:1200]}"
        )
# ================= DOWNLOAD ENGINE =================

def download_media(url, quality, folder):

    output = str(Path(folder) / "media.%(ext)s")

    if quality == "mp3":
        format_string = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }
        ]
    else:
        
        format_string = f"best[height<={quality}]/best"
        
        postprocessors = [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4"
            }
        ]

    options = {
    "format": format_string,
    "outtmpl": output,
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "socket_timeout": 30,
    "retries": 3,
    "fragment_retries": 3,
    "max_filesize": MAX_FILE_SIZE,
    "ffmpeg_location": FFMPEG_PATH,
    "postprocessors": postprocessors,
    "overwrites": True,

    "js_runtimes": {
        "deno": {
            "path": DENO_PATH
        }
    },
}
    load_cookies(options, folder)

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    files = [
        p for p in Path(folder).glob("media.*")
        if p.is_file()
        and not p.name.endswith((".part", ".ytdl"))
    ]

    if not files:
        raise Exception("فایل خروجی ساخته نشد.")

    result = max(files, key=lambda p: p.stat().st_mtime)

    if result.stat().st_size > MAX_FILE_SIZE:
        raise Exception("حجم فایل بیشتر از محدودیت تلگرام است.")

    return str(result)


# ================= BUTTON HANDLER =================

async def button_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    quality = query.data
    url = context.user_data.get("url")

    if quality not in ("1080", "720", "480", "mp3"):
        return

    if not url:
        await query.edit_message_text(
            "❌ لینک منقضی شده است. دوباره لینک را بفرست."
        )
        return

    label = "MP3" if quality == "mp3" else quality + "p"

    await query.edit_message_text(
        f"⏳ در حال دانلود با کیفیت {label}..."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:

            filename = await asyncio.to_thread(
                download_media,
                url,
                quality,
                folder
            )

            with open(filename, "rb") as media:

                if quality == "mp3":
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=media,
                        title=Path(filename).stem
                    )

                elif Path(filename).suffix.lower() == ".mp4":
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=media,
                        supports_streaming=True
                    )

                else:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=media
                    )

        await query.edit_message_text(
            "✅ دانلود و ارسال با موفقیت انجام شد."
        )

    except Exception as error:
        logger.exception("Download failed")

        error_text = str(error)

        await query.edit_message_text(
            "❌ دانلود ناموفق بود.\n\n"
            + error_text[:700]
        )


# ================= ERROR HANDLER =================

async def error_handler(update, context):
    logger.error(
        "Unhandled exception",
        exc_info=context.error
    )


# ================= MAIN =================

def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    if not HOSTNAME:
        raise RuntimeError(
            "RENDER_EXTERNAL_HOSTNAME is missing. "
            "Deploy this application as a Render Web Service."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_callback)
    )

    app.add_error_handler(error_handler)

    webhook_url = (
        f"https://{HOSTNAME}/{WEBHOOK_PATH}"
    )

    logger.info("Starting Trendify Media Downloader")
    logger.info("Webhook URL: %s", webhook_url)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=webhook_url,
        secret_token=WEBHOOK_SECRET,
        bootstrap_retries=-1
    )


if __name__ == "__main__":
    main()
