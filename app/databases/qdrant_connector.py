from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
import uuid
from app.config import muse_config

QDRANT_HOST = muse_config.get("QDRANT_HOST")
QDRANT_PORT = muse_config.get("QDRANT_PORT")
BATCH_SIZE = 128  # or 256 if the entries are tiny

# Qdrant client connection
qdrant = QdrantClient(
    host=QDRANT_HOST,  # Replace with actual host if remote
    port=int(QDRANT_PORT)
)

QDRANT_COLLECTION = "muse_memory"

def get_qdrant_client():
    return qdrant


## This function is for embedding the journal into its own collection
def upsert_embedding(vector, metadata, collection):
    from qdrant_client.http.models import PointStruct
    from uuid import uuid4

    point = PointStruct(
        id=str(uuid4()),
        vector=vector,
        payload=metadata
    )
    ensure_qdrant_collection(vector_size=len(vector), collection_name=collection)
    qdrant.upsert(
        collection_name=collection,
        points=[point]
    )

def message_id_to_uuid(msgid):
    # Use a deterministic UUID (namespace + message_id)
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, msgid))

## build_index() calls this for embedding records.
def upsert_single(entry, vector, collection=QDRANT_COLLECTION):
    metadata = entry.get("metadata", {})
    payload = {
        "timestamp": entry.get("timestamp"),
        "role": entry.get("role"),
        "source": entry.get("source"),
        "message": entry.get("message"),
        "message_id": entry.get("message_id"),
        "author_id": metadata.get("author_id"),
        "author_name": metadata.get("author_name"),
        "server": metadata.get("server"),
        "channel": metadata.get("channel"),
        "modality_hint": metadata.get("modality_hint"),
        # Uncomment the next two lines if you want tags included:
        # "auto_tags": entry.get("auto_tags", []),
        "user_tags": entry.get("user_tags", []),
        "is_private": entry.get("is_private", False),
        # "remembered": entry.get("remembered", False)
    }
    ensure_qdrant_collection(vector_size=len(vector), collection_name=collection)
    qdrant.upsert(
        collection_name=collection,
        points=[
            qmodels.PointStruct(
                id = message_id_to_uuid(entry.get("message_id")),
                vector=vector.tolist(),
                payload=payload
            )
        ]
    )


def ensure_qdrant_collection(vector_size, collection_name=None):
    collection_name = collection_name or QDRANT_COLLECTION
    if collection_name not in [c.name for c in qdrant.get_collections().collections]:
        qdrant.recreate_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE)
        )

def index_to_qdrant(entries, vectors, batch_size=128):
    ensure_qdrant_collection(vectors.shape[1])
    points = []

    for entry, vector in zip(entries, vectors):
        metadata = entry.get("metadata", {})
        payload = {
            "timestamp": entry.get("timestamp"),
            "role": entry.get("role"),
            "source": entry.get("source"),
            "message": entry.get("message"),
            # Flatten metadata
            "author_id": metadata.get("author_id"),
            "author_name": metadata.get("author_name"),
            "server": metadata.get("server"),
            "channel": metadata.get("channel"),
            "modality_hint": metadata.get("modality_hint"),
        }

        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector.tolist(),
                payload=payload
            )
        )

    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=batch)

