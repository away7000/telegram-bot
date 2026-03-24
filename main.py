import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("8648654865:AAEsThOEU0YiR51MW_C0ptH7DOtIael5kzM")
OPENROUTER_API_KEY = os.getenv("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")

def ask_ai(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "Kamu adalah AI crypto assistant"},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply = ask_ai(user_text)
    await update.message.reply_text(reply)

app = ApplicationBuilder().token("8648654865:AAEsThOEU0YiR51MW_C0ptH7DOtIael5kzM").build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan di Railway...")
app.run_polling()
