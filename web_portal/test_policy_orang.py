import sys
import json
import os

import requests


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_policy_orang.py <CARD_CODE>")
        sys.exit(1)

    card_code = sys.argv[1].strip()
    if not card_code:
        print("CARD_CODE cannot be empty")
        sys.exit(1)

    base_url = os.environ.get("TARZAN_BASE_URL", "http://localhost:8000")
    url = f"{base_url.rstrip('/')}/api/sap/policy-customer-balance/{card_code}/"
    params = {
        "database": "4B-ORANG",
        "limit": "200",
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

    print(f"HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError:
        print(resp.text)
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))

    if resp.status_code == 200 and data.get("success") and data.get("data"):
        print("\nSummary:")
        for row in data["data"]:
            card = row.get("CardCode")
            name = row.get("CardName")
            proj = row.get("Project")
            prj_name = row.get("PrjName")
            bal = row.get("Balance")
            print(f"- {card} | {name} | {proj} | {prj_name} | Balance={bal}")


if __name__ == "__main__":
    main()

