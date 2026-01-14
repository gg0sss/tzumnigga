import requests
import sqlite3
import os
from bs4 import BeautifulSoup
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://collect.tsum.ru/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

conn = sqlite3.connect("data.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS products (
    url TEXT PRIMARY KEY,
    in_stock INTEGER
)
""")

r = requests.get(URL, headers=HEADERS, timeout=20)
soup = BeautifulSoup(r.text, "lxml")

cards = soup.select("a[href*='/product/']")

for card in cards:
    url = "https://collect.tsum.ru" + card["href"]
    text = card.get_text().lower()

    in_stock = not any(x in text for x in ["нет в наличии", "продано"])

    c.execute("SELECT in_stock FROM products WHERE url=?", (url,))
    row = c.fetchone()

    if row and row[0] == 1 and not in_stock:
        send(f"❌ SOLD OUT\n\n{url}")

    c.execute(
        "INSERT OR REPLACE INTO products VALUES (?, ?)",
        (url, int(in_stock))
    )

conn.commit()
conn.close()
