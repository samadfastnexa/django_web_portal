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
cursor.execute("SELECT SCHEMA_NAME FROM SYS.SCHEMAS WHERE HAS_PRIVILEGES = 'TRUE' ORDER BY SCHEMA_NAME")
schemas = cursor.fetchall()

print("Available schemas:")
for schema in schemas:
    print(f"  - {schema[0]}")

conn.close()
