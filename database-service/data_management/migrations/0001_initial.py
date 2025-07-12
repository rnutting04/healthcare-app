# This migration marks existing models as already created
from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    
    dependencies = [
    ]
    
    operations = [
        # All existing models are already in the database
        # This migration is just to mark them as migrated
    ]
