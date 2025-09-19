from sentence_transformers import SentenceTransformer
import numpy as np
import os

# ---- Model / encoder ------------------------------------------------------
MODEL = SentenceTransformer("all-MiniLM-L6-v2")
USED_SIM_THRESHOLD = float(os.getenv("SUGGEST_USED_SIM_THRESHOLD", "0.93"))

def l2norm(x: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(x, axis=-1, keepdims=True)
    denom = np.clip(denom, 1e-9, None)
    return x / denom
