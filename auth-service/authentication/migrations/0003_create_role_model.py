# Manual migration to handle the conversion from CharField to ForeignKey for role
from django.db import migrations, models
import django.db.models.deletion

def migrate_roles_forward(apps, schema_editor):
    """Convert existing role CharField values to Role objects"""
    User = apps.get_model('authentication', 'User')
    Role = apps.get_model('authentication', 'Role')
    
    # Create the initial roles
    roles_data = {
        'PATIENT': ('Patient', 'Patient users who can view their medical records and book appointments'),
        'CLINICIAN': ('Clinician', 'Healthcare providers who can manage patient records and appointments'),
        'ADMIN': ('Administrator', 'System administrators with full access to all features')
    }
    
    role_objects = {}
    for name, (display_name, description) in roles_data.items():
        role, _ = Role.objects.get_or_create(
            name=name,
            defaults={
                'display_name': display_name,
                'description': description
            }
        )
        role_objects[name] = role
    
    # Update existing users
    for user in User.objects.all():
        if hasattr(user, 'role_old') and user.role_old:
            user.role_id = role_objects.get(user.role_old, role_objects['PATIENT']).id
            user.save()

def migrate_roles_backward(apps, schema_editor):
    """Convert Role objects back to CharField values"""
    User = apps.get_model('authentication', 'User')
    
    # Update users back to string values
    for user in User.objects.all():
        if user.role_id:
            role = user.role
            user.role_old = role.name if role else 'PATIENT'
            user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_remove_user_address_remove_user_date_of_birth_and_more'),
    ]

    operations = [
        # First, create the Role model
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, unique=True)),
                ('display_name', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Role',
                'verbose_name_plural': 'Roles',
                'db_table': 'roles',
                'ordering': ['name'],
            },
        ),
        
        # Rename the old role field temporarily
        migrations.RenameField(
            model_name='user',
            old_name='role',
            new_name='role_old',
        ),
        
        # Add the new ForeignKey field (nullable initially)
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='authentication.role'),
        ),
        
        # Migrate the data
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
        
        # Make the role field required
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='users', to='authentication.role'),
        ),
        
        # Remove the old field
        migrations.RemoveField(
            model_name='user',
            name='role_old',
        ),
    ]
