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

send("🤖 Тест: бот запустился!")

# Загружаем старую базу (если есть)
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        old_products = json.load(f)
else:
    old_products = {}

# Парсим сайт
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    r = requests.get(SITE_URL, headers=headers, timeout=20)
    
    print(f"Status code: {r.status_code}")
    print(f"Page length: {len(r.text)}")
    
    # Сохраняем HTML для отладки
    with open("page_debug.html", "w", encoding="utf-8") as f:
        f.write(r.text[:50000])  # Первые 50k символов
    
    soup = BeautifulSoup(r.text, "lxml")
    # TSUM использует /item/ а не /product/
    cards = soup.select("a[href*='/item/ITEM']")
    
    print(f"Найдено карточек: {len(cards)}")
    
    new_products = {}
    
    for card in cards:
        url = "https://collect.tsum.ru" + card["href"]
        
        # Пытаемся найти название (бренд + цена как идентификатор)
        brand = card.find("img", {"data-brandlogo": "true"})
        brand_name = brand["alt"] if brand else "Товар"
        
        # Проверяем наличие по цене (если цены нет - товар продан)
        price = card.find("span", class_=lambda x: x and "price" in x.lower())
        in_stock = price is not None
        
        new_products[url] = {
            "title": brand_name,
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
