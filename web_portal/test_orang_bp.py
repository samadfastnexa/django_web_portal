import django
django.setup()

from general_ledger.utils import get_hana_connection

# Try 4B-ORANG
conn = get_hana_connection('4B-ORANG')
cur = conn.cursor()

# Check if ORC00002 exists
sql = 'SELECT COUNT(*) FROM "JDT1" WHERE "ShortName" = \'ORC00002\''
cur.execute(sql)
orc_count = cur.fetchone()
print(f'Transactions for ORC00002 in 4B-ORANG: {orc_count[0]}')

# Sample ORC codes
sql2 = 'SELECT DISTINCT "ShortName" FROM "JDT1" WHERE "ShortName" LIKE \'ORC%\' LIMIT 10'
cur.execute(sql2)
rows = cur.fetchall()
print('\nSample BP codes starting with ORC in 4B-ORANG:')
for row in rows:
    print(f'  - {row[0]}')

cur.close()
conn.close()
