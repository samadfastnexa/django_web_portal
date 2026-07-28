# FieldAdvisoryService scripts

Territory/hierarchy mapping, dealer imports and sales-order checks.

Standalone one-off / diagnostic scripts. They are **not** imported by the app -
each bootstraps Django itself and can be run from any working directory:

```
PYTHONUTF8=1 python FieldAdvisoryService/scripts/<name>.py
```

A few are meant to be piped into the shell instead:

```
PYTHONUTF8=1 python manage.py shell < FieldAdvisoryService/scripts/<name>.py
```

## Contents

- `final_verification.py`
- `fix_salesorder_32.py`
- `generate_and_import_agri_hierarchy.py`
- `import_orange_dealers.py`
- `map_hana_territories.py`
- `match_territories.py`
