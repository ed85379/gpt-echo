
import json
from sentence_transformers import SentenceTransformer
from app import config
from app.databases import qdrant_connector
from app.core import utils

# ----------------------
# Config & Constants
# ----------------------

USE_QDRANT = config.USE_QDRANT

PROJECT_ROOT = config.PROJECT_ROOT
JOURNAL_DIR = config.JOURNAL_DIR
JOURNAL_CATALOG_PATH = config.JOURNAL_CATALOG_PATH
ENABLE_PRIVATE_JOURNAL = config.ENABLE_PRIVATE_JOURNAL
USER_TIMEZONE = config.USER_TIMEZONE
MODEL = SentenceTransformer(config.SENTENCE_TRANSFORMER_MODEL)


# ----------------------
# Qdrant Search Helper
# ----------------------

def search_journal(query_vector, top_k=5):
    client = qdrant_connector.get_qdrant_client()
    results = client.search(
        collection_name="echo_journal",
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )
    return results


# ----------------------
# Utilities
# ----------------------



def ensure_journal_dir():
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

def load_journal_catalog():
    if not JOURNAL_CATALOG_PATH.exists():
        return []
    with open(JOURNAL_CATALOG_PATH, "r") as f:
        return json.load(f)

def save_journal_catalog(entries):
    with open(JOURNAL_CATALOG_PATH, "w") as f:
        json.dump(entries, f, indent=2)



# ----------------------
# Search Function
# ----------------------

def search_indexed_journal(query, top_k=5, include_private=False, use_qdrant=USE_QDRANT):
    query_vector = MODEL.encode(query).tolist()
    results = []

    if use_qdrant:
        qdrant_results = search_journal(query_vector, top_k=top_k)

        for item in qdrant_results:
            payload = item.payload or {}
            if not include_private and payload.get("entry_type") == "private":
                continue
            results.append({
                "entry_id": payload.get("entry_id"),
                "paragraph_index": payload.get("paragraph_index"),
                "text": payload.get("text", ""),
                "mood": payload.get("mood"),
                "tags": payload.get("tags"),
                "score": item.score,
                "entry_type": payload.get("entry_type"),
                "timestamp": payload.get("timestamp")
            })


    else:
        # FAISS fallback
        import faiss
        import numpy as np

        index_path = JOURNAL_DIR / "journal.index"
        id_map_path = JOURNAL_DIR / "journal_id_map.json"

        if not index_path.exists() or not id_map_path.exists():
            return []

        index = faiss.read_index(str(index_path))
        with open(id_map_path, "r") as f:
            id_map = json.load(f)

        query_np = np.array([query_vector], dtype="float32")
        scores, indices = index.search(query_np, top_k)

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            payload = id_map[str(idx)]
            if not include_private and payload.get("entry_type") == "private":
                continue
            results.append({
                "entry_id": payload.get("entry_id"),
                "paragraph_index": payload.get("paragraph_index"),
                "text": payload.get("text", ""),
                "mood": payload.get("mood"),
                "tags": payload.get("tags"),
                "score": float(score),
                "entry_type": payload.get("entry_type"),
                "timestamp": payload.get("timestamp")
            })

    return results


# ----------------------
# Core Function
# ----------------------

def create_journal_entry(title, body, mood="reflective", tags=None, entry_type="public", source="manual", use_qdrant=USE_QDRANT):
    ensure_journal_dir()
    now = utils.get_formatted_datetime()
    slug = utils.slugify(title)
    filename = f"{now.replace(':', '-').replace('.', '-')}_{slug}.md"
    filepath = JOURNAL_DIR / filename

    if tags is None:
        tags = []

    encrypted = False
    encrypted_body = body
    if entry_type == "private":
        if not ENABLE_PRIVATE_JOURNAL:
            raise Exception("Private journal entries are disabled in config.")
        encrypted_body = utils.encrypt_text(body)
        encrypted = True

    with open(filepath, "w") as f:
        f.write(encrypted_body)

    # Basic summary: first non-empty line
    summary_line = next((line.strip() for line in body.splitlines() if line.strip()), "")

    catalog = load_journal_catalog()
    catalog.append({
        "title": title,
        "mood": mood,
        "tags": tags,
        "source": source,
        "datetime": now,
        "date": now.split("T")[0],
        "filename": filename,
        "entry_type": entry_type,
        "encrypted": encrypted,
        "summary": summary_line
    })
    save_journal_catalog(catalog)

    # Chunk, embed, index (private and public both included)
    paragraphs = [p for p in body.split("\n\n") if p.strip()]
    import faiss
    import numpy as np

    faiss_index_path = JOURNAL_DIR / "journal.index"
    id_map_path = JOURNAL_DIR / "journal_id_map.json"

    if faiss_index_path.exists() and id_map_path.exists():
        index = faiss.read_index(str(faiss_index_path))
        with open(id_map_path, "r") as f:
            id_map = json.load(f)
    else:
        index = faiss.IndexFlatL2(384)  # Assuming MiniLM output dimension is 384
        id_map = {}

    next_id = int(max(map(int, id_map.keys()), default=-1)) + 1

    for i, paragraph in enumerate(paragraphs):
        vector = MODEL.encode(paragraph).tolist()
        metadata = {
            "entry_id": filename,
            "paragraph_index": i,
            "entry_type": entry_type,
            "mood": mood,
            "tags": tags,
            "source": source,
            "timestamp": now,
            "text": paragraph
        }
        # Qdrant
        if use_qdrant:
            qdrant_connector.upsert_embedding(
                vector=vector,
                metadata=metadata,
                collection="echo_journal"
            )
        # FAISS
        index.add(np.array([vector], dtype="float32"))
        id_map[str(next_id)] = metadata
        next_id += 1

    faiss.write_index(index, str(faiss_index_path))
    with open(id_map_path, "w") as f:
        json.dump(id_map, f, indent=2)
