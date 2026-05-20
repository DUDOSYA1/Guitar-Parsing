import sys

import requests
import sqlite3
import time as t
import re

from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from pathlib import Path



if len(sys.argv) < 2:
    raise Exception(
        "Database path not provided"
    )

db_path = Path(sys.argv[1]).resolve()

print(f"[DB PATH] {db_path}")

db_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

BASE_URL = "https://skifmusic.ru"


KNOWN_BRANDS = [
    "Ibanez",
    "Schecter",
    "ESP",
    "LTD",
    "Solar",
    "S by Solar",
    "J&D",
    "J&D Guitars",
    "Magneto",
    "Fender",
    "Gibson",
    "Jackson",
    "Cort",
    "PRS",
    "Yamaha",
    "Epiphone"
]


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
    ua = UserAgent()

    headers = {
        "User-Agent": ua.random
    }

    response = requests.get(url, headers=headers, timeout=15)

    if response.status_code == 200:
        return response.text

    print(f"Ошибка загрузки страницы: {response.status_code}")
    return None


import re


def parse_brand_and_model(title):

    title = title.replace("Электрогитара", "").strip()

    parts = title.split()

    if not parts:
        return "N/A", "N/A"

    model_start_index = None

    for i, part in enumerate(parts):

        if re.search(r'\d', part) or '-' in part:

            model_start_index = i
            break

    if model_start_index is None:

        if len(parts) == 1:
            return parts[0], "N/A"

        return parts[0], " ".join(parts[1:])

    manufacturer = " ".join(parts[:model_start_index])

    model = " ".join(parts[model_start_index:])

    return manufacturer, model


def extract_country(item):

    tags = item.select(".product-card__tag")

    blacklist = [
        "хит продаж",
        "чехол в комплекте",
        "состояние"
    ]

    for tag in tags:

        text = tag.text.strip()

        low = text.lower()

        if any(word in low for word in blacklist):
            continue


        if len(text) <= 25 and not re.search(r'\d', text):

            return text

    return "N/A"


def extract_condition(item):

    tags = item.select(".product-card__tag")

    for tag in tags:

        text = tag.text.strip()

        if "Состояние" in text:
            return "B-Stock"

    return "New"


def parse_page(pages):

    conn = init_db()
    cursor = conn.cursor()

    for p in range(1, pages + 1):

        url = f"{BASE_URL}/catalog/elektrogitaryi-12/page{p}"

        print(f"Парсим: {url}")

        html = get_html(url)

        if not html:
            continue

        soup = BeautifulSoup(html, 'html.parser')

        items = soup.select('.cards-list__item')

        for item in items:

            try:

                link_elem = item.select_one('.product-card__link')

                title = (
                    link_elem.text.strip()
                    if link_elem
                    else "N/A"
                )

                manufacturer, model = parse_brand_and_model(title)

                condition = extract_condition(item)

                country = extract_country(item)

                price_elem = item.select_one('.product-card__price')

                if price_elem:

                    price_text = re.sub(r'\D', '', price_elem.text)

                    price = int(price_text) if price_text else None

                else:
                    price = None

                rating_elem = item.select_one(
                    ".product-card__reviews-rating"
                )

                rating = (
                    rating_elem.text.strip().replace(",", ".")
                    if rating_elem
                    else "N/A"
                )

                link = (
                    link_elem['href']
                    if link_elem and link_elem.get('href')
                    else "N/A"
                )

                cursor.execute('''
                    INSERT INTO guitars (
                        model,
                        manufacturer,
                        country,
                        condition,
                        price,
                        rating,
                        website,
                        url,
                        parsing_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model,
                    manufacturer,
                    country,
                    condition,
                    price,
                    rating,
                    "Skifmusic",
                    link,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

            except Exception as e:

                print(f"Ошибка при обработке товара: {e}")

        conn.commit()

        print(f"Успешно сохранено {len(items)} товаров.")

        t.sleep(2)

    conn.close()


parse_page(2)