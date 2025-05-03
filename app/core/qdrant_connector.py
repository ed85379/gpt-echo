from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
import numpy as np
import uuid
from app import config

QDRANT_HOST = config.get_setting("system_settings.QDRANT_HOST", "localhost")
QDRANT_PORT = config.get_setting("system_settings.QDRANT_PORT", "6333")
BATCH_SIZE = 128  # or 256 if the entries are tiny

# Qdrant client connection
qdrant = QdrantClient(
    host=QDRANT_HOST,  # Replace with actual host if remote
    port=int(QDRANT_PORT)
)

QDRANT_COLLECTION = "echo_memory"

def ensure_qdrant_collection(vector_size):
    if QDRANT_COLLECTION not in [c.name for c in qdrant.get_collections().collections]:
        qdrant.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE)
        )

def index_to_qdrant(entries, vectors, batch_size=128):
    ensure_qdrant_collection(vectors.shape[1])
    points = []

    for entry, vector in zip(entries, vectors):
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector.tolist(),
                payload={
                    "timestamp": entry.get("timestamp"),
                    "role": entry.get("role"),
                    "source": entry.get("source"),
                    "message": entry.get("message"),
                }
            )
        )

    # Upload in batches
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=batch)
