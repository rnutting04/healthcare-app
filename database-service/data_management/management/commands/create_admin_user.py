from django.core.management.base import BaseCommand
from django.db import transaction
from data_management.models import User, Role


class Command(BaseCommand):
    help = 'Creates an admin user if it does not exist'

    def handle(self, *args, **options):
        email = 'admin@example.com'
        
        try:
            with transaction.atomic():
                # Check if admin role exists, create if not
                admin_role, created = Role.objects.get_or_create(
                    name='ADMIN',
                    defaults={
                        'display_name': 'Administrator',
                        'description': 'System administrator with full access'
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS('Created ADMIN role'))
                
                # Check if admin user already exists
                if User.objects.filter(email=email).exists():
                    self.stdout.write(self.style.WARNING(f'Admin user {email} already exists'))
                    return
                
                # Create the admin user
                admin_user = User.objects.create_user(
                    email=email,
                    password='adminpass',
                    first_name='Admin',
                    last_name='Example',
                    role=admin_role,
                    is_active=True
                )
                
                self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {email}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))