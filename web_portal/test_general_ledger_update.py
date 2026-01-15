"""
Test the updated general ledger with TransType name and project extraction
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from general_ledger.utils import get_hana_connection
from general_ledger import hana_queries

print("\n" + "="*80)
print("  Testing General Ledger with TransType Name and Project Extraction")
print("="*80 + "\n")

try:
    conn = get_hana_connection('4B-ORANG')
    
    if conn:
        # Test with A020301001 account first to see all BPs
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from='A020301001',
            account_to='A020301001',
            limit=20
        )
        
        print(f"Found {len(transactions)} transactions for A020301001 account:\n")
        print("="*80)
        
        for txn in transactions:
            print(f"Date: {txn.get('PostingDate')}")
            print(f"Trans#: {txn.get('TransId')}")
            print(f"Account: {txn.get('Account')} - {txn.get('AccountName')}")
            print(f"BP: {txn.get('BPCode')} - {txn.get('BPName')}")
            print(f"Type Code: {txn.get('TransType')}")
            print(f"Type Name: {txn.get('TransTypeName')}")  # NEW
            print(f"Reference: {txn.get('Reference1')}")
            print(f"Description: {txn.get('Description')}")
            print(f"Project Code: {txn.get('ProjectCode')}")
            print(f"Project Name: {txn.get('ProjectName')}")
            print(f"Extracted Project: {txn.get('ExtractedProject')}")  # NEW
            print(f"Debit: {txn.get('Debit', 0):.2f}")
            print(f"Credit: {txn.get('Credit', 0):.2f}")
            print("-" * 80)
        
        # Show table format like in admin
        print("\n" + "="*80)
        print("  TABLE VIEW (like in admin)")
        print("="*80 + "\n")
        
        print(f"{'Date':<12} {'Trans#':<8} {'Account':<15} {'BP Code':<10} {'BP Name':<25} {'Type':<20} {'Project':<10} {'Description':<30} {'Debit':<12} {'Credit':<12}")
        print("-" * 180)
        
        for txn in transactions[:5]:
            date = str(txn.get('PostingDate', ''))[:10]
            trans = str(txn.get('TransId', ''))
            account = str(txn.get('Account', ''))
            bp_code = str(txn.get('BPCode', '') or '')
            bp_name = str(txn.get('BPName', '') or '')[:24]
            type_name = str(txn.get('TransTypeName', ''))[:19]  # NEW - using name instead of code
            project = str(txn.get('ExtractedProject', '') or txn.get('ProjectCode', '') or '')[:9]  # NEW - extracted project
            desc = str(txn.get('Description', '') or '')[:29]
            debit = float(txn.get('Debit', 0))
            credit = float(txn.get('Credit', 0))
            
            print(f"{date:<12} {trans:<8} {account:<15} {bp_code:<10} {bp_name:<25} {type_name:<20} {project:<10} {desc:<30} {debit:>12.2f} {credit:>12.2f}")
        
        conn.close()
        print("\n✓ Test completed successfully\n")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("="*80 + "\n")
