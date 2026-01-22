"""
Test document parser with actual product files
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.utils.document_parser import (
    parse_product_document, 
    get_product_document_path,
    WordDocumentParser
)
from django.conf import settings

print("=" * 80)
print("Testing Product Document Parser")
print("=" * 80)

# Test files
test_files = [
    {
        'name': 'Agroquat 20 SL',
        'ext': 'docx',
        'database': '4B-ORANG_APP'
    },
    {
        'name': 'Billa 41',
        'ext': 'docx',
        'database': '4B-ORANG_APP'
    },
    {
        'name': 'Gabru',
        'ext': 'docx',
        'database': '4B-ORANG_APP'
    }
]

for test_file in test_files:
    print(f"\n{'='*80}")
    print(f"Testing: {test_file['name']}.{test_file['ext']}")
    print(f"{'='*80}")
    
    # Get file path
    file_path = get_product_document_path(
        test_file['name'], 
        test_file['ext'], 
        test_file['database']
    )
    
    if file_path:
        print(f"✓ File found: {file_path}")
        
        # Get document info
        parser = WordDocumentParser(file_path)
        doc_info = parser.get_document_info()
        
        print(f"\nDocument Info:")
        print(f"  - Paragraphs: {doc_info.get('paragraphs', 0)}")
        print(f"  - Tables: {doc_info.get('tables', 0)}")
        print(f"  - Sections: {doc_info.get('sections', 0)}")
        
        # Parse with Mammoth
        print(f"\n{'─'*80}")
        print("Parsing with Mammoth method...")
        print(f"{'─'*80}")
        
        html_content = parse_product_document(file_path, method='mammoth')
        
        if html_content:
            # Show first 500 characters
            print(f"\nFirst 500 characters of HTML:")
            print(html_content[:500])
            print(f"\n... (Total length: {len(html_content)} characters)")
            
            # Check for tables
            if '<table' in html_content:
                table_count = html_content.count('<table')
                print(f"\n✓ Found {table_count} table(s) in HTML")
            
            # Check for headings
            if '<h1' in html_content or '<h2' in html_content:
                h1_count = html_content.count('<h1')
                h2_count = html_content.count('<h2')
                print(f"✓ Found {h1_count} H1 heading(s) and {h2_count} H2 heading(s)")
            
            # Check for images
            if 'data:image' in html_content:
                img_count = html_content.count('data:image')
                print(f"✓ Found {img_count} embedded image(s)")
        else:
            print("✗ Failed to parse document")
        
        # Parse with Custom method
        print(f"\n{'─'*80}")
        print("Parsing with Custom method...")
        print(f"{'─'*80}")
        
        html_content_custom = parse_product_document(file_path, method='custom')
        
        if html_content_custom:
            print(f"\nFirst 500 characters of HTML:")
            print(html_content_custom[:500])
            print(f"\n... (Total length: {len(html_content_custom)} characters)")
        else:
            print("✗ Failed to parse document with custom method")
            
    else:
        print(f"✗ File not found for: {test_file['name']}.{test_file['ext']}")

print(f"\n{'='*80}")
print("Testing Complete!")
print(f"{'='*80}")

# List all .docx files in the folders
print(f"\n{'='*80}")
print("Available .docx files:")
print(f"{'='*80}")

media_root = settings.MEDIA_ROOT
for folder in ['4B-ORANG', '4B-BIO']:
    folder_path = os.path.join(media_root, 'product_images', folder)
    if os.path.exists(folder_path):
        print(f"\n{folder}:")
        docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx')]
        for idx, file in enumerate(docx_files[:10], 1):  # Show first 10
            print(f"  {idx}. {file}")
        if len(docx_files) > 10:
            print(f"  ... and {len(docx_files) - 10} more files")
        print(f"  Total: {len(docx_files)} .docx files")
