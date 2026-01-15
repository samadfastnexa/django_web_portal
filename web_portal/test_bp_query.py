import django
django.setup()

from general_ledger.utils import get_hana_connection
from general_ledger import hana_queries

conn = get_hana_connection('4B-BIO')

# Test with string
count_str = hana_queries.general_ledger_count(conn, bp_code='ORC00002')
print(f'Count with string: {count_str}')

trans_str = hana_queries.general_ledger_report(conn, bp_code='ORC00002', limit=5)
print(f'Transactions with string: {len(trans_str)}')
if trans_str:
    print(f'First trans BP: {trans_str[0].get("BPCode")}')

# Test with list
count_list = hana_queries.general_ledger_count(conn, bp_code=['ORC00002'])
print(f'Count with list: {count_list}')

trans_list = hana_queries.general_ledger_report(conn, bp_code=['ORC00002'], limit=5)
print(f'Transactions with list: {len(trans_list)}')
if trans_list:
    print(f'First trans BP: {trans_list[0].get("BPCode")}')

conn.close()
