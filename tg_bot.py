from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
import csv
from io import StringIO, BytesIO
from datetime import datetime
import random

request_kwargs = {
    'proxy_url': 'socks5://185.166.213.79:1080',  
    'urllib3_proxy_kwargs': {
        'username': '',
        'password': '',
    }
}

TOKEN = "8744455253:AAGQyKEYka_jTo3Kmnvf-9np9E5HzWMAiLo"

conn = sqlite3.connect('guitars.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS guitars (
    id INTEGER PRIMARY KEY,
    model TEXT,
    brand TEXT,
    country TEXT,
    condition TEXT,
    price INTEGER,
    rating REAL,
    site TEXT,
    url TEXT,
    parse_date TEXT,
    description TEXT
)
''')
conn.commit()

cursor.execute("SELECT COUNT(*) FROM guitars")
if cursor.fetchone()[0] == 0:
    models = [
        ("Stratocaster", "Fender", "USA", "Электрогитара"),
        ("Les Paul", "Gibson", "USA", "Электрогитара"),
        ("Telecaster", "Fender", "USA", "Электрогитара"),
        ("SG", "Gibson", "USA", "Электрогитара"),
        ("FG800", "Yamaha", "China", "Акустика"),
    ]
    sites = ["avito.ru", "yula.ru"]
    
    for i in range(100):
        model, brand, country, desc = random.choice(models)
        condition = random.choice(["новая", "БУ"])
        price = random.randint(15000, 200000)
        if condition == "БУ":
            price = int(price * 0.7)
        rating = round(random.uniform(3.5, 5.0), 1)
        
        cursor.execute('''
        INSERT INTO guitars (model, brand, country, condition, price, rating, site, url, parse_date, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (model, brand, country, condition, price, rating, random.choice(sites), f"https://example.com/{i}", datetime.now().strftime("%Y-%m-%d"), desc))
    
    conn.commit()
    print("✅ Добавлено 100 гитар")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " *Guitar Bot*\n\n"
        " /search Fender - поиск (Excel файл)\n"
        " /top price desc - дорогие\n"
        " /top price asc - дешевые\n"
        " /toprating - по рейтингу\n"
        " /compare Les Paul - сравнение цен\n"
        " /stats - статистика",
        parse_mode='Markdown'
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /search Fender")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Ищу {query}...")
    
    cursor.execute('''
    SELECT model, brand, country, condition, price, rating, site, url 
    FROM guitars 
    WHERE model LIKE ? OR brand LIKE ?
    ''', (f'%{query}%', f'%{query}%'))
    
    results = cursor.fetchall()
    
    if not results:
        await update.message.reply_text(f"Ничего не найдено: {query}")
        return
    
    # Создаем CSV файл
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Модель", "Бренд", "Страна", "Состояние", "Цена", "Рейтинг", "Сайт", "Ссылка"])
    writer.writerows(results)
    
    csv_bytes = BytesIO(output.getvalue().encode('utf-8-sig'))
    
    await update.message.reply_document(
        document=csv_bytes,
        filename=f"guitars_{query}.csv",
        caption=f"🎸 Найдено: {len(results)} гитар"
    )

async def top_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используй: /top price asc или /top price desc")
        return
    
    order = "DESC" if context.args[0] == "desc" else "ASC"
    cursor.execute(f'SELECT model, brand, price, rating, condition FROM guitars ORDER BY price {order} LIMIT 10')
    results = cursor.fetchall()
    
    title = "ДОРОГИЕ" if order == "DESC" else "ДЕШЕВЫЕ"
    message = f"*{title}*\n\n"
    for i, (model, brand, price, rating, cond) in enumerate(results, 1):
        message += f"{i}. *{brand} {model}* - {price:,}₽ {rating}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def top_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute('SELECT model, brand, price, rating, condition FROM guitars ORDER BY rating DESC LIMIT 10')
    results = cursor.fetchall()
    
    message = "⭐ *ТОП ПО РЕЙТИНГУ*\n\n"
    for i, (model, brand, price, rating, cond) in enumerate(results, 1):
        message += f"{i}. *{brand} {model}* - ⭐{rating} | {price:,}₽\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /compare Stratocaster")
        return
    
    model = " ".join(context.args)
    
    cursor.execute('SELECT AVG(price), COUNT(*) FROM guitars WHERE model LIKE ? AND condition="новая"', (f'%{model}%',))
    new_avg, new_count = cursor.fetchone()
    
    cursor.execute('SELECT AVG(price), COUNT(*) FROM guitars WHERE model LIKE ? AND condition="БУ"', (f'%{model}%',))
    used_avg, used_count = cursor.fetchone()
    
    message = f"*{model.upper()}*\n\n"
    if new_count:
        message += f"Новые: {new_avg:,.0f}₽ ({new_count} шт.)\n"
    if used_count:
        message += f"Б/У: {used_avg:,.0f}₽ ({used_count} шт.)\n"
    if new_count and used_count:
        saving = new_avg - used_avg
        message += f"\nЭкономия: {saving:,.0f}₽ ({saving/new_avg*100:.0f}%)"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute('SELECT COUNT(*), AVG(price), AVG(rating) FROM guitars')
    total, avg_price, avg_rating = cursor.fetchone()
    
    await update.message.reply_text(
        f"*СТАТИСТИКА*\n\n"
        f"Всего: {total}\n"
        f"Средняя цена: {avg_price:,.0f}₽\n"
        f"Средний рейтинг: {avg_rating:.1f}",
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("top", top_price))
    app.add_handler(CommandHandler("toprating", top_rating))
    app.add_handler(CommandHandler("compare", compare))
    app.add_handler(CommandHandler("stats", stats))
    
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()