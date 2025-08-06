# Generated migration to remove embedding models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0004_rename_chunk_text_preview_to_chunk_text'),
    ]

    operations = [
        # First remove the models from Django's migration state
        # This needs to happen before dropping the tables
        migrations.RemoveField(
            model_name='embeddingchunk',
            name='document_embedding',
        ),
        migrations.DeleteModel(
            name='EmbeddingChunk',
        ),
        migrations.DeleteModel(
            name='DocumentEmbedding',
        ),
        
        # Then drop the tables if they exist
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS embedding_chunks CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[]
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS document_embeddings CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[]
        ),
    ]