import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from data_management.models import SuggestionTemplate, CancerType

class Command(BaseCommand):
    help = (
        "Import suggestion questions grouped by cancer_type from a JSON file. "
        "Idempotent: uses (cancer_type, text) uniqueness."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="suggestions.json",
            help="Path to the suggestions JSON (default: ./suggestions.json)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing suggestion templates before importing",
        )
        parser.add_argument(
            "--compute-embeddings",
            action="store_true",
            help="Optionally compute and store embedding_json for each question "
                 "(requires sentence-transformers installed).",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="all-MiniLM-L6-v2",
            help="Embedding model name (used only if --compute-embeddings).",
        )

    def handle(self, *args, **opts):
        file_path = opts["file"]
        clear_existing = opts["clear"]
        do_embed = opts["compute_embeddings"]
        model_name = opts["model"]

        # Resolve relative path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON: {e}"))
            return

        # Accept either an array or an object with 'results'
        blocks = data["results"] if isinstance(data, dict) and "results" in data else data
        if not isinstance(blocks, list) or not blocks:
            self.stdout.write(self.style.WARNING("No suggestion blocks found in JSON"))
            return

        #  import for embeddings
        model = None
        if do_embed:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_name)
                self.stdout.write(self.style.NOTICE(f"Embedding model loaded: {model_name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to load embedding model '{model_name}': {e}"
                ))
                return

        created = 0
        updated_embed = 0
        total = 0

        with transaction.atomic():
            if clear_existing:
                SuggestionTemplate.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("Cleared existing suggestion templates"))

            for block in blocks:
                cancer_type = (block.get("cancer_type_name") or block.get("cancer_type") or "").strip().lower()
                questions = block.get("questions") or []
                if not cancer_type or not questions:
                    continue
                try:
                    cancer_type_obj = CancerType.objects.get(cancer_type__iexact=cancer_type, parent__isnull=True) # match top level cancer type
                except CancerType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"No cancer type found for {cancer_type} - skipping"))
                    continue

                # Compute embeddings in a batch if requested
                embeddings = None
                if do_embed:
                    try:
                        embeddings = model.encode(questions, normalize_embeddings=True)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Embedding failed: {e}"))
                        return

                for idx, q in enumerate(questions):
                    text = (q or "").strip()
                    if not text:
                        continue
                    defaults = {}
                    if do_embed and embeddings is not None:
                        defaults["embedding_json"] = json.dumps(embeddings[idx].tolist())

                    obj, made = SuggestionTemplate.objects.get_or_create(
                        cancer_type=cancer_type_obj,
                        text=text,
                        defaults=defaults,
                    )
                    if made:
                        created += 1
                    else:
                        # chose to compute embeddings and none stored yet, update
                        if do_embed and (not obj.embedding_json) and embeddings is not None:
                            obj.embedding_json = json.dumps(embeddings[idx].tolist())
                            obj.save(update_fields=["embedding_json"])
                            updated_embed += 1

                    total += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nSuggestions import completed:\n"
            f"- Read: {total} questions across cancer types\n"
            f"- Created: {created} new templates\n"
            f"- Updated embeddings: {updated_embed}\n"
            f"- Total templates in DB: {SuggestionTemplate.objects.count()}"
        ))
