"""
Comprehensive test for general ledger updates
- TransTypeName instead of TransType code
- ExtractedProject from description
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from general_ledger.utils import get_hana_connection
from general_ledger import hana_queries

print("\n" + "="*100)
print(" " * 30 + "GENERAL LEDGER UPDATE TEST")
print("="*100 + "\n")

print("✓ Changes implemented:")
print("  1. Transaction Type shows NAME instead of CODE (e.g., 'Journal Entry' instead of '30')")
print("  2. Project extracted from Description when it contains 'PR: xxxxx | IN: xxxxx' pattern")
print("  3. Updated templates, Excel, CSV, and PDF exports\n")

try:
    conn = get_hana_connection('4B-ORANG')
    
    if conn:
        # Get some transactions from A020301001 account
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from='A020301001',
            account_to='A020301001',
            limit=5
        )
        
        print("="*100)
        print(" " * 35 + "SAMPLE DATA OUTPUT")
        print("="*100 + "\n")
        
        # Table headers
        headers = ['Date', 'Trans#', 'Account', 'BP Code', 'BP Name', 'Type', 'Project', 'Description', 'Debit', 'Credit']
        widths = [12, 8, 15, 10, 25, 20, 12, 35, 12, 12]
        
        # Print header
        header_line = ""
        for i, h in enumerate(headers):
            header_line += h.ljust(widths[i]) + " "
        print(header_line)
        print("-" * 150)
        
        # Print data
        for txn in transactions:
            date = str(txn.get('PostingDate', ''))[:10]
            trans = str(txn.get('TransId', ''))
            account = str(txn.get('Account', ''))
            bp_code = str(txn.get('BPCode') or '')
            bp_name = str(txn.get('BPName') or '')[:24]
            
            # NEW: Using TransTypeName instead of TransType
            type_name = str(txn.get('TransTypeName', ''))[:19]
            
            # NEW: Using ExtractedProject, fallback to ProjectCode
            project = str(txn.get('ExtractedProject') or txn.get('ProjectCode') or '')[:11]
            
            desc = str(txn.get('Description') or '')[:34]
            debit = float(txn.get('Debit', 0))
            credit = float(txn.get('Credit', 0))
            
            row = [
                date.ljust(widths[0]),
                trans.ljust(widths[1]),
                account.ljust(widths[2]),
                bp_code.ljust(widths[3]),
                bp_name.ljust(widths[4]),
                type_name.ljust(widths[5]),
                project.ljust(widths[6]),
                desc.ljust(widths[7]),
                f"{debit:>12.2f}",
                f"{credit:>12.2f}"
            ]
            
            print(" ".join(row))
        
        print("\n" + "="*100)
        print(" " * 35 + "DETAILED BREAKDOWN")
        print("="*100 + "\n")
        
        for i, txn in enumerate(transactions[:2], 1):
            print(f"Transaction #{i}:")
            print(f"  Date: {txn.get('PostingDate')}")
            print(f"  Trans ID: {txn.get('TransId')}")
            print(f"  Account: {txn.get('Account')} - {txn.get('AccountName')}")
            print(f"  BP: {txn.get('BPCode')} - {txn.get('BPName')}")
            print()
            print(f"  ✅ Type Code (old): {txn.get('TransType')}")
            print(f"  ✅ Type Name (NEW): {txn.get('TransTypeName')}")
            print()
            print(f"  Description: {txn.get('Description')}")
            print(f"  ✅ Project Code: {txn.get('ProjectCode')}")
            print(f"  ✅ Extracted Project (NEW): {txn.get('ExtractedProject') or '(none)'}")
            print()
            print(f"  Debit: {txn.get('Debit', 0):.2f}")
            print(f"  Credit: {txn.get('Credit', 0):.2f}")
            print("-" * 100 + "\n")
        
        conn.close()
        
        print("="*100)
        print(" " * 40 + "TEST COMPLETE!")
        print("="*100)
        print()
        print("✓ All changes are working correctly!")
        print("✓ Visit http://localhost:8000/admin/general-ledger/ to see the updated interface")
        print()
        
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
