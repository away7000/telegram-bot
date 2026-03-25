import requests
import os
import sqlite3
import os
from cryptography.fernet import Fernet
from eth_account import Account
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

conn = sqlite3.connect("wallets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS wallets (
    user_id TEXT PRIMARY KEY,
    address TEXT,
    private_key TEXT
)
""")
conn.commit()

SECRET_KEY = os.getenv("SECRET_KEY")
cipher = Fernet(SECRET_KEY)

RPCS = {
    "eth": "https://eth.api.pocket.network",
    "bsc": "https://bsc.api.pocket.network",
    "arb": "https://arb-one.api.pocket.network",
    "base": "https://mainnet.base.org"
}

CHAIN_IDS = {
    "eth": 1,
    "bsc": 56,
    "arb": 42161,
    "base": 8453
}

# 🔐 ENV
TELEGRAM_TOKEN = "8648654865:AAEsThOEU0YiR51MW_C0ptH7DOtIael5kzM"
GROQ_API_KEY = "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"

# 🌐 WEB3 SETUP
INFURA_URL = "https://mainnet.infura.io/v3/4adf5125bbfa4be0b7ef420369a4fb84"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# ================= AI FUNCTION =================
def ask_ai(user_text):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        }
    )

    data = response.json()
    print("AI RESPONSE:", data)  # debug

    if "choices" not in data:
        return f"AI Error: {data}"

    return data["choices"][0]["message"]["content"]

# ================= WALLET FUNCTION =================
def get_balance(address):
    try:
        balance = w3.eth.get_balance(address)
        eth = w3.from_wei(balance, 'ether')
        return f"Saldo: {eth} ETH"
    except Exception as e:
        return f"Error wallet: {str(e)}"
        
def create_wallet(user_id):
    acct = Account.create()

    save_wallet(user_id, acct.address, acct.key.hex())

    return f"""
Wallet berhasil dibuat!

Address:
{acct.address}

⚠️ Private key disimpan aman
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
            'chainId': CHAIN_IDS[chain]  # 🔥 WAJIB
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)

        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return f"✅ TX Sent!\nHash: {w3.to_hex(tx_hash)}"

    except Exception as e:
        return f"Error: {str(e)}"

def save_wallet(user_id, address, private_key):
    encrypted_pk = cipher.encrypt(private_key.encode()).decode()

    cursor.execute(
        "INSERT OR REPLACE INTO wallets (user_id, address, private_key) VALUES (?, ?, ?)",
        (user_id, address, encrypted_pk)
    )
    conn.commit()


def get_wallet(user_id):
    cursor.execute("SELECT address, private_key FROM wallets WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        address, encrypted_pk = row
        private_key = cipher.decrypt(encrypted_pk.encode()).decode()
        return address, private_key

    return None, None

def save_wallet(user_id, address, private_key):
    print("SAVE WALLET:", user_id, address)

    encrypted_pk = cipher.encrypt(private_key.encode()).decode()

    cursor.execute(
        "INSERT OR REPLACE INTO wallets VALUES (?, ?, ?)",
        (user_id, address, encrypted_pk)
    )
    conn.commit()

def load_skill(name):
    with open(f"skills/{name}.md", "r") as f:
        return f.read()

def route_skill(user_text):
    text = user_text.lower()

    if any(x in text for x in ["buy", "sell", "token", "price", "trading"]):
        return "trading"

    elif any(x in text for x in ["wallet", "send", "address", "balance"]):
        return "wallet"

    else:
        return "general"
        
# ================= HANDLERS =================
async def ask_command(update, context):
    try:
        user_text = " ".join(context.args)

        if not user_text:
            await update.message.reply_text("Tulis pertanyaan setelah /ask")
            return

        reply = ask_ai(user_text)

        await update.message.reply_text(reply)

    except Exception as e:
        print("ERROR /ask:", e)
        await update.message.reply_text(f"Error: {str(e)}")

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
    user_id = str(update.effective_user.id)
    result = create_wallet(user_id)
    await update.message.reply_text(result)

async def send_command(update, context):
    try:
        user_id = str(update.effective_user.id)

        address, private_key = get_wallet(user_id)

        if not private_key:
            await update.message.reply_text("Buat wallet dulu /createwallet")
            return

        chain = context.args[0]
        to_address = context.args[1]
        amount = context.args[2]

        result = send_eth(chain, private_key, to_address, amount)
        await update.message.reply_text(result)

    except:
        await update.message.reply_text("Format:\n/send eth 0xReceiver 0.01")
        
async def buy_command(update, context):
    try:
        user_id = str(update.effective_user.id)

        address, private_key = get_wallet(user_id)

        if not private_key:
            await update.message.reply_text("Buat wallet dulu /createwallet")
            return

        chain = context.args[0]
        token = context.args[1]
        amount = context.args[2]

        result = swap_eth_to_token(chain, private_key, token, amount)
        await update.message.reply_text(result)

    except:
        await update.message.reply_text("Format:\n/buy eth TOKEN 0.01")

async def mywallet_command(update, context):
    try:
        print("MYWALLET KE TRIGGER")  # debug

        user_id = str(update.effective_user.id)

        address, _ = get_wallet(user_id)

        print("ADDRESS:", address)  # debug

        if not address:
            await update.message.reply_text("Belum punya wallet. /createwallet dulu")
            return

        await update.message.reply_text(f"""
💼 Wallet Kamu:

Address:
{address}
""")

    except Exception as e:
        print("ERROR MYWALLET:", e)
        await update.message.reply_text(f"Error: {str(e)}")
        

async def exportpk_command(update, context):
    user_id = str(update.effective_user.id)

    address, private_key = get_wallet(user_id)

    if not private_key:
        await update.message.reply_text("Wallet belum ada")
        return

    await update.message.reply_text(f"""
⚠️ PRIVATE KEY (JANGAN DIBAGIKAN):

{private_key}
""")
    
# ================= MAIN =================
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# 👉 command wallet
app.add_handler(CommandHandler("createwallet", create_wallet_command))
app.add_handler(CommandHandler("mywallet", mywallet_command))
app.add_handler(CommandHandler("exportpk", exportpk_command))
app.add_handler(CommandHandler("send", send_command))
app.add_handler(CommandHandler("buy", buy_command))
app.add_handler(CommandHandler("ask", ask_command))

# 👉 AI chat
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan + wallet aktif 🚀")
app.run_polling()
