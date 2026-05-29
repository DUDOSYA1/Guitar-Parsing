import sys
import requests
import sqlite3
import time as t
import re
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from pathlib import Path
import cloudscraper
from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.sweetwater.com"

if len(sys.argv) < 2:
    db_path = Path("sweetwater.db").resolve()
else:
    db_path = Path(sys.argv[1]).resolve()

print(f"[DB PATH] {db_path}")

db_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def create_driver():

    options = Options()

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    options.add_argument("--start-maximized")

    options.add_argument(
        "user-agent=Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        options=options
    )

    return driver

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




scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

def get_html(url):
    headers = {
        "User-Agent": UserAgent().random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }

    try:
        response = scraper.get(
            url,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            return response.text

        print(f"HTTP {response.status_code}: {url}")

    except Exception as e:
        print(f"Ошибка сети: {e}")

    return None


def extract_country(product_soup):
    """
    Ищем страну производства на странице товара
    """

    text = product_soup.get_text(" ", strip=True)

    patterns = [
        r"Made in\s+([A-Za-z\s]+)",
        r"Country of Origin\s*:?[\s]+([A-Za-z\s]+)",
        r"Manufactured in\s+([A-Za-z\s]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            country = match.group(1).strip()

            # Убираем мусор
            country = re.sub(r'[^A-Za-z\s]', '', country)

            if len(country) > 1:
                return country.title()

    return "N/A"


def extract_rating(product_soup):

    rating_elem = product_soup.select_one('.rating__stars')

    if rating_elem and rating_elem.get('data-rated'):
        return rating_elem.get('data-rated').strip()

    # fallback
    rating_text = product_soup.get_text(" ", strip=True)

    match = re.search(
        r'Rated\s+(\d+(\.\d+)?)\/5',
        rating_text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return "N/A"


def parse_product_page(url):
    html = get_html(url)

    if not html:
        return {
            "rating": "N/A",
            "country": "N/A",
            "condition": "New"
        }

    soup = BeautifulSoup(html, "html.parser")

    rating = extract_rating(soup)

    country = extract_country(soup)

    title = soup.title.get_text().lower() if soup.title else ""

    is_used = (
        "used" in title or
        "demo" in title or
        "open box" in title or
        "b-stock" in title
    )

    condition = "B-Stock" if is_used else "New"

    return {
        "rating": rating,
        "country": country,
        "condition": condition
    }


def parse_price(text):
    if not text:
        return 0

    cleaned = re.sub(r'[^\d]', '', text)

    if not cleaned:
        return 0

    # Убираем центы
    value = int(cleaned)

    return value // 100

def parse_catalog(
        conn,
        cursor,
        base_url,
        pages_count,
        condition_value
):
    for p in range(1, pages_count + 1):

        url = f"{base_url}{p}"

        print(f"\nПарсим страницу: {url}")

        html = get_html(url)

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select('.product-card.gg--card')

        print(f"Найдено карточек: {len(cards)}")

        for card in cards:
            try:

                # =========================
                # Название
                # =========================

                title_elem = (
                    card.select_one('.product-card__name') or
                    card.select_one('.product-card-title') or
                    card.select_one('h2') or
                    card.select_one('a[title]')
                )

                if not title_elem:
                    continue

                title = title_elem.get_text(" ", strip=True)

                if not title:
                    continue

                # =========================
                # Производитель
                # =========================

                manufacturer = title.split()[0]

                # =========================
                # Цена
                # =========================

                price_elem = (
                    card.select_one('.product-card__price') or
                    card.select_one('.price') or
                    card.select_one('[class*="price"]')
                )

                price = 0

                if price_elem:
                    price = parse_price(
                        price_elem.get_text()
                    )

                # =========================
                # Ссылка
                # =========================

                link_elem = (
                    card.select_one('a[href]')
                )

                if not link_elem:
                    continue

                href = link_elem.get("href")

                if not href:
                    continue

                if href.startswith("/"):
                    full_link = BASE_URL + href
                else:
                    full_link = href

                # =========================
                # Модель
                # =========================

                model = title.replace(
                    manufacturer,
                    ""
                ).strip()

                # =========================
                # Доп данные
                # =========================

                extra_data = parse_product_page(
                    full_link
                )

                # condition теперь задается
                # от каталога

                # =========================
                # INSERT
                # =========================

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
                    extra_data['country'],
                    condition_value,
                    price,
                    extra_data['rating'],
                    "SWEETWATER",
                    full_link,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ))

                print(
                    f"Добавлено: "
                    f"{manufacturer} {model} "
                    f"[{condition_value}]"
                )

                t.sleep(0.5)

            except Exception as e:
                print(f"Ошибка в карточке: {e}")

        conn.commit()

if __name__ == "__main__":

    conn = init_db()
    cursor = conn.cursor()

    parse_catalog(
        conn=conn,
        cursor=cursor,
        base_url="https://www.sweetwater.com/c589--Electric_Guitars?all=&sb=popular&pn=",
        pages_count=1,
        condition_value="New"
    )

    conn.close()

    print("\nГотово. Sweetwater база обновлена.")