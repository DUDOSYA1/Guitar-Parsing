from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
import pandas as pd
import csv
from io import StringIO, BytesIO
from normalizer import GuitarNormalizer

TOKEN = "8744455253:AAGQyKEYka_jTo3Kmnvf-9np9E5HzWMAiLo"

# 1. Загружаем сырые данные из твоей БД
conn = sqlite3.connect('muztorg_guitars.db')
df_raw = pd.read_sql_query("SELECT * FROM guitars", conn)
conn.close()

# 2. Применяем нормализацию
normalizer = GuitarNormalizer()
df = normalizer.run(df_raw)  # <- теперь df — чистые, сгруппированные данные

print(f"✅ Нормализация завершена. Уникальных групп: {len(df)}")

# ---------------------------------------------------------
# ДАЛЬШЕ БОТ РАБОТАЕТ ТОЛЬКО С DataFrame df
# ---------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎸 *Guitar Bot (Normalized)*\n\n"
        "🔍 /search Fender\n"
        "💰 /top desc\n"
        "💰 /top asc\n"
        "⭐ /toprating\n"
        "📊 /compare Les Paul\n"
        "📈 /stats",
        parse_mode='Markdown'
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /search Fender")
        return

    query = " ".join(context.args).lower()
    await update.message.reply_text(f"🔍 Ищу {query}...")

    # Поиск по нормализованным данным
    mask = (
        df['model'].str.lower().str.contains(query, na=False) |
        df['manufacturer_en'].str.lower().str.contains(query, na=False)
    )
    results = df[mask]

    if results.empty:
        await update.message.reply_text(f"Ничего не найдено: {query}")
        return

    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL, delimiter=';')
    writer.writerow(["№", "Модель", "Бренд", "Страна", "Состояние", "Цена (₽)", "Рейтинг", "Сайт", "Ссылка"])

    for i, row in results.iterrows():
        writer.writerow([
            i + 1,
            row['model'],
            row['manufacturer_en'],
            row['country_en'],
            row['condition_en'],
            row['price'],
            row['rating'],
            row['website'],
            row['url']
        ])

    csv_bytes = BytesIO(output.getvalue().encode('utf-8-sig'))
    await update.message.reply_document(
        document=csv_bytes,
        filename=f"guitars_{query}.csv",
        caption=f"Найдено: {len(results)} гитар (нормализовано)"
    )

async def top_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используй: /top asc или /top desc")
        return

    order_desc = context.args[0] == "desc"
    sorted_df = df.sort_values('price', ascending=not order_desc).head(10)

    title = "🔥 САМЫЕ ДОРОГИЕ" if order_desc else "💸 САМЫЕ ДЕШЁВЫЕ"
    message = f"*{title}*\n\n"
    for i, row in sorted_df.iterrows():
        rating_str = f"⭐{row['rating']}" if pd.notna(row['rating']) else "⭐Нет"
        message += f"{i+1}. *{row['manufacturer_en']} {row['model']}* - {row['price']:,.0f}₽ {rating_str}\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def top_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_df = df.dropna(subset=['rating']).sort_values('rating', ascending=False).head(10)

    message = "⭐ *ТОП ПО РЕЙТИНГУ (нормализовано)*\n\n"
    for i, row in sorted_df.iterrows():
        message += f"{i+1}. *{row['manufacturer_en']} {row['model']}* - ⭐{row['rating']} | {row['price']:,.0f}₽\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /compare Les Paul")
        return

    model_query = " ".join(context.args).lower()

    new = df[
        df['model'].str.lower().str.contains(model_query, na=False) &
        (df['condition_en'] == "New")
    ]
    used = df[
        df['model'].str.lower().str.contains(model_query, na=False) &
        (df['condition_en'].str.contains("Used", na=False))
    ]

    message = f"*{model_query.upper()}*\n\n"
    if not new.empty:
        message += f"Новые: {new['price'].mean():,.0f}₽ ({len(new)} шт.)\n"
    if not used.empty:
        message += f"Б/У: {used['price'].mean():,.0f}₽ ({len(used)} шт.)\n"
    if not new.empty and not used.empty:
        saving = new['price'].mean() - used['price'].mean()
        message += f"\n💸 Экономия: {saving:,.0f}₽ ({saving/new['price'].mean()*100:.0f}%)"

    await update.message.reply_text(message, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = len(df)
    avg_price = df['price'].mean()
    avg_rating = df['rating'].mean()

    await update.message.reply_text(
        f"📊 *СТАТИСТИКА (нормализовано)*\n\n"
        f"🎸 Уникальных групп: {total}\n"
        f"💰 Средняя цена: {avg_price:,.0f}₽\n"
        f"⭐ Средний рейтинг: {avg_rating:.1f}",
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

    print("🎸 Бот запущен. Данные нормализованы через GuitarNormalizer")
    app.run_polling()

if __name__ == "__main__":
    main()