# Generated manually for RAGDocument model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0002_file_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='RAGDocument',
            fields=[
                ('file', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='rag_document', serialize=False, to='data_management.filemetadata')),
                ('cancer_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='data_management.cancertype')),
            ],
            options={
                'db_table': 'rag_documents',
            },
        ),
        migrations.AddIndex(
            model_name='ragdocument',
            index=models.Index(fields=['cancer_type'], name='rag_documen_cancer__860c4e_idx'),
        ),
    ]
