import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from data_management.models import CancerType


class Command(BaseCommand):
    help = 'Import cancer types from cancer_types.json file. This command is idempotent.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='cancer_types.json',
            help='Path to the cancer_types.json file (default: cancer_types.json in project root)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing cancer types before importing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        clear_existing = options['clear']
        
        # If relative path, assume it's relative to the current working directory
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        
        try:
            # Load JSON data
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract results array
            cancer_types_data = data.get('results', [])
            
            if not cancer_types_data:
                self.stdout.write(self.style.WARNING('No cancer types found in the JSON file'))
                return
            
            with transaction.atomic():
                # Optionally clear existing data
                if clear_existing:
                    CancerType.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS('Cleared all existing cancer types'))
                
                # Create a mapping of old IDs to new cancer type objects
                id_mapping = {}
                parent_mapping = {}  # Store parent relationships to process later
                
                # First pass: Create all cancer types without parent relationships
                created_count = 0
                updated_count = 0
                
                for ct_data in cancer_types_data:
                    old_id = ct_data['id']
                    cancer_type_name = ct_data['cancer_type']
                    description = ct_data.get('description', '')
                    parent_id = ct_data.get('parent')
                    
                    # Store parent relationship for later
                    if parent_id:
                        parent_mapping[old_id] = parent_id
                    
                    # Get or create the cancer type
                    cancer_type, created = CancerType.objects.get_or_create(
                        cancer_type=cancer_type_name,
                        defaults={
                            'description': description,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(f'Created: {cancer_type_name}')
                    else:
                        # Update description if it has changed
                        if cancer_type.description != description:
                            cancer_type.description = description
                            cancer_type.save()
                            updated_count += 1
                            self.stdout.write(f'Updated: {cancer_type_name}')
                    
                    # Store mapping
                    id_mapping[old_id] = cancer_type
                
                # Second pass: Set up parent relationships
                relationships_updated = 0
                for old_id, parent_id in parent_mapping.items():
                    cancer_type = id_mapping.get(old_id)
                    parent_cancer_type = id_mapping.get(parent_id)
                    
                    if cancer_type and parent_cancer_type:
                        if cancer_type.parent != parent_cancer_type:
                            cancer_type.parent = parent_cancer_type
                            cancer_type.save()
                            relationships_updated += 1
                            self.stdout.write(
                                f'Set parent: {cancer_type.cancer_type} -> {parent_cancer_type.cancer_type}'
                            )
                
                # Summary
                self.stdout.write(self.style.SUCCESS(
                    f'\nImport completed successfully:\n'
                    f'- Created: {created_count} cancer types\n'
                    f'- Updated: {updated_count} cancer types\n'
                    f'- Parent relationships updated: {relationships_updated}\n'
                    f'- Total cancer types in database: {CancerType.objects.count()}'
                ))
                
                # Show hierarchy
                self.stdout.write(self.style.SUCCESS('\nCancer Type Hierarchy:'))
                self._print_hierarchy()
                
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON file: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing cancer types: {str(e)}'))
    
    def _print_hierarchy(self, parent=None, level=0):
        """Recursively print the cancer type hierarchy"""
        cancer_types = CancerType.objects.filter(parent=parent).order_by('cancer_type')
        
        for ct in cancer_types:
            indent = '  ' * level + ('└─ ' if level > 0 else '')
            self.stdout.write(f'{indent}{ct.cancer_type}')
            # Print subtypes
            self._print_hierarchy(parent=ct, level=level + 1)