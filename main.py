import requests
import os
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# 🔐 ENV
TELEGRAM_TOKEN = "8648654865:AAEsThOEU0YiR51MW_C0ptH7DOtIael5kzM"
GROQ_API_KEY = "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"

# 🌐 WEB3 SETUP
INFURA_URL = "https://mainnet.infura.io/v3/4adf5125bbfa4be0b7ef420369a4fb84"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# ================= AI FUNCTION =================
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
                {"role": "system", "content": "Kamu adalah AI crypto assistant"},
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
        return f"Error: {str(e)}"

# ================= WALLET FUNCTION =================
def get_balance(address):
    try:
        balance = w3.eth.get_balance(address)
        eth = w3.from_wei(balance, 'ether')
        return f"Saldo: {eth} ETH"
    except Exception as e:
        return f"Error wallet: {str(e)}"

# ================= HANDLERS =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply = ask_ai(user_text)
    await update.message.reply_text(reply)

async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        address = context.args[0]
        result = get_balance(address)
        await update.message.reply_text(result)
    except:
        await update.message.reply_text("Format: /saldo 0xAddress")

# ================= MAIN =================
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# 👉 command wallet
app.add_handler(CommandHandler("saldo", saldo_command))

# 👉 AI chat
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan + wallet aktif 🚀")
app.run_polling()
