from pathlib import Path
import sqlite3
import pandas as pd

from normalizer import GuitarNormalizer


PARSING_DIR = Path("Parsing")
OUTPUT_DB = "normalized_guitars.db"

SOURCE_TABLE = "guitars"


class DatabaseCollector:

    def __init__(self, parsing_dir: Path):
        self.parsing_dir = parsing_dir

    def find_databases(self):
        return list(self.parsing_dir.rglob("*.db"))

    def load_database(self, db_path: Path):

        try:
            conn = sqlite3.connect(db_path)

            df = pd.read_sql_query(
                f"SELECT * FROM {SOURCE_TABLE}",
                conn
            )

            conn.close()

            print(f"[OK] {db_path.name}: {len(df)} rows")

            return df

        except Exception as e:
            print(f"[ERROR] {db_path.name}: {e}")
            return pd.DataFrame()

    def load_all(self):

        db_files = self.find_databases()

        if not db_files:
            raise FileNotFoundError(
                "No databases found inside Parsing/"
            )

        frames = []

        for db in db_files:

            df = self.load_database(db)

            if not df.empty:
                frames.append(df)

        if not frames:
            raise ValueError("No valid data loaded")

        result = pd.concat(frames, ignore_index=True)

        print(f"\n[TOTAL] {len(result)} rows loaded")

        return result


class DatabaseWriter:

    def __init__(self, output_db: str):
        self.output_db = output_db

    def save(self, df: pd.DataFrame):

        conn = sqlite3.connect(self.output_db)

        df.to_sql(
            "guitars",
            conn,
            if_exists="replace",
            index=False
        )

        conn.close()

        print(
            f"\n[SAVED] Normalized database -> {self.output_db}"
        )


def main():

    print("\n=== GUITAR ETL PIPELINE ===\n")

    collector = DatabaseCollector(PARSING_DIR)

    raw_df = collector.load_all()

    normalizer = GuitarNormalizer()

    normalized_df = normalizer.run(raw_df)

    writer = DatabaseWriter(OUTPUT_DB)

    writer.save(normalized_df)

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()