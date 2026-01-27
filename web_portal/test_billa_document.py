"""Test Billa document parsing to check table content"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.utils.document_parser import WordDocumentParser

# Test Billa document
file_path = r"F:\samad\clone tarzan\django_web_portal\web_portal\media\product_images\4B-ORANG\Billa 41.docx"

if os.path.exists(file_path):
    print(f"Testing document: {file_path}")
    print("=" * 80)
    
    parser = WordDocumentParser(file_path)
    
    # Get document info
    info = parser.get_document_info()
    print(f"\nDocument Info:")
    print(f"  Paragraphs: {info.get('paragraphs')}")
    print(f"  Tables: {info.get('tables')}")
    print(f"  Sections: {info.get('sections')}")
    
    # Test mammoth parsing
    print("\n" + "=" * 80)
    print("MAMMOTH PARSING:")
    print("=" * 80)
    html_mammoth, messages = parser.parse_to_html_mammoth()
    if html_mammoth:
        # Save to file
        with open('billa_mammoth_output.html', 'w', encoding='utf-8') as f:
            f.write(html_mammoth)
        print(f"HTML saved to billa_mammoth_output.html")
        print(f"HTML Length: {len(html_mammoth)} characters")
    
    if messages:
        print("\nMessages:")
        for msg in messages:
            print(f"  {msg}")
    
    # Test custom parsing
    print("\n" + "=" * 80)
    print("CUSTOM PARSING:")
    print("=" * 80)
    html_custom = parser.parse_custom_formatting()
    if html_custom:
        # Save to file
        with open('billa_custom_output.html', 'w', encoding='utf-8') as f:
            f.write(html_custom)
        print(f"HTML saved to billa_custom_output.html")
        print(f"HTML Length: {len(html_custom)} characters")
    
    # Check table content specifically
    print("\n" + "=" * 80)
    print("TABLE ANALYSIS:")
    print("=" * 80)
    for i, table in enumerate(parser.doc.tables):
        print(f"\nTable {i+1}:")
        print(f"  Rows: {len(table.rows)}")
        print(f"  Columns: {len(table.columns) if table.rows else 0}")
        
        for row_idx, row in enumerate(table.rows):
            print(f"\n  Row {row_idx + 1}:")
            for cell_idx, cell in enumerate(row.cells):
                print(f"    Cell {cell_idx + 1}: {cell.text.strip()}")
else:
    print(f"File not found: {file_path}")
