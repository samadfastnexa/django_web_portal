# sap_integration scripts

SAP HANA / Service Layer diagnostics, dealer & territory scope checks, one-off data fixes.

Standalone one-off / diagnostic scripts. They are **not** imported by the app -
each bootstraps Django itself and can be run from any working directory:

```
PYTHONUTF8=1 python sap_integration/scripts/<name>.py
```

A few are meant to be piped into the shell instead:

```
PYTHONUTF8=1 python manage.py shell < sap_integration/scripts/<name>.py
```

## Contents

- `check_b4_sales_target_django.py`
- `check_dealer_scope.py`
- `check_sales_target_comprehensive.py`
- `check_sales_target_simple.py`
- `debug_territory_mapping.py`
- `debug_territory_query.py`
- `demo_product_display.py`
- `find_parents_with_children.py`
- `fix_recommended_products.py`
- `fix_sap_company_db_setting.py`
- `item_price_diagnostic.py`
- `list_schemas.py`
- `new_recommended_products_api.py`
- `quick_sap_test.py`
- `quick_test_item_price.py`
- `sap_check_cardcode.py`
- `sync_and_check.py`
