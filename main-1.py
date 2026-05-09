import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import google.generativeai as genai

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHAHARLAR = [
    ["🏙 Toshkent", "🌆 Samarqand"],
    ["🌇 Namangan", "🌃 Andijon"],
    ["🌉 Buxoro", "🌁 Farg'ona"],
    ["🔙 Orqaga"]
]

KASB, SHAHAR, MAOSH = range(3)

user_data_store = {}

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Men *Ish Qidiruvchi Bot* man 🤖\n"
        "OLX, HH.uz va boshqa saytlardan ish topib beraman.\n\n"
        "Boshlash uchun /qidir buyrug'ini yuboring!",
        parse_mode="Markdown"
    )

# --- QIDIR ---
async def qidir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 *Qaysi kasbda ish qidiryapsiz?*\n\n"
        "Masalan: _haydovchi_, _dasturchi_, _sotuvchi_, _oshpaz_...",
        parse_mode="Markdown"
    )
    return KASB

async def kasb_oldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_user.id] = {"kasb": update.message.text}
    
    markup = ReplyKeyboardMarkup(SHAHARLAR, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"✅ Kasb: *{update.message.text}*\n\n📍 Qaysi shahardan ish qidirasiz?",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return SHAHAR

async def shahar_oldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shahar = update.message.text.replace("🏙 ", "").replace("🌆 ", "").replace(
        "🌇 ", "").replace("🌃 ", "").replace("🌉 ", "").replace("🌁 ", "")
    
    user_data_store[update.effective_user.id]["shahar"] = shahar
    
    await update.message.reply_text(
        f"✅ Shahar: *{shahar}*\n\n"
        "💰 Kutilayotgan maosh? (ixtiyoriy)\n"
        "Masalan: _3 000 000 so'm_ yoki /otkazib_ket",
        parse_mode="Markdown"
    )
    return MAOSH

async def maosh_oldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data_store[uid]["maosh"] = update.message.text
    await qidirishni_boshlash(update, context, uid)
    return ConversationHandler.END

async def maoshsiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data_store[uid]["maosh"] = None
    await qidirishni_boshlash(update, context, uid)
    return ConversationHandler.END

async def qidirishni_boshlash(update, context, uid):
    data = user_data_store.get(uid, {})
    kasb = data.get("kasb", "")
    shahar = data.get("shahar", "Toshkent")
    maosh = data.get("maosh", "")

    maosh_qism = f", maosh {maosh}" if maosh else ""
    
    await update.message.reply_text(
        f"🔍 *{kasb}* bo'yicha *{shahar}* da ish qidirilmoqda...\n\n⏳ Bir oz kuting!",
        parse_mode="Markdown"
    )

    olx_link = f"https://www.olx.uz/rabota/?search%5Bfilter_str_city_id%5D={shahar.lower()}&search%5Bq%5D={kasb.replace(' ', '+')}"
    hh_link = f"https://hh.uz/search/vacancy?text={kasb.replace(' ', '+')}&area=84"

    prompt = f"""
O'zbekistonda "{kasb}" kasbi bo'yicha "{shahar}" shahrida{maosh_qism} ish haqida ma'lumot ber.

Quyidagi formatda yoz (Telegram uchun):

Bu kasb haqida qisqa ma'lumot va o'rtacha maosh (O'zbekistonda).

Keyin bu kasb uchun odatda qanday talablar bo'lishini yoz.

So'ngra quyidagi havolalardan qidirish tavsiyasi ber:
🔗 OLX: {olx_link}
🔗 HH.uz: {hh_link}

Oxirida 2-3 ta amaliy maslahat ber.
O'zbek tilida yoz.
"""

    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        javob = response.text

        await update.message.reply_text(
            f"✅ *{kasb.upper()} — {shahar}* bo'yicha natijalar:\n\n{javob}",
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "🔄 Yana qidirish uchun: /qidir\n"
            "🏠 Bosh sahifa: /start"
        )
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Qayta urinib ko'ring: /qidir"
        )

async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi. /qidir bilan qayta boshlang.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("qidir", qidir)],
        states={
            KASB: [MessageHandler(filters.TEXT & ~filters.COMMAND, kasb_oldi)],
            SHAHAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, shahar_oldi)],
            MAOSH: [
                CommandHandler("otkazib_ket", maoshsiz),
                MessageHandler(filters.TEXT & ~filters.COMMAND, maosh_oldi)
            ],
        },
        fallbacks=[CommandHandler("bekor", bekor)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
