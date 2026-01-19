from django.db import connection

with connection.cursor() as cursor:
    cursor.execute('DESCRIBE accounts_salesstaffprofile')
    rows = cursor.fetchall()
    print("\nTable Structure:")
    print(f"{'Field':<30} {'Type':<30} {'Null':<10} {'Key':<10}")
    print("-" * 80)
    for row in rows:
        print(f"{row[0]:<30} {row[1]:<30} {row[2]:<10} {row[3]:<10}")
