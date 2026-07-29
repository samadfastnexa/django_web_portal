# accounts scripts

User, designation and permission maintenance scripts.

Standalone one-off / diagnostic scripts. They are **not** imported by the app -
each bootstraps Django itself and can be run from any working directory:

```
PYTHONUTF8=1 python accounts/scripts/<name>.py
```

A few are meant to be piped into the shell instead:

```
PYTHONUTF8=1 python manage.py shell < accounts/scripts/<name>.py
```

## Contents

- `check_employee_assignments.py`
- `cleanup_test_permissions.py`
- `create_missing_users.py`
- `create_phone_user.py`
- `find_duplicate_employee_codes.py`
- `fix_designation_data.py`
- `generate_and_import_agri_sales_staff.py`
- `grant_organogram_permission.py`
- `map_remaining_designations.py`
- `migrate_existing_designations.py`
- `populate_designations.py`
- `show_phone_users.py`
