import sys
import time
import sqlite3
import re
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent

from pathlib import Path


# ------------------------------------------------
# DB PATH
# ------------------------------------------------

if len(sys.argv) < 2:
    raise Exception(
        "Database path not provided"
    )

db_path = Path(sys.argv[1]).resolve()

print(f"[DB PATH] {db_path}")

# Создаем папку если нет
db_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

def init_db():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guitars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            manufacturer TEXT,
            country TEXT,
            condition TEXT,
            price INTEGER,
            rating TEXT,
            website TEXT,
            url TEXT,
            parsing_date TEXT
        )
    ''')
    conn.commit()
    return conn


def get_driver():
    ua = UserAgent()
    options = Options()
    # Безголовый режим для скорости
    options.add_argument("--headless=new")
    options.add_argument(f"user-agent={ua.random}")
    options.add_argument("--disable-images")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options)
    return driver


def clean_price(price_text):
    match = re.search(r'(\d+[\s\xa0]*\d+)', price_text)
    if match:
        cleaned = re.sub(r'[\s\xa0]', '', match.group(1))
        return int(cleaned)
    return "N/A"


def clean_manufacturer(text):
    if not text:
        return "N/A"
    cleaned = text.replace('Электрогитара', '').strip()
    return cleaned if cleaned else "N/A"


def clean_model(text):
    if not text:
        return "N/A"
    cleaned = text.replace('Электрогитара', '').strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned if cleaned else "N/A"


def clean_rating(text):
    if not text:
        return "No rating"
    match = re.search(r'(\d+\.\d+)', text)
    return match.group(1) if match else "No rating"


def parse_page(driver, url):
    """Парсит одну страницу по URL"""
    driver.get(url)
    time.sleep(3)  # Ждём загрузки

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    items = soup.select('article.catalog-card.js-catalog-card')

    if not items:
        print(f"  → Товары не найдены на {url}")
        return []

    page_items = []
    for item in items:
        try:
            raw_manufacturer = item.select_one('.catalog-card__category')
            manufacturer = clean_manufacturer(raw_manufacturer.text.strip() if raw_manufacturer else "")

            raw_model = item.select_one('.catalog-card__info')
            model = clean_model(raw_model.text.strip() if raw_model else "")

            # Убираем дублирование производителя в модели
            if manufacturer != "N/A" and model.startswith(manufacturer):
                model = model[len(manufacturer):].lstrip()
            elif manufacturer == "N/A" and model != "N/A":
                parts = model.split()
                if parts:
                    manufacturer = parts[0]
                    if model.startswith(manufacturer):
                        model = model[len(manufacturer):].lstrip()

            condition = "Used (B-Stock)" if "B-Stock" in model or "б/у" in item.get_text().lower() else "New"

            price_elem = item.select_one('.catalog-card__price')
            price = clean_price(price_elem.text.strip()) if price_elem else "N/A"

            rating_elem = item.select_one('.catalog-card__misc')
            rating = clean_rating(rating_elem.text.strip() if rating_elem else "")

            link_elem = item.select_one('a.catalog-card__link')
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                link = f"https://www.muztorg.ru{href}" if href.startswith('/') else href
            else:
                link = "N/A"

            if price != "N/A" and model != "N/A":
                page_items.append({
                    'model': model, 'manufacturer': manufacturer, 'country': "Not specified",
                    'condition': condition, 'price': price, 'rating': rating,
                    'website': "Muztorg", 'url': link,
                    'parsing_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception as e:
            print(f"  Ошибка обработки товара: {e}")

    return page_items


def parse_all_pages(start_page=1, max_pages=10):
    """Парсит все страницы через параметр ?page=N"""
    driver = get_driver()
    conn = init_db()
    cursor = conn.cursor()
    total_items = 0

    try:
        for page in range(start_page, start_page + max_pages):
            url = f"https://www.muztorg.ru/category/elektrogitary?page={page}"
            print(f"\n📄 Страница {page}: {url}")

            items = parse_page(driver, url)

            if not items:
                print(f"  → На странице {page} нет товаров. Возможно, это конец.")
                break

            for item in items:
                cursor.execute('''
                    INSERT INTO guitars (model, manufacturer, country, condition, price, rating, website, url, parsing_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (item['model'], item['manufacturer'], item['country'],
                      item['condition'], item['price'], item['rating'],
                      item['website'], item['url'], item['parsing_date']))

            conn.commit()
            total_items += len(items)
            print(f"  ✅ Сохранено {len(items)} товаров (всего: {total_items})")

            # Небольшая задержка между страницами
            time.sleep(1)

    finally:
        driver.quit()
        conn.close()

    print(f"\n🎉 Готово! Всего сохранено {total_items} товаров с {page} страниц.")


if __name__ == "__main__":
    # Парсим первые 10 страниц (можно увеличить)
    parse_all_pages(start_page=1, max_pages=2)