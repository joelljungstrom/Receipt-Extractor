import pandas as pd
import sqlite3
from pathlib import Path

# 1) Read your CSV
line_items = Path.home() / "Documents" / "Projects" / "Receipt Extractor" / "Output" / "line_items.csv"
purchases = Path.home() / "Documents" / "Projects" / "Receipt Extractor" / "Output" / "purchases.csv"

line_items_df = pd.read_csv(line_items)
purchases_df = pd.read_csv(purchases)

# 2) Create (or open) a local SQLite database file
db_path = Path.home() / "Documents" / "Projects" / "sqlite_db" / "superset_data.db"
conn = sqlite3.connect(db_path)

# 3) Write your DataFrame into a table called "my_table"
line_items_df.to_sql("line_items", conn, if_exists="replace", index=False)
purchases_df.to_sql("purchases", conn, if_exists="replace", index=False)

conn.close()