from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8744455253:AAGQyKEYka_jTo3Kmnvf-9np9E5HzWMAiLo"

# Пример данных (нормализованный вид из ТЗ)
guitars_data = [
    {
        "model": "Stratocaster",
        "brand": "Fender",
        "country": "USA",
        "condition": "БУ",
        "price": 75000,
        "rating": 4.8,
        "site": "avito.ru",
        "url": "https://avito.ru/1",
        "parse_date": "2026-04-10",
        "description": "Классическая электрогитара, отличное состояние"
    },
    {
        "model": "Les Paul",
        "brand": "Gibson",
        "country": "USA",
        "condition": "новая",
        "price": 180000,
        "rating": 4.9,
        "site": "avito.ru",
        "url": "https://avito.ru/2",
        "parse_date": "2026-04-10",
        "description": "Новая гитара, в коробке"
    },
    {
        "model": "Yamaha FG800",
        "brand": "Yamaha",
        "country": "China",
        "condition": "новая",
        "price": 28000,
        "rating": 4.7,
        "site": "yula.ru",
        "url": "https://yula.ru/3",
        "parse_date": "2026-04-09",
        "description": "Акустическая гитара для начинающих"
    }
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎸 *Бот для выдачи данных о гитарах*\n\n"
        "📋 *Команды:*\n"
        "/all - показать все гитары\n"
        "/stats - статистика\n"
        "/search <модель или бренд> - поиск\n"
        "/help - справка",
        parse_mode='Markdown'
    )

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not guitars_data:
        await update.message.reply_text("Нет данных")
        return
    
    message = "🎸 *ВСЕ ГИТАРЫ*\n\n"
    for i, g in enumerate(guitars_data, 1):
        message += (
            f"*{i}. {g['model']}* — {g['brand']}\n"
            f"📍 Страна: {g['country']}\n"
            f"🔧 Состояние: {g['condition']}\n"
            f"💰 Цена: {g['price']:,}₽\n"
            f"⭐ Рейтинг: {g['rating']}\n"
            f"🌐 Сайт: {g['site']}\n"
            f"🔗 Ссылка: {g['url']}\n"
            f"📅 Дата парсинга: {g['parse_date']}\n"
            f"📝 Описание: {g['description']}\n"
            f"{'─' * 30}\n\n"
        )
        
        if len(message) > 4000:
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
            message = ""
    
    if message:
        await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = len(guitars_data)
    total_price = sum(g['price'] for g in guitars_data)
    avg_price = total_price / total if total > 0 else 0
    new_count = sum(1 for g in guitars_data if g['condition'] == 'новая')
    used_count = sum(1 for g in guitars_data if g['condition'] == 'БУ')
    avg_rating = sum(g['rating'] for g in guitars_data) / total if total > 0 else 0
    
    await update.message.reply_text(
        f"📊 *СТАТИСТИКА*\n\n"
        f"🎸 Всего гитар: *{total}*\n"
        f"💰 Средняя цена: *{avg_price:,.0f}₽*\n"
        f"💵 Общая стоимость: *{total_price:,.0f}₽*\n"
        f"🆕 Новых: *{new_count}*\n"
        f"🔨 Б/У: *{used_count}*\n"
        f"⭐ Средний рейтинг: *{avg_rating:.1f}*\n",
        parse_mode='Markdown'
    )

async def search_guitars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("ℹ️ Пример использования: `/search Fender` или `/search Stratocaster`", parse_mode='Markdown')
        return
    
    query = " ".join(context.args).lower()
    results = []
    
    for g in guitars_data:
        if query in g['model'].lower() or query in g['brand'].lower() or query in g['description'].lower():
            results.append(g)
    
    if not results:
        await update.message.reply_text(f"❌ Ничего не найдено по запросу: {query}")
        return
    
    message = f"🔍 *РЕЗУЛЬТАТЫ ПО ЗАПРОСУ:* {query}\n\n"
    for i, g in enumerate(results[:10], 1):
        message += (
            f"*{i}. {g['model']}* — {g['brand']}\n"
            f"💰 {g['price']:,}₽ | {g['condition']} | ⭐ {g['rating']}\n"
            f"🔗 {g['url']}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("all", show_all))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("search", search_guitars))
    app.add_handler(CommandHandler("help", help_command))
    
    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()