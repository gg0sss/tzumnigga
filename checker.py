import requests
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# Загружаем старую базу (если есть)
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        old_products = json.load(f)
else:
    old_products = {}

new_products = {}

# Настройка Chrome в headless режиме
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

try:
    send("🤖 Запуск парсинга...")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    for category_url in CATEGORIES:
        print(f"\nПарсинг: {category_url}")
        driver.get(category_url)
        
        # Ждём загрузки первых карточек
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/item/ITEM']"))
        )
        
        # Скроллим и нажимаем "Показать больше" пока он есть
        last_count = 0
        attempts = 0
        max_attempts = 50
        
        print(f"  Начинаем поиск кнопки 'Показать больше'...")
        
        while attempts < max_attempts:
            # Скроллим вниз
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Ищем кнопку "Показать больше товаров"
            try:
                print(f"  Попытка {attempts + 1}: ищем кнопку...")
                button = driver.find_element(By.XPATH, "//p[contains(text(), 'Показать больше товаров')]")
                print(f"  Кнопка найдена! Кликаем...")
                driver.execute_script("arguments[0].click();", button)
                print(f"  Кнопка нажата!")
                time.sleep(3)
            except Exception as e:
                # Кнопки нет - все товары загружены
                print(f"  Кнопка не найдена: {e}")
                break
            
            # Проверяем не зависли ли
            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/item/ITEM']")
            current_count = len(cards)
            print(f"  Текущее количество карточек: {current_count}")
            
            if current_count == last_count:
                # Количество не изменилось - всё загружено
                print(f"  Количество не изменилось - выходим")
                break
            
            last_count = current_count
            attempts += 1
        
        # Собираем все карточки
        cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/item/ITEM']")
        print(f"  ИТОГО товаров в категории: {len(cards)}")
        
        # Извлекаем данные
        for card in cards:
            try:
                url = card.get_attribute("href")
                
                # Пропускаем дубликаты
                if url in new_products:
                    continue
                
                # Достаём бренд
                try:
                    brand_img = card.find_element(By.CSS_SELECTOR, "img[data-brandlogo='true']")
                    brand_name = brand_img.get_attribute("alt")
                except:
                    brand_name = "Товар"
                
                # Проверяем наличие по цене
                try:
                    card.find_element(By.CSS_SELECTOR, "span[class*='price']")
                    in_stock = True
                except:
                    in_stock = False
                
                new_products[url] = {
                    "title": brand_name,
                    "in_stock": in_stock
                }
                
                # Проверяем: был в наличии, а теперь НЕТ
                if url in old_products:
                    if old_products[url]["in_stock"] and not in_stock:
                        send(f"❌ ПРОДАНО\n\n{brand_name}\n\n{url}")
            
            except Exception as e:
                print(f"  Ошибка обработки карточки: {e}")
                continue
    
    driver.quit()
    
    # Сохраняем новую базу
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_products, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Всего проверено товаров: {len(new_products)}")
    send(f"✅ Парсинг завершён\n\nОтслеживается товаров: {len(new_products)}")

except Exception as e:
    send(f"⚠️ Ошибка парсинга:\n{str(e)}")
    print(f"ERROR: {e}")
    try:
        driver.quit()
    except:
        pass
