import sqlite3
import pandas as pd

conn = sqlite3.connect("muztorg_guitars.db")

# смотрим нормализованные данные
df = pd.read_sql("SELECT * FROM guitars_normalized", conn)

print(df.head(20))

conn.close()