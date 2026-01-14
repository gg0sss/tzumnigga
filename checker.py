import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SITE_URL = "https://collect.tsum.ru/"
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_FILE = "products.json"

def send(msg):
    """Отправить сообщение в Telegram"""
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

# Загружаем старую базу (если есть)
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        old_products = json.load(f)
else:
    old_products = {}

# Парсим сайт
try:
    r = requests.get(SITE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    soup = BeautifulSoup(r.text, "lxml")
    cards = soup.select("a[href*='/product/']")
    
    new_products = {}
    
    for card in cards:
        url = "https://collect.tsum.ru" + card["href"]
        # Достаём название товара
        title_elem = card.select_one(".product-card__title, h3, .title")
        title = title_elem.get_text(strip=True) if title_elem else "Товар"
        
        text = card.get_text().lower()
        in_stock = not any(x in text for x in ["нет в наличии", "продано", "sold out"])
        
        new_products[url] = {
            "title": title,
            "in_stock": in_stock
        }
        
        # Проверяем: был в наличии, а теперь НЕТ
        if url in old_products:
            if old_products[url]["in_stock"] and not in_stock:
                send(f"❌ ПРОДАНО\n\n{title}\n\n{url}")
    
    # Сохраняем новую базу
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_products, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Проверено товаров: {len(new_products)}")

except Exception as e:
    send(f"⚠️ Ошибка парсинга:\n{str(e)}")
    print(f"ERROR: {e}")
