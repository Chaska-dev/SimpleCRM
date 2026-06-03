from django.db import migrations, models


def create_system_companies(apps, schema_editor):
    Workspace = apps.get_model("crm", "Workspace")
    Company = apps.get_model("crm", "Company")
    for ws in Workspace.objects.all():
        Company.objects.get_or_create(
            workspace=ws,
            is_workspace=True,
            defaults={"name": ws.name},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0006_city_country_alter_contact_city_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_workspace',
            field=models.BooleanField(db_index=True, default=False, help_text='True for the company that mirrors this workspace. Cannot be deleted.'),
        ),
        migrations.RunPython(create_system_companies, noop_reverse),
    ]
