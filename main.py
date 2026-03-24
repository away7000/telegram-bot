import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8648654865:AAEsThOEU0YiR51MW_C0ptH7DOtIael5kzM"
GROQ_API_KEY = "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"

def ask_ai(prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Kamu adalah AI assistant yang pintar dan membantu"},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        print(result)  # debug log

        if "choices" not in result:
            return f"AI Error: {result}"

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error system: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply = ask_ai(user_text)
    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan di Railway...")
app.run_polling()
