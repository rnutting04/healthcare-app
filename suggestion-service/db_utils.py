import os
import json
import logging
from typing import List, Tuple
import numpy as np
import requests
from model import MODEL, l2norm

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("suggestion-service")

# ---- Config ---------------------------------------------------------------
TIMEOUT = float(os.getenv("SVC_HTTP_TIMEOUT", "3.0"))
DB_URL = os.getenv("DB_SERVICE_URL", "http://database-service:8004/api/chat")

def user_headers(user_token: str):
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}

# ---- Utils ----------------------------------------------------------------
def db_last_messages(session_id: str, user_token: str, limit: int = 5) -> List[dict]:
    url = f"{DB_URL}/internal/sessions/last-messages/"
    r = requests.get(url, params={"session_id": session_id, "limit": limit},
                     headers=user_headers(user_token), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json() or []


def db_templates(cancer_type: str, user_token: str) -> Tuple[List[int], List[str], np.ndarray]:
    url = f"{DB_URL}/internal/suggestions/templates/"
    r = requests.get(url, params={"cancer_type": cancer_type},
                     headers=user_headers(user_token), timeout=TIMEOUT)
    r.raise_for_status()
    rows = r.json() or []

    ids   = [row["id"]   for row in rows]
    texts = [row["text"] for row in rows]

    embs = []
    missing = []

    for i, row in enumerate(rows):
        v = row.get("embedding_json", None)
        if v is None:
            vec = MODEL.encode(texts[i], normalize_embeddings=True)
            embs.append(vec)
            missing.append({"id": ids[i], "embedding": vec.tolist()})
        else:
            if isinstance(v, str):
                v = json.loads(v)
            embs.append(np.array(v, dtype=np.float32))

    arr = np.vstack(embs) if embs else np.zeros((0,384), dtype=np.float32)
    arr = l2norm(arr) if arr.size else arr

    # push new embeddings back to DB (best-effort)
    if missing:
        try:
            requests.post(
                f"{DB_URL}/internal/suggestions/upsert-embeddings/",
                headers=user_headers(user_token),
                json={"items": missing},
                timeout=TIMEOUT
            ).raise_for_status()
        except Exception as e:
            log.warning(f"Embedding backfill POST failed: {e}")

    return ids, texts, arr

def db_history(session_id: str, user_token: str) -> List[str]:
    url = f"{DB_URL}/internal/suggestions/history/"
    r = requests.get(url, params={"session_id": session_id},
                     headers=user_headers(user_token), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json() or []

def db_set_last4(session_id: str, items: List[str], user_token: str) -> None:
    url = f"{DB_URL}/suggestions/"
    requests.post(url, headers=user_headers(user_token),
                  json={"session_id": session_id, "suggestions": items[:4]},
                  timeout=TIMEOUT).raise_for_status()

def db_append_history(session_id: str, items: List[str], user_token: str) -> None:
    url = f"{DB_URL}/internal/suggestions/history/"
    requests.post(url, headers=user_headers(user_token),
                  json={"session_id": session_id, "items": items[:4]},
                  timeout=TIMEOUT).raise_for_status()

