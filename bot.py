import os
import io
import logging
import requests
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # set this in Railway variables

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome to *dawud035bot*!\n\n"
        "Here's what I can do:\n"
        "🔗 /shorten <url> — shorten a long link\n"
        "🖼 Send me a photo — I'll compress it and give you conversion options\n"
        "🔄 /convert <jpg|png|webp> — convert your last sent photo to a format\n\n"
        "Just try one of the commands above!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def shorten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /shorten <url>\nExample: /shorten https://example.com")
        return

    long_url = context.args[0]
    try:
        resp = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": long_url},
            timeout=10,
        )
        if resp.status_code == 200 and resp.text.startswith("http"):
            await update.message.reply_text(f"✅ Shortened link:\n{resp.text}")
        else:
            await update.message.reply_text("⚠️ Couldn't shorten that URL. Make sure it's valid (starts with http/https).")
    except requests.RequestException as e:
        logger.error(f"Shorten error: {e}")
        await update.message.reply_text("⚠️ Something went wrong while shortening the link. Try again later.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # highest resolution
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    # store in user_data so /convert can use it later
    context.user_data["last_image"] = bytes(file_bytes)

    # Send back a compressed JPEG version by default
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=60, optimize=True)
    buffer.seek(0)

    await update.message.reply_photo(
        photo=buffer,
        caption="✅ Compressed version (JPEG, quality 60).\n"
                "Want a different format? Use /convert png or /convert webp",
    )


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "last_image" not in context.user_data:
        await update.message.reply_text("Please send me a photo first, then use /convert <format>.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /convert <jpg|png|webp>")
        return

    fmt = context.args[0].lower()
    fmt_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}

    if fmt not in fmt_map:
        await update.message.reply_text("Supported formats: jpg, png, webp")
        return

    image_bytes = context.user_data["last_image"]
    image = Image.open(io.BytesIO(image_bytes))

    if fmt_map[fmt] == "JPEG":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format=fmt_map[fmt])
    buffer.seek(0)
    buffer.name = f"converted.{fmt}"

    await update.message.reply_document(document=buffer, caption=f"✅ Converted to {fmt.upper()}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("shorten", shorten))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot started polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
