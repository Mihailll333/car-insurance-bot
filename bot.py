import os
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
openai.api_key = os.getenv("OPENAI_KEY")

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для покупки автостраховки.\n"
        "Пожалуйста, отправь мне фото паспорта."
    )
    user_data[update.effective_user.id] = {"step": "passport"}

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"{uid}_{user_data[uid]['step']}.jpg"
    await photo_file.download_to_drive(file_path)

    step = user_data[uid]['step']
    if step == "passport":
        user_data[uid]["passport"] = file_path
        user_data[uid]["step"] = "car_doc"
        await update.message.reply_text("✅ Паспорт получен. Теперь отправь фото техпаспорта.")
    elif step == "car_doc":
        user_data[uid]["car_doc"] = file_path
        user_data[uid]["step"] = "confirm_data"
        # Мокаем Mindee
        extracted = {
            "Имя": "Иван",
            "Фамилия": "Иванов",
            "Госномер": "AA1234BB",
            "VIN": "WVWZZZ1JZXW000000"
        }
        user_data[uid]["data"] = extracted
        summary = "\n".join(f"{k}: {v}" for k, v in extracted.items())
        await update.message.reply_text(f"🔍 Я извлек следующие данные:\n{summary}\n\nВсе верно? (да/нет)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip().lower()
    step = user_data.get(uid, {}).get("step")

    if step == "confirm_data":
        if text == "да":
            user_data[uid]["step"] = "price"
            await update.message.reply_text("💵 Стоимость страховки — 100 USD. Вас устраивает? (да/нет)")
        elif text == "нет":
            user_data[uid]["step"] = "passport"
            await update.message.reply_text("Пожалуйста, отправь фото паспорта заново.")
        else:
            await update.message.reply_text("Пожалуйста, ответь 'да' или 'нет'.")
    elif step == "price":
        if text == "да":
            user_data[uid]["step"] = "done"
            policy = await generate_dummy_policy(user_data[uid]["data"])
            await update.message.reply_text(f"📄 Вот ваша страховка:\n\n{policy}")
        elif text == "нет":
            await update.message.reply_text("Извините, цена фиксирована — 100 USD.")
        else:
            await update.message.reply_text("Пожалуйста, ответь 'да' или 'нет'.")

async def generate_dummy_policy(data: dict) -> str:
    summary = "\n".join(f"{k}: {v}" for k, v in data.items())
    prompt = (
        f"Создай шаблон страхового полиса на основании следующих данных:\n{summary}\n"
        "Полис должен быть коротким, но официальным."
    )

    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()
