# Generated migration for file storage models
# This file should be copied to database-service/data_management/migrations/

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("data_management", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserEncryptionKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("rotated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="encryption_key", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "user_encryption_keys",
            },
        ),
        migrations.CreateModel(
            name="FileMetadata",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("filename", models.CharField(max_length=255)),
                ("file_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("file_size", models.BigIntegerField()),
                ("mime_type", models.CharField(max_length=100)),
                ("storage_path", models.CharField(max_length=500)),
                ("is_encrypted", models.BooleanField(default=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("last_accessed", models.DateTimeField(blank=True, null=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "file_metadata",
                "ordering": ["-uploaded_at"],
                "indexes": [
                    models.Index(fields=["user", "-uploaded_at"], name="file_metada_user_id_aa5879_idx"),
                    models.Index(fields=["file_hash"], name="file_metada_file_ha_c91f5a_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="FileAccessLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("access_type", models.CharField(choices=[("upload", "Upload"), ("download", "Download"), ("delete", "Delete"), ("view", "View")], max_length=20)),
                ("accessed_at", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=500, null=True)),
                ("success", models.BooleanField(default=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                ("file", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_logs", to="data_management.filemetadata")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "file_access_logs",
                "ordering": ["-accessed_at"],
                "indexes": [
                    models.Index(fields=["file", "-accessed_at"], name="file_access_file_id_a5e2f6_idx"),
                    models.Index(fields=["user", "-accessed_at"], name="file_access_user_id_5d0e2b_idx"),
                ],
            },
        ),
    ]