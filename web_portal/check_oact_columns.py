"""Check OACT table columns"""
from hdbcli import dbapi
import os
from dotenv import load_dotenv

load_dotenv()

conn = dbapi.connect(
    address=os.getenv('HANA_HOST'),
    port=int(os.getenv('HANA_PORT')),
    user=os.getenv('HANA_USER'),
    password=os.getenv('HANA_PASSWORD')
)

cursor = conn.cursor()
cursor.execute('SET SCHEMA "4B-BIO_APP"')
cursor.execute("SELECT COLUMN_NAME FROM TABLE_COLUMNS WHERE TABLE_NAME = 'OACT' ORDER BY POSITION")

cols = [row[0] for row in cursor.fetchall()]
print(f"OACT table has {len(cols)} columns:")
for col in cols:
    print(f"  - {col}")

cursor.close()
conn.close()
