from django.db import migrations


ACCESS_PROFILES = [
    'Administrador',
    'Gerente',
    'Vendedor',
    'Estoquista',
]


def create_access_profiles(apps, schema_editor):
    group_model = apps.get_model('auth', 'Group')
    for profile_name in ACCESS_PROFILES:
        group_model.objects.get_or_create(name=profile_name)


def remove_access_profiles(apps, schema_editor):
    group_model = apps.get_model('auth', 'Group')
    group_model.objects.filter(name__in=ACCESS_PROFILES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_access_profiles, remove_access_profiles),
    ]
