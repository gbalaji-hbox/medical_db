import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------
# Filesystem paths
# ---------------------------
# Resolve project root (directory containing src/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Individual file locations
DISEASE_CSV = os.path.join(BASE_DIR, "src", "CIM", "disease", "api_prescriptioncauselist_202603101243.csv")
HBOX_XLSX = os.path.join(BASE_DIR, "src", "CIM", "Hbox list 3 9 26.xlsx")
MAPPINGS_DIR = os.path.join(BASE_DIR, "src", "CIM", "mappings")
LLM_MAPPING_CSV = os.path.join(MAPPINGS_DIR, "problem_list_llm_mapping.csv")
BACKUP_DIR = MAPPINGS_DIR
EMBED_DB = os.path.join(MAPPINGS_DIR, "disease_vectors.db")
EMBED_TABLE = "disease_embeddings"  # SQLite table name for disease embeddings

# ---------------------------
# Load disease reference data
# ---------------------------
disease_df = pd.read_csv(DISEASE_CSV)
# Verify required columns exist
required_cols = {"cause", "icd_code"}
if not required_cols.issubset(disease_df.columns):
    raise ValueError(f"Disease CSV missing required columns: {required_cols - set(disease_df.columns)}")

# ---------------------------
# SQLite embedding utilities
# ---------------------------
def init_db(conn):
    """Create the embeddings table if it does not exist."""
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {EMBED_TABLE} (
            disease_id TEXT PRIMARY KEY,
            icd_code TEXT,
            weight REAL,
            embedding BLOB
        )
    """)
    conn.commit()

def embed_texts(texts, model):
    """Encode a list of strings into sentence‑transformer embeddings."""
    return model.encode(texts, convert_to_numpy=True)

def store_embeddings(conn, disease_ids, icd_codes, weights, embeddings):
    """Persist disease embeddings into SQLite as BLOBs."""
    cur = conn.cursor()
    for did, icd, w, emb in zip(disease_ids, icd_codes, weights, embeddings):
        cur.execute(f"""
            INSERT OR REPLACE INTO {EMBED_TABLE} (disease_id, icd_code, weight, embedding)
            VALUES (?, ?, ?, ?)
        """, (did, icd, w, emb.tobytes()))
    conn.commit()

def load_embeddings(conn):
    """Retrieve all disease embeddings from SQLite."""
    cur = conn.cursor()
    cur.execute(f"SELECT disease_id, icd_code, weight, embedding FROM {EMBED_TABLE}")
    rows = cur.fetchall()
    disease_ids = [row[0] for row in rows]
    icd_codes = [row[1] for row in rows]
    weights = [row[2] for row in rows]
    embeddings = np.array([np.frombuffer(row[3], dtype=np.float32) for row in rows])
    return disease_ids, icd_codes, np.array(weights), embeddings

def ensure_embeddings(model, conn):
    """Create embeddings if they do not already exist; otherwise load existing ones."""
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {EMBED_TABLE}")
    count = cur.fetchone()[0]
    if count == len(disease_df):
        # Embeddings already present – just load them
        return load_embeddings(conn)
    # Generate embeddings for the disease causes
    disease_texts = disease_df["cause"].astype(str).tolist()
    disease_ids = disease_df["cause"].astype(str).tolist()
    icd_codes = disease_df["icd_code"].astype(str).tolist()
    weights = np.ones(len(disease_df), dtype=np.float32)  # default weight = 1.0
    embeddings = embed_texts(disease_texts, model)
    store_embeddings(conn, disease_ids, icd_codes, weights, embeddings)
    return disease_ids, icd_codes, weights, embeddings# ---------------------------
# Tokenisation helper
# ---------------------------
def tokenize_problem_list(text):
    """Split a problem‑list string into normalized tokens."""
    if pd.isna(text):
        return []
    # Split on common delimiters and strip whitespace
    separators = r'[;,|/\\\n]+'
    return [t.strip() for t in pd.Series(text).str.split(separators).explode().dropna() if t.strip()]

# ---------------------------
# Main processing routine
# ---------------------------
def main():
    # 1️⃣ Load or create disease embeddings
    model = SentenceTransformer("all-MiniLM-L6-v2")
    conn = sqlite3.connect(EMBED_DB)
    init_db(conn)
    disease_ids, icd_codes, weights, disease_emb = ensure_embeddings(model, conn)

    # 2️⃣ Load the HBOX Excel file and extract all unique tokens
    hbox_df = pd.read_excel(HBOX_XLSX, sheet_name='Sheet1', engine='openpyxl')
    if 'Problem List' not in hbox_df.columns:
        raise ValueError("Hbox file does not contain a 'Problem List' column.")
    token_set = set()
    for pl in hbox_df['Problem List']:
        token_set.update(tokenize_problem_list(pl))
    tokens = list(token_set)

    # 3️⃣ Embed the tokens
    token_emb = embed_texts(tokens, model)

    # 4️⃣ Compute cosine similarity (batch)
    # Normalise vectors to unit length
    disease_norm = disease_emb / np.linalg.norm(disease_emb, axis=1, keepdims=True)
    token_norm = token_emb / np.linalg.norm(token_emb, axis=1, keepdims=True)
    sim_matrix = cosine_similarity(token_norm, disease_norm)  # shape: (tokens, diseases)

    # 5️⃣ For each token, pick the top‑2 distinct disease matches
    mapping_rows = []
    for idx, token in enumerate(tokens):
        sims = sim_matrix[idx]  # similarity scores for this token against all diseases
        # Indices of top‑2 scores (descending)
        top_indices = sims.argsort()[::-1][:2]
        primary_idx = top_indices[0]
        secondary_idx = top_indices[1] if len(top_indices) > 1 else None
        primary_disease = disease_ids[primary_idx]
        primary_icd = icd_codes[primary_idx]
        secondary_disease = disease_ids[secondary_idx] if secondary_idx is not None else ""
        secondary_icd = icd_codes[secondary_idx] if secondary_idx is not None else ""

        # Primary mapping row
        mapping_rows.append({
            "token": token,
            "matched_cause": primary_disease,
            "icd_code": primary_icd,
            "method": "ai_vector",
            "notes": f"primary; similarity={sims[primary_idx]:.4f}"
        })
        # Secondary mapping row (if a distinct second match exists)
        if secondary_idx is not None:
            mapping_rows.append({
                "token": token,
                "matched_cause": secondary_disease,
                "icd_code": secondary_icd,
                "method": "ai_vector",
                "notes": f"secondary; similarity={sims[secondary_idx]:.4f}"
            })

    # 6️⃣ Backup any existing mapping file and write the new one
    if os.path.exists(LLM_MAPPING_CSV):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"problem_list_llm_mapping_backup_{ts}.csv")
        os.replace(LLM_MAPPING_CSV, backup_path)

    out_df = pd.DataFrame(mapping_rows)
    out_df.to_csv(LLM_MAPPING_CSV, index=False, encoding="utf-8")

    # 7️⃣ Log the run
    log_path = os.path.join(MAPPINGS_DIR, "problem_list_llm_integration_log.txt")
    with open(log_path, "a", encoding="utf-8") as log_f:
        log_f.write(f"[{datetime.now().isoformat()}] AI vector mapping generated. Tokens processed: {len(tokens)}\n")

if __name__ == "__main__":
    main()