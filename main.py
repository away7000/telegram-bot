import requests
import os
import sqlite3
import os
import matplotlib.pyplot as plt
from cryptography.fernet import Fernet
from eth_account import Account
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

SYSTEM_PROMPT = """
Kamu adalah AI assistant.

WAJIB:
- Selalu jawab dalam Bahasa Indonesia
- Gunakan bahasa santai tapi profesional
- Jawaban harus jelas, ringkas, dan langsung ke inti
- Jangan gunakan Bahasa Inggris kecuali istilah teknis (BTC, trading, dll)
- kayaknya
- kemungkinan
- sebaiknya

Jika user pakai bahasa lain, tetap jawab dalam Bahasa Indonesia.
"""

conn = sqlite3.connect("wallets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

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
def ask_ai(user_id, user_text):
    skill_name = route_skill(user_text)
    skill_prompt = load_skill(skill_name)

    memory = get_memory(user_id)

    messages = [
        {"role": "system",
        "content": SYSTEM_PROMPT + "\n\n" + skill_prompt}
    ] + memory + [
        {"role": "user", "content": user_text}
    ]

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages
        }
    )

    data = response.json()

    if "choices" not in data:
        return f"AI Error: {data}"

    reply = data["choices"][0]["message"]["content"]

    # 🔥 simpan ke database
    save_memory(user_id, "user", user_text)
    save_memory(user_id, "assistant", reply)

    return reply


# ================= WALLET FUNCTION =================
def save_skill_from_text(skill_name, content):
    with open(f"skills/{skill_name}.md", "w") as f:
        f.write(content)
        
def extract_coin_ai(user_text):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "Ekstrak hanya nama atau simbol mata uang kripto dari kalimat tersebut. جواب فقط nama coin saja. Contoh: 'ethereum', 'btc', 'solana'."
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ]
        }
    )

    data = response.json()

    if "choices" not in data:
        return None

    coin = data["choices"][0]["message"]["content"].strip().lower()

    return coin

def extract_asset_ai(user_text):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "Extract only the asset name (crypto or gold). Example: btc, eth, sol, gold."
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ]
        }
    )

    data = response.json()

    if "choices" not in data:
        return None

    return data["choices"][0]["message"]["content"].strip().lower()
    
def search_coin(query):
    url = f"https://api.coingecko.com/api/v3/search?query={query}"
    res = requests.get(url).json()

    coins = res.get("coins", [])

    if not coins:
        return None

    return coins[0]["id"]

def get_price_dynamic(query):
    coin_id = search_coin(query)

    if not coin_id:
        return "❌ Coin tidak ditemukan"

    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    res = requests.get(url).json()

    if coin_id not in res:
        return "❌ Gagal ambil harga"

    price = res[coin_id]["usd"]

    return f"💰 Harga {query.upper()}: ${price}"

def get_metal_price(metal):
    metals = {
        "emas": "gold",
        "gold": "gold",
        "xau": "gold",
        "perak": "silver",
        "silver": "silver",
        "xag": "silver"
    }

    m = metals.get(metal.lower())

    if not m:
        return None

    url = "https://api.metals.live/v1/spot"

    try:
        res = requests.get(url).json()

        for item in res:
            if m in item:
                price = item[m]
                return f"💰 Harga {m.upper()}: ${price}/oz"

        return "❌ Gagal ambil harga"

    except:
        return "❌ Error ambil data"

def get_gold_idr():
    try:
        # 🔥 ambil harga emas (PAXG)
        gold_res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=pax-gold&vs_currencies=usd",
            timeout=5
        ).json()

        if "pax-gold" not in gold_res:
            return "❌ Gagal ambil harga emas"

        gold_usd = gold_res["pax-gold"]["usd"]

        # 🔥 ambil kurs USD → IDR
        forex_res = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=5
        ).json()

        # ✅ VALIDASI
        if forex_res.get("result") != "success":
            return "❌ Gagal ambil kurs USD/IDR"

        usd_idr = forex_res["rates"]["IDR"]

        # 🔥 konversi ke rupiah / gram
        price_idr_per_gram = (gold_usd * usd_idr) / 31.1035

        return f"""
🥇 Harga Emas (approx):

USD/oz : ${gold_usd}
USD/IDR : {usd_idr}

💰 IDR/gram : Rp {int(price_idr_per_gram):,}
"""

    except Exception as e:
        print("ERROR GOLD:", e)
        return f"❌ Error: {str(e)}"

def convert_usd_to_idr(amount):
    try:
        res = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=5
        ).json()

        if res.get("result") != "success":
            return "❌ Gagal ambil kurs"

        rate = res["rates"]["IDR"]
        result = amount * rate

        return f"💱 ${amount} = Rp {int(result):,}"

    except Exception as e:
        return f"❌ Error: {str(e)}"
        
def get_forex(pair="USDIDR"):
    url = "https://api.exchangerate.host/latest?base=USD&symbols=IDR"

    res = requests.get(url).json()
    rate = res["rates"]["IDR"]

    return f"💱 USD/IDR: {rate}"

