import re
import pandas as pd

from unidecode import unidecode


class GuitarNormalizer:

    def __init__(self):

        self.empty_values = {
            "",
            " ",
            "na",
            "n/a",
            "none",
            "null",
            "not specified",
            "-",
            "--"
        }

    # ---------------- CLEAN ----------------

    def clean_text(self, value):

        if pd.isna(value):
            return "N/A"

        value = str(value).strip()

        if value.lower() in self.empty_values:
            return "N/A"

        value = unidecode(value)

        value = re.sub(r"\s+", " ", value)

        if value == "":
            return "N/A"

        return value

    # ---------------- PRICE ----------------

    def clean_price(self, value):

        if pd.isna(value):
            return "N/A"

        value = str(value)

        if value.lower().strip() in self.empty_values:
            return "N/A"

        value = re.sub(r"[^0-9.,]", "", value)

        value = value.replace(",", ".")

        try:
            return float(value)
        except:
            return "N/A"

    # ---------------- RATING ----------------

    def clean_rating(self, value):

        if pd.isna(value):
            return "N/A"

        value = str(value).strip()

        if value.lower() in self.empty_values:
            return "N/A"

        try:
            return round(float(value), 2)
        except:
            return "N/A"

    # ---------------- CONDITION ----------------

    def normalize_condition(self, value):

        value = self.clean_text(value)

        if value == "N/A":
            return "N/A"

        value_lower = value.lower()

        used_words = [
            "used",
            "second hand",
            "бу",
            "b-stock"
        ]

        for word in used_words:
            if word in value_lower:
                return "БУ"

        return "Новая"

    # ---------------- COLUMN NORMALIZATION ----------------

    def normalize_columns(self, df: pd.DataFrame):

        column_mapping = {
            "model": "Модель гитары",
            "manufacturer": "Производитель",
            "brand": "Производитель",
            "country": "Страна производства",
            "condition": "Состояние",
            "price": "Цена",
            "rating": "Рейтинг",
            "website": "Сайт",
            "url": "Ссылка",
            "link": "Ссылка",
            "parsing_date": "Дата парсинга",
            "date": "Дата парсинга"
        }

        normalized = {}

        for column in df.columns:

            column_lower = column.lower()

            if column_lower in column_mapping:
                normalized[column] = column_mapping[column_lower]

        df = df.rename(columns=normalized)

        return df

    # ---------------- REQUIRED COLUMNS ----------------

    def ensure_columns(self, df: pd.DataFrame):

        required_columns = [
            "Модель гитары",
            "Производитель",
            "Страна производства",
            "Состояние",
            "Цена",
            "Рейтинг",
            "Сайт",
            "Ссылка",
            "Дата парсинга"
        ]

        for column in required_columns:

            if column not in df.columns:
                df[column] = "N/A"

        return df[required_columns]

    # ---------------- MAIN ----------------

    def run(self, df: pd.DataFrame):

        df = self.normalize_columns(df)

        df = self.ensure_columns(df)

        df["Модель гитары"] = df[
            "Модель гитары"
        ].apply(self.clean_text)

        df["Производитель"] = df[
            "Производитель"
        ].apply(self.clean_text)

        df["Страна производства"] = df[
            "Страна производства"
        ].apply(self.clean_text)

        df["Состояние"] = df[
            "Состояние"
        ].apply(self.normalize_condition)

        df["Цена"] = df[
            "Цена"
        ].apply(self.clean_price)

        df["Рейтинг"] = df[
            "Рейтинг"
        ].apply(self.clean_rating)

        df["Сайт"] = df[
            "Сайт"
        ].apply(self.clean_text)

        df["Ссылка"] = df[
            "Ссылка"
        ].apply(self.clean_text)

        df["Дата парсинга"] = df[
            "Дата парсинга"
        ].apply(self.clean_text)

        # Удаляем полные дубликаты
        df = df.drop_duplicates()

        # Сортировка по цене
        if "Цена" in df.columns:
            df = df.sort_values(
                by="Цена",
                ascending=True,
                na_position="last"
            )

        return df