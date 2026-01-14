import requests
import sqlite3
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

SITE_URL = "https://collect.tsum.ru/"
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send(msg):
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

# --- 1. Ответ на /start ---
updates = requests.get(f"{TG_API}/getUpdates").json()

for upd in updates.get("result", []):
    msg = upd.get("message", {})
    text = msg.get("text", "")
    chat = msg.get("chat", {}).get("id")

    if text == "/start" and str(chat) == CHAT_ID:
        send(
            "🤖 TSUM SOLD OUT BOT\n\n"
            "Я слежу за TSUM Collect.\n"
            "Напишу, когда товар уйдёт в sold-out."
        )

# --- 2. SOLD OUT логика ---
conn = sqlite3.connect("data.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS products (
    url TEXT PRIMARY KEY,
    in_stock INTEGER
)
""")

r = requests.get(SITE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
soup = BeautifulSoup(r.text, "lxml")

cards = soup.select("a[href*='/product/']")

for card in cards:
    url = "https://collect.tsum.ru" + card["href"]
    text = card.get_text().lower()

    in_stock = not any(x in text for x in ["нет в наличии", "продано"])

    c.execute("SELECT in_stock FROM products WHERE url=?", (url,))
    row = c.fetchone()

    if row and row[0] == 1 and not in_stock:
        send(f"❌ SOLD OUT\n{url}")

    c.execute(
        "INSERT OR REPLACE INTO products VALUES (?, ?)",
        (url, int(in_stock))
    )

conn.commit()
conn.close()
