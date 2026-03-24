import requests
import os
from eth_account import Account
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

RPCS = {
    "eth": "https://eth.api.pocket.network",
    "bsc": "https://bsc.api.pocket.network",
    "arb": "https://arb-one.api.pocket.network",
    "base": "https://mainnet.base.org"
}

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
        
def create_wallet():
    acct = Account.create()
    
    address = acct.address
    private_key = acct.key.hex()

    return f"""
🔥 Multi-Chain Wallet

Address:
{address}

Network Support:
✅ ETH
✅ BSC
✅ ARBITRUM
✅ BASE

Private Key:
{private_key}
"""

def send_eth(chain, private_key, to_address, amount):
    try:
        w3 = Web3(Web3.HTTPProvider(RPCS[chain]))

        account = w3.eth.account.from_key(private_key)
        sender = account.address

        nonce = w3.eth.get_transaction_count(sender)

        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(float(amount), 'ether'),
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)

        # ✅ FIX DI SINI
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return f"✅ TX Sent!\nHash: {w3.to_hex(tx_hash)}"

    except Exception as e:
        return f"Error: {str(e)}"
        
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

async def create_wallet_command(update, context):
    wallet = create_wallet()
    await update.message.reply_text(wallet)

async def send_command(update, context):
    try:
        chain = context.args[0]
        private_key = context.args[1]
        to_address = context.args[2]
        amount = context.args[3]

        result = send_eth(chain, private_key, to_address, amount)
        await update.message.reply_text(result)

    except:
        await update.message.reply_text("Format:\n/send eth PRIVATE_KEY TO_ADDRESS AMOUNT")
        
# ================= MAIN =================
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# 👉 command wallet
app.add_handler(CommandHandler("saldo", saldo_command))
app.add_handler(CommandHandler("createwallet", create_wallet_command))
app.add_handler(CommandHandler("send", send_command))

# 👉 AI chat
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan + wallet aktif 🚀")
app.run_polling()
