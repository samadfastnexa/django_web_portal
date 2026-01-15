import django
django.setup()

from general_ledger.utils import get_hana_connection

conn = get_hana_connection('4B-BIO')
cur = conn.cursor()

# Check if ORC00002 exists
sql = 'SELECT DISTINCT "ShortName" FROM "JDT1" WHERE "ShortName" LIKE \'ORC%\' LIMIT 10'
cur.execute(sql)
rows = cur.fetchall()
print('Sample BP codes starting with ORC:')
for row in rows:
    print(f'  - {row[0]}')

# Check total count
sql2 = 'SELECT COUNT(DISTINCT "ShortName") FROM "JDT1"'
cur.execute(sql2)
total = cur.fetchone()
print(f'\nTotal distinct BP codes: {total[0]}')

# Check if ORC00002 specifically exists
sql3 = 'SELECT COUNT(*) FROM "JDT1" WHERE "ShortName" = \'ORC00002\''
cur.execute(sql3)
orc_count = cur.fetchone()
print(f'Transactions for ORC00002: {orc_count[0]}')

cur.close()
conn.close()
