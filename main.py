import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("8648654865:AAEsThOEU0YiR51MW_C0ptH7DOtIael5kzM")
OPENROUTER_API_KEY = os.getenv("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")

def ask_ai(prompt):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "meta-llama/llama-3-8b-instruct",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        print(result)

        if "choices" not in result:
            return f"AI Error: {result}"

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error system: {str(e)}"

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
