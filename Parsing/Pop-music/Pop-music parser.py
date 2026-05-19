import sys

import requests
import sqlite3
import time as t
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

BASE_URL = "https://pop-music.ru"

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

import sys

sys.stdout.reconfigure(
    encoding="utf-8"
)

sys.stderr.reconfigure(
    encoding="utf-8"
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


def get_html(url):
    headers = {"User-Agent": UserAgent().random}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Ошибка сети: {e}")
    return None


def extract_country(product_soup):
    # Ищем блок характеристик
    specs = product_soup.select('.productfull__description-spec')
    for spec in specs:
        text = spec.get_text(" ", strip=True)
        if "Страна-производитель:" in text:
            # Извлекаем текст строго после двоеточия
            parts = text.split("Страна-производитель:")
            if len(parts) > 1:
                country_raw = parts[1].strip()
                # Убираем лишние слова, если они приклеились, берем первое слово (название страны)
                # И делаем формат "Китай", а не "КИТАЙ"
                country_clean = country_raw.split()[0] if country_raw else ""
                return country_clean.capitalize()
    return "N/A"


def parse_product_page(url):
    html = get_html(url)
    if not html:
        return {"rating": "0", "country": "N/A", "condition": "New"}

    soup = BeautifulSoup(html, "html.parser")

    # 1. Рейтинг
    rating_elem = soup.select_one('.productfull__reviews-total-rate')
    rating = rating_elem.text.strip() if rating_elem else "0"

    # 2. Страна
    country = extract_country(soup)

    # 3. Состояние
    # Если в URL или в H1 есть "уценка" - это B-Stock
    h1 = soup.find('h1')
    h1_text = h1.get_text().lower() if h1 else ""
    is_used = "уцен" in h1_text or "ucenka" in url.lower() or "уценка" in url.lower()
    condition = "B-Stock" if is_used else "New"

    return {
        "rating": rating,
        "country": country,
        "condition": condition
    }


def parse_page(pages_count):
    conn = init_db()
    cursor = conn.cursor()

    for p in range(1, pages_count + 1):
        url = f"{BASE_URL}/catalog/gitaryi/elektrogitaryi/?PAGEN_2={p}"
        html = get_html(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select('.product-card')

        for card in cards:
            try:
                # 1. Сначала определяем название (title)
                title = "N/A"
                btn = card.select_one('.js-add-to-cart')

                # Пробуем достать из JSON данных кнопки (самый точный метод)
                if btn and btn.get('data-info'):
                    data = json.loads(btn.get('data-info'))
                    title = data.get('name', 'N/A')
                    price = data.get('price', 0)
                    manufacturer = data.get('brand', 'N/A')
                else:
                    # Если JSON нет, ищем в заголовке карточки
                    title_elem = card.select_one('.product-card__title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                    price_elem = card.select_one('.product-card__price')
                    price = int(re.sub(r'\D', '', price_elem.text)) if price_elem else 0
                    manufacturer = title.split()[0] if title != "N/A" else "N/A"

                # === КРИТИЧЕСКАЯ ПРОВЕРКА: Отсекаем N/A в title ===
                if not title or title == "N/A":
                    continue

                # 2. Ссылка на товар
                link_elem = card.select_one('.product-card__img a')
                if not link_elem:
                    continue
                href = link_elem.get("href")
                full_link = BASE_URL + href if href.startswith('/') else href

                # 3. Чистим модель (удаляем слово 'Электрогитара' и бренд)
                model = title.replace(manufacturer, '').replace('Электрогитара', '').strip()

                # 4. Данные со страницы товара
                extra_data = parse_product_page(full_link)

                cursor.execute('''
                    INSERT INTO guitars (
                        model, manufacturer, country, condition, price, rating, website, url, parsing_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model,
                    manufacturer,
                    extra_data['country'],
                    extra_data['condition'],
                    price,
                    extra_data['rating'],
                    "POP-MUSIC",
                    full_link,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                print(f"Добавлено: {manufacturer} {model} ({extra_data['country']})")
                t.sleep(0.5)

            except Exception as e:
                print(f"Ошибка в карточке: {e}")

        conn.commit()

    conn.close()
    print("\nГотово! База данных обновлена.")


if __name__ == "__main__":
    parse_page(2)