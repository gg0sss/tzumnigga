import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_FILE = "products.json"

# Категории для отслеживания
CATEGORIES = [
    "https://collect.tsum.ru/women/catalog/povsednevnye-sumki-82",
    "https://collect.tsum.ru/women/catalog/riukzaki-i-poiasnye-sumki-87",
    "https://collect.tsum.ru/women/catalog/dorozhnye-i-sportivnye-sumki-93",
    "https://collect.tsum.ru/women/catalog/klatchi-i-vechernie-sumki-90"
]

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

new_products = {}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

try:
    # Парсим каждую категорию
    for category_url in CATEGORIES:
        print(f"Парсинг: {category_url}")
        
        page = 1
        all_cards = []
        
        # Пробуем пагинацию - проходим по всем страницам
        while True:
            # Пробуем разные варианты пагинации
            url_with_page = f"{category_url}?page={page}"
            
            r = requests.get(url_with_page, headers=headers, timeout=20)
            print(f"  Страница {page}: Status {r.status_code}, Length: {len(r.text)}")
            
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("a[href*='/item/ITEM']")
            
            if not cards:
                # Если карточек нет - значит страницы закончились
                print(f"  Страниц найдено: {page - 1}")
                break
            
            all_cards.extend(cards)
            print(f"  Найдено карточек на странице: {len(cards)}")
            
            page += 1
            
            # Защита от бесконечного цикла
            if page > 50:
                print(f"  СТОП: достигнут лимит 50 страниц")
                break
        
        print(f"  ИТОГО карточек в категории: {len(all_cards)}")
        
        for card in all_cards:
            url = "https://collect.tsum.ru" + card["href"]
            
            # Пропускаем дубликаты
            if url in new_products:
                continue
            
            # Достаём бренд
            brand = card.find("img", {"data-brandlogo": "true"})
            brand_name = brand["alt"] if brand else "Товар"
            
            # Проверяем наличие по цене
            price = card.find("span", class_=lambda x: x and "price" in x.lower())
            in_stock = price is not None
            
            new_products[url] = {
                "title": brand_name,
                "in_stock": in_stock
            }
            
            # Проверяем: был в наличии, а теперь НЕТ
            if url in old_products:
                if old_products[url]["in_stock"] and not in_stock:
                    send(f"❌ ПРОДАНО\n\n{brand_name}\n\n{url}")
    
    # Сохраняем новую базу
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_products, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Всего проверено товаров: {len(new_products)}")

except Exception as e:
    send(f"⚠️ Ошибка парсинга:\n{str(e)}")
    print(f"ERROR: {e}")
