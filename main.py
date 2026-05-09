import os
import logging
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

logging.basicConfig(level=logging.INFO)

KASB, SHAHAR, MAOSH = range(3)
user_data = {}

SHAHARLAR = [
    ["Toshkent", "Samarqand"],
    ["Namangan", "Andijon"],
    ["Buxoro", "Farg'ona"],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men Ish Qidiruvchi Botman!\n\n"
        "OLX va HH.uz ga havola va maslahat beraman.\n\n"
        "/qidir — ish qidirish\n"
        "/start — bosh sahifa"
    )

async def qidir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💼 Qaysi kasbda ish qidiryapsiz?\n\nMasalan: haydovchi, sotuvchi, dasturchi")
    return KASB

async def kasb_oldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"kasb": update.message.text}
    markup = ReplyKeyboardMarkup(SHAHARLAR, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("📍 Qaysi shahar?", reply_markup=markup)
    return SHAHAR

async def shahar_oldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["shahar"] = update.message.text
    await update.message.reply_text("💰 Kutilgan maosh? (yoki /otkazib_ket)")
    return MAOSH

async def maosh_oldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["maosh"] = update.message.text
    await qidirish(update, context)
    return ConversationHandler.END

async def otkazib_ket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["maosh"] = ""
    await qidirish(update, context)
    return ConversationHandler.END

async def qidirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    kasb = user_data[uid]["kasb"]
    shahar = user_data[uid]["shahar"]
    maosh = user_data[uid].get("maosh", "")

    await update.message.reply_text(f"🔍 {kasb} — {shahar} bo'yicha qidirilmoqda...")

    olx = f"https://www.olx.uz/rabota/?search%5Bq%5D={kasb.replace(' ', '+')}"
    hh = f"https://hh.uz/search/vacancy?text={kasb.replace(' ', '+')}"

    prompt = f"""O'zbekistonda "{kasb}" kasbi bo'yicha "{shahar}" shahrida ish haqida qisqa ma'lumot ber.
{f"Maosh: {maosh}" if maosh else ""}

Quyidagilarni yoz:
1. Bu kasb uchun o'rtacha maosh Toshkentda
2. Asosiy talablar (2-3 ta)
3. Qidiruv havolalari:
   OLX: {olx}
   HH.uz: {hh}
4. 2 ta amaliy maslahat

O'zbek tilida, qisqa yoz."""

    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(e)
        await update.message.reply_text(
            f"✅ Qidiruv havolalari:\n\n"
            f"🔗 OLX: {olx}\n\n"
            f"🔗 HH.uz: {hh}\n\n"
            "Yana qidirish: /qidir"
        )

async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. /qidir bilan qayta boshlang.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("qidir", qidir)],
        states={
            KASB: [MessageHandler(filters.TEXT & ~filters.COMMAND, kasb_oldi)],
            SHAHAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, shahar_oldi)],
            MAOSH: [
                CommandHandler("otkazib_ket", otkazib_ket),
                MessageHandler(filters.TEXT & ~filters.COMMAND, maosh_oldi),
            ],
        },
        fallbacks=[CommandHandler("bekor", bekor)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    print("Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
