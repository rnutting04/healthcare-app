from django.db import migrations

def populate_languages(apps, schema_editor):
    Language = apps.get_model('patients', 'Language')
    
    languages = [
        {'code': 'en', 'name': 'English', 'native_name': 'English', 'display_order': 1},
        {'code': 'ar', 'name': 'Arabic', 'native_name': 'العربية', 'display_order': 2},
        {'code': 'zh', 'name': 'Chinese', 'native_name': '中文', 'display_order': 3},
        {'code': 'fr', 'name': 'French', 'native_name': 'Français', 'display_order': 4},
        {'code': 'hi', 'name': 'Hindi', 'native_name': 'हिन्दी', 'display_order': 5},
        {'code': 'es', 'name': 'Spanish', 'native_name': 'Español', 'display_order': 6},
    ]
    
    for lang_data in languages:
        Language.objects.create(**lang_data)
    
    # Set English as default for all existing patients
    Patient = apps.get_model('patients', 'Patient')
    english = Language.objects.get(code='en')
    Patient.objects.filter(preferred_language__isnull=True).update(preferred_language=english)

def reverse_populate_languages(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    Patient.objects.update(preferred_language=None)
    
    Language = apps.get_model('patients', 'Language')
    Language.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_language_patient_preferred_language'),
    ]

    operations = [
        migrations.RunPython(populate_languages, reverse_populate_languages),
    ]
