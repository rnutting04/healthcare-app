from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Enable PGVector extension in PostgreSQL'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                # Check if extension already exists
                cursor.execute(
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                )
                if cursor.fetchone():
                    self.stdout.write(
                        self.style.SUCCESS('PGVector extension already enabled')
                    )
                else:
                    # Create extension
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    self.stdout.write(
                        self.style.SUCCESS('Successfully enabled PGVector extension')
                    )
        except Exception as e:
            logger.error(f"Error enabling PGVector extension: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Failed to enable PGVector extension: {str(e)}')
            )