from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

import sqlite3
import pandas as pd
import csv
from io import StringIO, BytesIO

TOKEN = "8744455253:AAGQyKEYka_jTo3Kmnvf-9np9E5HzWMAiLo"

RATES = {"USD": 73, "EUR": 84, "RUB": 1}


def price_in_rub(row):
    price = row["Цена"]
    if pd.isna(price):
        return float("nan")
    currency = row.get("Валюта", "RUB")
    rate = RATES.get(str(currency).upper(), 1)
    return float(price) * rate

df = pd.DataFrame()


def load_data():

    global df

    try:

        conn = sqlite3.connect(
            "normalized_guitars.db"
        )

        new_df = pd.read_sql_query(
            "SELECT * FROM guitars",
            conn
        )

        conn.close()

        new_df["Цена"] = pd.to_numeric(
            new_df["Цена"],
            errors="coerce"
        )

        new_df["Рейтинг"] = pd.to_numeric(
            new_df["Рейтинг"],
            errors="coerce"
        )

        df = new_df

        print(
            f"Загружено {len(df)} записей"
        )

    except Exception as e:

        print(
            f"Ошибка загрузки: {e}"
        )



async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🎸 Guitar Bot\n\n"
        "🔍 /search Fender\n"
        "💰 /top desc\n"
        "💰 /top asc\n"
        "⭐ /toprating\n"
        "📊 /compare Les Paul\n"
        "📈 /stats\n"
        "🔄 /reload"
    )


async def reload_db(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    load_data()

    await update.message.reply_text(
        f"✅ База обновлена\n"
        f"Записей: {len(df)}"
    )


async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if df.empty:

        await update.message.reply_text(
            "База не загружена"
        )

        return

    if not context.args:

        await update.message.reply_text(
            "Пример:\n/search Fender"
        )

        return

    query = " ".join(
        context.args
    ).lower()

    mask = (

        df["Модель гитары"]
        .astype(str)
        .str.lower()
        .str.contains(
            query,
            na=False
        )

        |

        df["Производитель"]
        .astype(str)
        .str.lower()
        .str.contains(
            query,
            na=False
        )
    )

    results = df[mask]

    if results.empty:

        await update.message.reply_text(
            "Ничего не найдено"
        )

        return

    output = StringIO()

    writer = csv.writer(
        output,
        delimiter=";"
    )

    writer.writerow([
        "Модель",
        "Производитель",
        "Цена",
        "Валюта",
        "Рейтинг",
        "Сайт"
    ])

    for _, row in results.iterrows():

        writer.writerow([

            row["Модель гитары"],
            row["Производитель"],
            row["Цена"],
            row.get("Валюта", "N/A"),
            row["Рейтинг"],
            row["Ссылка"]

        ])

    csv_bytes = BytesIO(
        output.getvalue()
        .encode("utf-8-sig")
    )

    await update.message.reply_document(
        document=csv_bytes,
        filename="results.csv"
    )


async def top_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if df.empty:

        return

    if not context.args:

        await update.message.reply_text(
            "/top asc\n/top desc"
        )

        return

    order_desc = (
        context.args[0]
        == "desc"
    )

    sorted_df = (
        df.assign(
            _price_rub=df.apply(price_in_rub, axis=1)
        )
        .sort_values(
            "_price_rub",
            ascending=not order_desc
        )
        .drop(columns=["_price_rub"])
        .head(10)
    )

    title = (
        "🔥 ДОРОГИЕ"
        if order_desc
        else
        "💸 ДЕШЁВЫЕ"
    )

    message = f"{title}\n\n"

    for i, row in sorted_df.iterrows():

        rating = (
            row["Рейтинг"]
            if pd.notna(
                row["Рейтинг"]
            )
            else "-"
        )

        currency = row.get("Валюта", "RUB")
        symbols = {"USD": "$", "EUR": "€", "RUB": "₽"}
        symbol = symbols.get(str(currency).upper(), "₽")
        rub = price_in_rub(row)
        rub_str = (
            f" (~{rub:,.0f} ₽)"
            if str(currency).upper() != "RUB"
            else ""
        )

        message += (

            f"{i+1}. "
            f"{row['Производитель']} "
            f"{row['Модель гитары']}\n"
            f"💰 {row['Цена']:,.0f} {symbol}"
            f"{rub_str} "
            f"⭐ {rating}\n\n"
        )

    await update.message.reply_text(
        message
    )


async def top_rating(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if df.empty:

        return

    sorted_df = (

        df.dropna(
            subset=["Рейтинг"]
        )

        .sort_values(
            "Рейтинг",
            ascending=False
        )

        .head(10)
    )

    message = "⭐ ТОП ПО РЕЙТИНГУ\n\n"

    for i, row in sorted_df.iterrows():

        message += (

            f"{i+1}. "
            f"{row['Производитель']} "
            f"{row['Модель гитары']}\n"
            f"⭐ {row['Рейтинг']}\n\n"
        )

    await update.message.reply_text(
        message
    )


async def compare(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if df.empty:

        return

    if not context.args:

        await update.message.reply_text(
            "/compare Les Paul"
        )

        return

    query = (
        " ".join(
            context.args
        )
        .lower()
    )

    results = df[
        df[
            "Модель гитары"
        ]
        .astype(str)
        .str.lower()
        .str.contains(
            query,
            na=False
        )
    ]

    if results.empty:

        await update.message.reply_text(
            "Не найдено"
        )

        return

    avg = results[
        "Цена"
    ].mean()

    await update.message.reply_text(

        f"🎸 {query}\n\n"
        f"Найдено: {len(results)}\n"
        f"Средняя цена: {avg:,.0f} ₽"

    )


async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if df.empty:

        await update.message.reply_text(
            "База не загружена"
        )

        return

    total = len(df)

    avg_price = (
        df["Цена"]
        .mean()
    )

    avg_rating = (
        df["Рейтинг"]
        .mean()
    )

    await update.message.reply_text(

        f"📊 СТАТИСТИКА\n\n"
        f"🎸 Гитар: {total}\n"
        f"💰 Средняя цена: "
        f"{avg_price:,.0f} ₽\n"
        f"⭐ Средний рейтинг: "
        f"{avg_rating:.1f}"

    )


def main():

    load_data()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "reload",
            reload_db
        )
    )

    app.add_handler(
        CommandHandler(
            "search",
            search
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top_price
        )
    )

    app.add_handler(
        CommandHandler(
            "toprating",
            top_rating
        )
    )

    app.add_handler(
        CommandHandler(
            "compare",
            compare
        )
    )

    app.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    print("Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()