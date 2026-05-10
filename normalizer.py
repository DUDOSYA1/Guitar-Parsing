import re
import pandas as pd
from unidecode import unidecode
from rapidfuzz import fuzz, process
from deep_translator import GoogleTranslator


class GuitarNormalizer:
    def __init__(self):
        self.tr = GoogleTranslator(source="auto", target="en")

    # ---------------- CLEAN ----------------
    def clean(self, x):
        if not x:
            return ""
        x = unidecode(str(x))
        x = x.lower().strip()
        x = re.sub(r"\s+", " ", x)
        return x

    # ---------------- TRANSLATE ----------------
    def translate(self, x):
        x = self.clean(x)
        BRAND_MAP = {
            "fender": "Fender",
            "gibson": "Gibson",
            "epiphone": "Epiphone",
            "harley benton": "Harley Benton",
            "squier": "Squier",
            "prs": "PRS"
        }
        return BRAND_MAP.get(x, x.title())

    # ---------------- MODEL NORMALIZATION ----------------
    def normalize_model(self, model):
        model = self.clean(model)

        # убираем мусор
        stop = {
            "electric", "acoustic", "guitar",
            "left", "right", "hand", "edition",
            "series", "standard", "pro", "deluxe"
        }

        words = [w for w in model.split() if w not in stop]

        # сортировка = убираем разный порядок слов
        words = sorted(words)

        return " ".join(words)

    # ---------------- FUZZY DEDUP ----------------
    def deduplicate(self, df):
        unique = []
        mapping = {}

        for m in df["model_norm"]:
            match = process.extractOne(m, unique, scorer=fuzz.ratio)

            if match and match[1] > 90:
                mapping[m] = match[0]
            else:
                unique.append(m)
                mapping[m] = m

        df["model_group"] = df["model_norm"].map(mapping)
        return df

    # ---------------- MAIN PIPELINE ----------------
    def run(self, df):

        df["model_norm"] = df["model"].apply(self.normalize_model)

        df["manufacturer_en"] = df["manufacturer"].apply(self.translate)
        df["country_en"] = df["country"].apply(self.translate)
        df["condition_en"] = df["condition"].apply(self.translate)

        df["website"] = df["website"].apply(self.clean)

        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

        df = self.deduplicate(df)

        result = df.sort_values("price").groupby("model_group").agg({
            "model": "first",
            "manufacturer_en": "first",
            "country_en": "first",
            "condition_en": "first",
            "price": "min",
            "rating": "mean",
            "website": "first",
            "url": "first",
            "parsing_date": "max"
        }).reset_index(drop=True)

        return result