import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام حسین عزیز! 🚀\nلینک ویدیو (یوتیوب، اینستاگرام، تیک‌تاک و...) رو بفرست تا با کیفیت دلخواه برات دانلود کنم!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("لطفاً یک لینک معتبر بفرست.")
        return

    msg = await update.message.reply_text("⏳ در حال دریافت اطلاعات ویدیو...")

    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            context.user_data['url'] = url

            keyboard = [
                [
                    InlineKeyboardButton("🎬 1080p", callback_data="1080"),
                    InlineKeyboardButton("🎬 720p", callback_data="720"),
                    InlineKeyboardButton("🎬 480p", callback_data="480")
                ],
                [
                    InlineKeyboardButton("🎵 فقط صوت (MP3)", callback_data="mp3")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await msg.edit_text(f"📌 **{title}**\n\nلطفاً کیفیت مورد نظر را انتخاب کن:", reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text("❌ خطا در دریافت اطلاعات ویدیو. ممکن است لینک خصوصی یا نامعتبر باشد.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality = query.data
    url = context.user_data.get('url')

    if not url:
        await query.edit_message_text("❌ لینک یافت نشد. لطفاً دوباره لینک را بفرست.")
        return

    await query.edit_message_text(f"⏳ در حال دانلود و ارسال ویدیو با کیفیت {quality}...")

    filename = f"video_{query.from_user.id}.mp4"

    try:
        if quality == "mp3":
            format_str = "bestaudio/best"
            filename = f"audio_{query.from_user.id}.mp3"
        else:
            format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"

        ydl_opts = {
            'format': format_str,
            'outtmpl': filename,
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # ارسال فایل به تلگرام
        with open(filename, 'rb') as video_file:
            if quality == "mp3":
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=video_file)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=video_file)

        # پاک کردن فایل بعد از ارسال
        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ خطا در دانلود: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
