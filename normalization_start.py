import sqlite3
import pandas as pd
from normalizer import GuitarNormalizer

SOURCE_DB = "thomann_guitars.db"
TARGET_DB = "thomann_guitars_normalized.db"


def main():
    src_conn = sqlite3.connect(SOURCE_DB)

    df = pd.read_sql("SELECT * FROM guitars", src_conn)

    src_conn.close()

    print(f"Loaded rows: {len(df)}")

    norm = GuitarNormalizer()

    result = norm.run(df)

    print(f"Normalized rows: {len(result)}")

    target_conn = sqlite3.connect(TARGET_DB)

    result.to_sql(
        "guitars_normalized",
        target_conn,
        if_exists="replace",
        index=False
    )

    target_conn.close()

    print("DONE")
    print(f"Saved to: {TARGET_DB}")


if __name__ == "__main__":
    main()