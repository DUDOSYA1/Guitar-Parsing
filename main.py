import sqlite3
import pandas as pd
from normalizer import GuitarNormalizer


DB = "thomann_guitars.db"


def main():
    conn = sqlite3.connect(DB)

    df = pd.read_sql_query("SELECT * FROM guitars", conn)

    print(f"Loaded rows: {len(df)}")

    norm = GuitarNormalizer()

    result = norm.run(df)

    result.to_sql(
        "guitars_normalized",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()

    print("DONE → guitars_normalized created")


if __name__ == "__main__":
    main()