import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.apps import apps

# Get all non-abstract models
models = [m for m in apps.get_models() if not m._meta.abstract]

print(f"\n{'='*60}")
print(f"TOTAL DATABASE MODELS: {len(models)}")
print(f"{'='*60}\n")

# Group by app
apps_dict = {}
for model in models:
    app_label = model._meta.app_label
    if app_label not in apps_dict:
        apps_dict[app_label] = []
    apps_dict[app_label].append(model)

# Display by app
for app_label in sorted(apps_dict.keys()):
    app_models = apps_dict[app_label]
    print(f"\n{app_label} ({len(app_models)} models):")
    print("-" * 60)
    for model in sorted(app_models, key=lambda m: m.__name__):
        has_db_table = hasattr(model._meta, 'db_table') and model._meta.db_table
        status = "✓" if has_db_table else "✗"
        db_table_name = model._meta.db_table if has_db_table else "(default)"
        print(f"  {status} {model.__name__:40} → {db_table_name}")

# Check for missing db_table
print(f"\n{'='*60}")
models_without_explicit_table = []
for model in models:
    # Django auto-generates db_table, so we check if it was explicitly set
    # by checking if db_table contains the app label and model name in lowercase
    expected_default = f"{model._meta.app_label}_{model._meta.model_name}"
    if model._meta.db_table == expected_default:
        # This is likely the default, check if it was explicitly set in Meta
        if not hasattr(model.Meta, 'db_table') if hasattr(model, 'Meta') else True:
            models_without_explicit_table.append(f"{model._meta.app_label}.{model.__name__}")

if models_without_explicit_table:
    print(f"⚠️  Models possibly using default db_table: {len(models_without_explicit_table)}")
    for model_name in models_without_explicit_table:
        print(f"  - {model_name}")
else:
    print("✓ All models appear to have explicit db_table configuration")

print(f"\n{'='*60}\n")
