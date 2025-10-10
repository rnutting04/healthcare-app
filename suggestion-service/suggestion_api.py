import logging
import hashlib
import numpy as np
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from auth import require_jwt  # should return {"token": <raw user jwt>, "claims": {...}}
from db_utils import db_last_messages, db_templates, db_history, db_set_last4
from model import MODEL, USED_SIM_THRESHOLD

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("suggestion-service")


app = FastAPI(title="Suggestion Service")

# ---- Request model --------------------------------------------------------
class SuggestReq(BaseModel):
    session_id: str
    cancer_type: str | None = "uterine"

def _norm(s: str) -> str:
    """Normalize text for exact-match comparison (case/whitespace insensitive)."""
    return " ".join((s or "").lower().strip().split())

def _stable_shuffle(indices: list[int], seed_text: str) -> list[int]:
    """Deterministically shuffle indices using a seed derived from session+context."""
    if not indices:
        return []
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    arr = np.array(indices, dtype=np.int64)
    rng.shuffle(arr)
    return arr.tolist()

@app.post("/suggest")
def suggest(body: SuggestReq, user=Depends(require_jwt)):
    # pull user token (require_jwt returns dict or raw string)
    user_token = user["token"] if isinstance(user, dict) and "token" in user else user
    if not user_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth context")

    cancer_type = (body.cancer_type or "Uterine Cancer").strip()
    log.info(f"Suggesting for cancer type {cancer_type}")

    # 1) latest user message to drive similarity
    try:
        last_msgs = db_last_messages(body.session_id, user_token, limit=5)
    except Exception as e:
        log.warning(f"DB last-messages fetch failed: {e}")
        last_msgs = []

    last_user_msg = next(
        (m.get("content", "") for m in reversed(last_msgs)
         if m.get("role") == "user" and m.get("content")),
        ""
    )
    convo_tail_text = last_user_msg or "\n".join(
        f"{m.get('role')}: {m.get('content','')}" for m in last_msgs[-3:]
    )

    # 2) templates + embeddings (lazy backfill inside db_templates)
    try:
        _, texts, embs = db_templates(cancer_type, user_token)
    except Exception as e:
        log.error(f"DB templates fetch failed: {e}")
        return {"top_4": [], "top_15": []}

    if embs.shape[0] == 0:
        return {"top_4": [], "top_15": []}

    # 3) score vs current query
    if convo_tail_text.strip():
        q_emb = MODEL.encode(convo_tail_text, normalize_embeddings=True, show_progress_bar=False)
    else:
        q_emb = np.zeros(embs.shape[1], dtype=np.float32)
    scores = embs @ q_emb

    # 4) filter: never suggest anything already asked in this session
    try:
        history = db_history(body.session_id, user_token)  # list[str]
    except Exception as e:
        log.warning(f"DB history fetch failed: {e}")
        history = []
    asked = {_norm(t) for t in history}
    candidates = [i for i, t in enumerate(texts) if _norm(t) not in asked]

    # also drop questions VERY similar to the current user message
    if convo_tail_text.strip() and candidates:
        candidates = [i for i in candidates if float(scores[i]) < USED_SIM_THRESHOLD]

    # fallback: if all filtered by similarity, keep "not already asked"
    if not candidates:
        candidates = [i for i, t in enumerate(texts) if _norm(t) not in asked]
        if not candidates:
            return {"top_4": [], "top_15": []}

    # 5) rank (deterministic shuffle if low signal)
    subset_scores = np.array([float(scores[i]) for i in candidates], dtype=np.float32)
    low_signal = (subset_scores.size == 0) or np.allclose(subset_scores, subset_scores[0]) or not convo_tail_text.strip()
    if low_signal:
        ranked = _stable_shuffle(candidates, f"{body.session_id}|{convo_tail_text[:128]}")
    else:
        ranked = sorted(candidates, key=lambda i: float(scores[i]), reverse=True)

    top15 = [texts[i] for i in ranked[:15]]
    top4  = top15[:4]

    # 6) persist last-4 for reload (best-effort, no history writes here)
    try:
        db_set_last4(body.session_id, top4, user_token)
    except Exception as e:
        log.warning(f"Persist last-4 failed: {e}")

    return {"top_4": top4, "top_15": top15}
