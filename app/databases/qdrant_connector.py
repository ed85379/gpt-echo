from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client import models as rest
from sentence_transformers import SentenceTransformer
import uuid, bson
from app.config import muse_config

QDRANT_HOST = muse_config.get("QDRANT_HOST")
QDRANT_PORT = muse_config.get("QDRANT_PORT")
BATCH_SIZE = 128  # or 256 if the entries are tiny
model = SentenceTransformer(muse_config.get("SENTENCE_TRANSFORMER_MODEL"))

# Qdrant client connection
qdrant = QdrantClient(
    host=QDRANT_HOST,  # Replace with actual host if remote
    port=int(QDRANT_PORT)
)

QDRANT_COLLECTION = "muse_memory"

def get_qdrant_client():
    return qdrant

def query(collection_name, search_query, limit=10, query_filter=None, with_payload=True, with_vectors=False):
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=collection_name,
        query=model.encode([search_query])[0],
        limit=limit,
        query_filter=query_filter,
        with_payload=with_payload,
        with_vectors=with_vectors
    )
    return response.points

## This function is for embedding the journal into its own collection
def upsert_embedding(vector, metadata, collection, point_id=None):
    from qdrant_client.http.models import PointStruct
    from uuid import uuid4
    point_id = point_id or str(uuid.uuid4())
    point = PointStruct(
        id=point_id,
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

def safe_str(val):
    if isinstance(val, bson.ObjectId):
        return str(val)
    return val

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
        "is_deleted": entry.get("is_deleted", False),
        "project_id": safe_str(entry.get("project_id")),
        "remembered": entry.get("remembered", False)
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

# This method does not appear to be in use. Clean up.
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
            "user_tags": entry.get("user_tags", []),
            "is_private": entry.get("is_private", False),
            "is_deleted": entry.get("is_deleted", False),
            "project_id": safe_str(entry.get("project_id")),
            "remembered": entry.get("remembered", False)
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

def delete_point(point_id_str: str, collection_name: str):
    point_id = message_id_to_uuid(point_id_str)
    qdrant.delete(
        collection_name=collection_name,
        points_selector=qmodels.PointIdsList(
            points=[point_id]
        )
    )
