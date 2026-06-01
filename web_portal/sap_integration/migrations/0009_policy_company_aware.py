from django.db import migrations, models


def clear_legacy_policies(apps, schema_editor):
    """Remove pre-existing, company-agnostic policy rows.

    Before this migration every "Sync Policies" run from any company dumped
    its policies into one shared table keyed only by `code`, with no record of
    which company they belonged to. Those rows are an un-attributable mix and
    are fully re-syncable from SAP, so we clear them. After this migration each
    sync is scoped to a company and stores `database`.
    """
    Policy = apps.get_model('sap_integration', 'Policy')
    Policy.objects.all().delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sap_integration', '0008_fix_table_names_lowercase'),
    ]

    operations = [
        # Clear legacy rows first so dropping the unique-on-code and adding the
        # composite unique constraint cannot collide.
        migrations.RunPython(clear_legacy_policies, noop),
        migrations.AddField(
            model_name='policy',
            name='database',
            field=models.CharField(db_index=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='policy',
            name='code',
            field=models.CharField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name='policy',
            constraint=models.UniqueConstraint(fields=('database', 'code'), name='uniq_policy_database_code'),
        ),
    ]
