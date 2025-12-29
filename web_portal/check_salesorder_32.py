import os
import sys
import django
import json

# Setup Django environment
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
try:
    django.setup()
except Exception as e:
    print(f"Warning: Django setup failed ({e})")

from FieldAdvisoryService.models import SalesOrder

def check_order():
    try:
        order = SalesOrder.objects.get(pk=32)
        print(f"--- SalesOrder #{order.pk} ---")
        print(f"CardCode: {order.card_code}")
        print(f"CardName: {order.card_name}")
        print(f"DocDate: {order.doc_date}")
        print(f"Status: {order.status}")
        print(f"Posted to SAP: {order.is_posted_to_sap}")
        print(f"SAP DocEntry: {order.sap_doc_entry}")
        print(f"SAP DocNum: {order.sap_doc_num}")
        print(f"SAP Error: {order.sap_error}")
        
        if order.sap_response_json:
            print("SAP Response JSON (first 500 chars):")
            print(order.sap_response_json[:500] + "...")
        
        print("\n--- Document Lines ---")
        for line in order.document_lines.all():
            print(f"Line {line.line_num}: {line.item_code} - {line.quantity} x {line.unit_price}")

    except SalesOrder.DoesNotExist:
        print("SalesOrder #32 does not exist.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_order()
