"""
Test script to verify analytics API is wired correctly
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.urls import get_resolver

def test_analytics_urls():
    """Check if analytics URLs are registered"""
    resolver = get_resolver()
    
    analytics_urls = [
        '/api/analytics/dashboard/overview/',
        '/api/analytics/sales/',
        '/api/analytics/farmers/',
        '/api/analytics/performance/',
    ]
    
    print("=" * 60)
    print("ANALYTICS API URL VERIFICATION")
    print("=" * 60)
    
    for url in analytics_urls:
        try:
            match = resolver.resolve(url)
            print(f"✓ {url}")
            print(f"  View: {match.func.__name__ if hasattr(match.func, '__name__') else match.func.view_class.__name__}")
        except Exception as e:
            print(f"✗ {url}")
            print(f"  Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("EXISTING ANALYTICS-RELATED ENDPOINTS")
    print("=" * 60)
    
    # Check existing analytics endpoint in preferences
    try:
        match = resolver.resolve('/api/analytics/overview/')
        print(f"✓ /api/analytics/overview/ (preferences app)")
    except Exception:
        print(f"✗ /api/analytics/overview/ not found")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_analytics_urls()