def get_gold_chart():
    try:
        url = "https://api.coingecko.com/api/v3/coins/gold/market_chart?vs_currency=usd&days=7"
        data = requests.get(url).json()

        prices = data["prices"]

        x = [p[0] for p in prices]
        y = [p[1] for p in prices]

        plt.figure()
        plt.plot(x, y)

        file_path = "gold_chart.png"
        plt.savefig(file_path)
        plt.close()

        return file_path

    except Exception as e:
        print("Chart error:", e)
        return None
def get_chart(asset):
    try:
        # 🔹 mapping asset
        if asset in ["emas", "gold"]:
            coin_id = "pax-gold"
        else:
            coin_id = search_coin(asset)

        if not coin_id:
            return None, None

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=7"
        data = requests.get(url).json()

        prices = data.get("prices", [])

        if not prices:
            return None, None

        x = [p[0] for p in prices]
        y = [p[1] for p in prices]

        plt.figure()
        plt.plot(x, y)

        file_path = f"{asset}_chart.png"
        plt.savefig(file_path)
        plt.close()

        return file_path, y[-1]  # last price

    except Exception as e:
        print("Chart error:", e)
        return None, None

def analyze_chart(asset, price):
    prompt = f"""
Analisa aset berikut:

Aset: {asset}
Harga sekarang: {price}

Berikan:
- Trend (naik/turun/sideways)
- Rekomendasi (beli/jual/tunggu)
- Risiko

Jawab dalam Bahasa Indonesia.
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a trading analyst."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    data = response.json()

    if "choices" not in data:
        return "❌ Gagal analisa"

    return data["choices"][0]["message"]["content"]

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

def save_memory(user_id, role, content):
    cursor.execute(
        "INSERT INTO memory (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()

def get_memory(user_id, limit=10):
    cursor.execute(
        "SELECT role, content FROM memory WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )

    rows = cursor.fetchall()

    # balik urutan biar kronologis
    rows.reverse()

    return [{"role": r[0], "content": r[1]} for r in rows]
    
# ================= HANDLERS =================
async def ask_command(update, context):
    try:
        user_id = str(update.effective_user.id)
        user_text = " ".join(context.args)

        if not user_text:
            await update.message.reply_text("Tulis pertanyaan setelah /ask")
            return

        reply = ask_ai(user_id, user_text)

        await update.message.reply_text(reply)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text(f"Error: {str(e)}")

async def reset_command(update, context):
    user_id = str(update.effective_user.id)

    cursor.execute("DELETE FROM memory WHERE user_id=?", (user_id,))
    conn.commit()

    await update.message.reply_text("Memory direset 🧠")
    
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
    
async def handle_message(update, context):
    try:
        user_id = str(update.effective_user.id)
        user_text = update.message.text.lower()

        # ================= CHART =================
        if "chart" in user_text or "grafik" in user_text:

            asset = extract_asset_ai(user_text)

            if not asset:
                await update.message.reply_text("❌ Gagal detect asset")
                return

            chart, price = get_chart(asset)

            if chart:
                analysis = analyze_chart(asset, price)

                await update.message.reply_photo(
                    photo=open(chart, "rb"),
                    caption=f"📈 Grafik {asset.upper()}"
                )

                await update.message.reply_text(analysis)
                return

            else:
                await update.message.reply_text("❌ Gagal ambil chart")
                return

        # ================= HARGA =================
        elif any(x in user_text for x in ["harga", "price", "berapa"]):

            if any(x in user_text for x in ["emas", "gold"]):
                reply = get_gold_idr()

            else:
                coin = extract_coin_ai(user_text)

                if not coin:
                    reply = "❌ Gagal detect coin"
                else:
                    reply = get_price_dynamic(coin)

        # ================= KONVERSI =================
        elif "usd" in user_text and "idr" in user_text:

            words = user_text.split()

            amount = 1
            for w in words:
                if w.replace(".", "", 1).isdigit():
                    amount = float(w)
                    break

            reply = convert_usd_to_idr(amount)

        # ================= AI =================
        else:
            reply = ask_ai(user_id, user_text)

        await update.message.reply_text(reply)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text(f"Error: {str(e)}")
        
async def addskill_command(update, context):
    try:
        text = " ".join(context.args)

        # format: /addskill defi | isi prompt
        name, content = text.split("|", 1)

        save_skill_from_text(name.strip(), content.strip())

        await update.message.reply_text(f"✅ Skill {name} berhasil ditambahkan")

    except Exception as e:
        await update.message.reply_text("Format salah. Gunakan: /addskill nama | isi")
        
# ================= MAIN =================
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# 👉 command wallet
app.add_handler(CommandHandler("createwallet", create_wallet_command))
app.add_handler(CommandHandler("mywallet", mywallet_command))
app.add_handler(CommandHandler("exportpk", exportpk_command))
app.add_handler(CommandHandler("send", send_command))
app.add_handler(CommandHandler("buy", buy_command))
app.add_handler(CommandHandler("ask", ask_command))
app.add_handler(CommandHandler("reset", reset_command))
app.add_handler(CommandHandler("addskill", addskill_command))

# 👉 AI chat
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan + wallet aktif 🚀")
app.run_polling()
