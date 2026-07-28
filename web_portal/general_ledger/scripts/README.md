# general_ledger scripts

One-off source patches for GL reporting.

Standalone one-off / diagnostic scripts. They are **not** imported by the app -
each bootstraps Django itself and can be run from any working directory:

```
PYTHONUTF8=1 python general_ledger/scripts/<name>.py
```

A few are meant to be piped into the shell instead:

```
PYTHONUTF8=1 python manage.py shell < general_ledger/scripts/<name>.py
```

## Contents

- `fix_sap_logo.py`
