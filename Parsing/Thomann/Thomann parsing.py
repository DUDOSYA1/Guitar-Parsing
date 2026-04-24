import time
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent


def init_db():
    conn = sqlite3.connect('thomann_guitars.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guitars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            manufacturer TEXT,
            country TEXT,
            condition TEXT,
            price TEXT,
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
    # options.add_argument("--headless") # Раскомментируйте для работы в фоновом режиме
    options.add_argument(f"user-agent={ua.random}")
    # Укажите путь к вашему chromedriver, если он не в PATH
    driver = webdriver.Chrome(options=options)
    return driver


def parse_page():
    driver = get_driver()
    url = "https://www.thomannmusic.com/all-products-from-the-category-electric-guitars.html"
    driver.get(url)

    wait = WebDriverWait(driver, 10)

    # Пример нажатия кнопки "Show more" 2 раза для подгрузки данных
    for _ in range(2):
        try:
            show_more_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search-pagination__show-more")))
            driver.execute_script("arguments[0].click();", show_more_btn)
            time.sleep(2)  # Ожидание подгрузки
        except Exception as e:
            print("Кнопка больше не доступна или ошибка:", e)
            break

    # Передаем полностью загруженный HTML в BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    items = soup.select('.fx-product-list-entry')
    conn = init_db()
    cursor = conn.cursor()

    for item in items:
        try:
            manufacturer = item.select_one('.title__manufacturer').text.strip() if item.select_one('.title__manufacturer') else "N/A"
            model = item.select_one('.title__name').text.strip() if item.select_one('.title__name') else "N/A"

            # Определение состояния (на Thomann B-Stock указывает на БУ/уценку)
            condition = "Used (B-Stock)" if "B-Stock" in model or "B-Stock" in item.get_text() else "New"

            price = item.select_one('.fx-typography-price-primary fx-price-group__primary product__price-primary').text.strip() if item.select_one(
                '.fx-typography-price-primary fx-price-group__primary product__price-primary') else "N/A"

            rating_elem = item.select_one('.fx-rating-stars__stars')
            rating = rating_elem.get('aria-label') if rating_elem else "No rating"

            link_elem = item.select_one('a.product-listings-info__direct-link')
            link = "https://www.thomannmusic.com" + link_elem['href'] if link_elem else "N/A"

            # Страна часто не указана в листинге, на Thomann это обычно требует захода в карточку товара
            country = "Not specified"

            cursor.execute('''
                INSERT INTO guitars (model, manufacturer, country, condition, price, rating, website, url, parsing_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model, manufacturer, country, condition, price, rating, "Thomann", link,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        except Exception as e:
            print(f"Ошибка при обработке товара: {e}")

    conn.commit()
    conn.close()
    print(f"Успешно сохранено {len(items)} товаров в БД.")


if __name__ == "__main__":
    parse_page()