from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
from typing import Any
from bson import ObjectId
from app.databases.mongo_connector import mongo, mongo_system
from app.config import muse_config
from app.api.queues import index_queue, log_queue


router = APIRouter(prefix="/api/messages", tags=["messages"])


MONGO_CONVERSATION_COLLECTION = muse_config.get("MONGO_CONVERSATION_COLLECTION")

@router.get("/")
def get_messages(
        limit: int = Query(10, le=50),
        before: Optional[str] = None,
        after: Optional[str] = None,
        sources: Optional[List[str]] = Query(None),
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = Query(None)
):
    query: dict = {}

    # Timestamp filtering
    if before:
        dt = parse(before)
        dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        query["timestamp"] = {"$lt": dt}
    if after:
        dt = parse(after)
        dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        if "timestamp" in query:
            query["timestamp"]["$gt"] = dt
        else:
            query["timestamp"] = {"$gt": dt}

    if sources:
        query["source"] = {"$in": sources}
    if project_id:
        try:
            query["project_id"] = ObjectId(project_id)
        except Exception:
            # Invalid ObjectId string—fail gracefully, or skip filter
            pass
    if tags:
        query["user_tags"] = {"$in": tags}

    # 🔹 Apply time_skip band if active
    state_doc = mongo_system.find_one_document(
        "muse_states",
        {"type": "states"},
        {"time_skip": 1, "_id": 0},
    ) or {}

    time_skip = state_doc.get("time_skip") or {}
    if time_skip.get("active"):
        start_ts = time_skip.get("start", {}).get("timestamp")
        end_ts = time_skip.get("end", {}).get("timestamp")

        if start_ts and end_ts:
            # Make sure they’re timezone-aware datetimes
            if isinstance(start_ts, str):
                start_ts = parse(start_ts)
            if isinstance(end_ts, str):
                end_ts = parse(end_ts)

            if start_ts.tzinfo is None:
                start_ts = start_ts.replace(tzinfo=timezone.utc)
            if end_ts.tzinfo is None:
                end_ts = end_ts.replace(tzinfo=timezone.utc)

            # Exclude the seam band: timestamp < start_ts OR timestamp > end_ts
            # Using $or so it composes with existing filters
            band_filter = {
                "$or": [
                    {"timestamp": {"$lte": start_ts}},
                    {"timestamp": {"$gte": end_ts}},
                ]
            }

            if query:
                query = {"$and": [query, band_filter]}
            else:
                query = band_filter

    logs = mongo.find_logs(
        collection_name=MONGO_CONVERSATION_COLLECTION,
        query=query,
        limit=limit,
        sort_field="timestamp",
        ascending=False,
    )

    print(f"Getting messages: {query} — found {len(logs)}")

    result = []
    for msg in logs:
        mapped = {
            "from": msg.get("from") or msg.get("role") or "iris",
            "text": msg.get("message") or "",
            "timestamp": msg["timestamp"].isoformat() + "Z"
            if isinstance(msg["timestamp"], datetime)
            else str(msg["timestamp"]),
            "_id": str(msg["_id"]),
            "message_id": msg.get("message_id") or "",
            "source": msg.get("source", ""),
            "user_tags": msg.get("user_tags", []),
            "is_private": msg.get("is_private", False),
            "is_hidden": msg.get("is_hidden", False),
            "remembered": msg.get("remembered", False),
            "is_deleted": msg.get("is_deleted", False),
            "project_id": str(msg["project_id"]) if msg.get("project_id") else None,
            "flags": msg.get("flags", []),
            "metadata": msg.get("metadata", {}),
        }
        result.append(mapped)

    return {"messages": result[::-1]}

@router.post("/log")
async def log_message_endpoint(payload: dict = Body(...)):
    # Validate message fields if needed
    try:
        await log_queue.put(payload)
        return {"status": "queued"}
    except Exception as e:
        import traceback
        print("Logging error in /api/messages/log:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag")
async def tag_message(
    message_ids: List[str] = Body(...),
    add_user_tags: Optional[List[str]] = Body(None),
    remove_user_tags: Optional[List[str]] = Body(None),
    is_private: Optional[bool] = Body(None),
    is_hidden: Optional[bool] = Body(None),
    remembered: Optional[bool] = Body(None),
    is_deleted: Optional[bool] = Body(None),
    set_project: Optional[Any] = Body(None),
    exported: Optional[bool] = Body(None)
):
    print(message_ids)
    print(set_project)
    mongo_update = {}
    contentful = False

    # Handle user_tags (contentful)
    if add_user_tags:
        mongo_update.setdefault("$addToSet", {})["user_tags"] = {"$each": add_user_tags}
        contentful = True
    if remove_user_tags:
        mongo_update.setdefault("$pullAll", {})["user_tags"] = remove_user_tags
        contentful = True

    set_fields = {}
    unset_fields = []

    # Handle is_private, is_hidden, remembered, is_deleted (contentful)
    if is_private is not None:
        contentful = True
        if is_private:
            set_fields["is_private"] = True
        else:
            unset_fields.append("is_private")
    if is_hidden is not None:
        contentful = True
        if is_hidden:
            set_fields["is_hidden"] = True
        else:
            unset_fields.append("is_hidden")
    if remembered is not None:
        contentful = True
        if remembered:
            set_fields["remembered"] = True
        else:
            unset_fields.append("remembered")
    if is_deleted is not None:
        contentful = True
        if is_deleted:
            set_fields["is_deleted"] = True
        else:
            unset_fields.append("is_deleted")

    # --- PROJECT LOGIC ---
    if set_project is not None:
        contentful = True
        if set_project:
            # Coerce to ObjectId if it's a string and not already one
            if not isinstance(set_project, ObjectId):
                try:
                    set_fields["project_id"] = ObjectId(set_project)
                except Exception:
                    # If set_project isn't a valid ObjectId, handle gracefully
                    return {"updated": 0, "detail": f"Invalid project_id: {set_project}"}
            else:
                set_fields["project_id"] = set_project
        else:
            unset_fields.append("project_id")

    # Handle exported
    if exported is not None:
        if exported:
            set_fields["exported_on"] = datetime.now(timezone.utc)
        else:
            unset_fields.append("exported_on")

    # Only set updated_on for "contentful" changes
    if contentful:
        set_fields["updated_on"] = datetime.now(timezone.utc)

    if set_fields:
        mongo_update["$set"] = set_fields
    if unset_fields:
        mongo_update["$unset"] = {f: "" for f in unset_fields}

    if not mongo_update:
        return {"updated": 0, "detail": "No actions specified."}

    result = mongo.db.muse_conversations.update_many(
        {"message_id": {"$in": message_ids}},
        mongo_update
    )
    for message_id in message_ids:
        await index_queue.put(message_id)
    return {"updated": result.modified_count}

@router.get("/user_tags")
def get_user_tags(
    limit: int = Query(100, description="Maximum number of tags to return")
):
    # Use MongoDB aggregation to get unique user tags with counts
    pipeline = [
        {"$unwind": "$user_tags"},
        {"$group": {"_id": "$user_tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": limit}
    ]
    tag_docs = list(mongo.db.muse_conversations.aggregate(pipeline))
    return {"tags": [{"tag": doc["_id"], "count": doc["count"]} for doc in tag_docs]}

@router.get("/calendar_status")
def get_calendar_status(
    days: int = Query(30, ge=1, le=366),
    source: str = Query(None, description="Optional source filter (Frontend, ChatGPT)")
):
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    match_filter = {
        "timestamp": {"$gte": start_date}
    }
    if source:
        # Always treat source as case-insensitive for safety
        match_filter["source"] = source.lower()
    else:
        # If not specified, keep original behavior: ignore chatgpt
        match_filter["source"] = {"$ne": "chatgpt"}
    pipeline = [
        {"$match": match_filter},
        {"$project": {
            "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "exported": {"$cond": [{"$ifNull": ["$exported_on", False]}, 1, 0]}
        }},
        {"$group": {
            "_id": "$day",
            "total": {"$sum": 1},
            "exported": {"$sum": "$exported"}
        }},
        { "$sort": { "_id": 1 } }
    ]
    stats = {doc["_id"]: {"total": doc["total"], "exported": doc["exported"]} for doc in mongo.db.muse_conversations.aggregate(pipeline)}
    return {"days": stats}

@router.get("/calendar_status_simple")
def get_calendar_status_simple(
    start: str = Query(...),   # "YYYY-MM-DD"
    end: str = Query(...),     # "YYYY-MM-DD"
    source: str = Query(None),
    tag: List[str] = Query(None),
    project_id: Optional[str] = None
):
    # Parse input strings as datetimes in UTC
    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    # Add one day to make the range inclusive
    end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    match_filter = {
        "timestamp": {"$gte": start_dt, "$lt": end_dt}
    }
    if source:
        match_filter["source"] = source.lower()
    else:
        match_filter["source"] = {"$ne": "chatgpt"}
    if tag:
        match_filter["user_tags"] = {"$in": tag}
    if project_id:
        try:
            match_filter["project_id"] = ObjectId(project_id)
        except Exception:
            # Invalid ObjectId string—fail gracefully, or skip filter
            pass
    # Now use aggregation to group by day using timestamp
    pipeline = [
        {"$match": match_filter},
        {"$group": {
            "_id": { "$dateToString": { "format": "%Y-%m-%d", "date": "$timestamp" } },
            "any": { "$first": "$_id" }
        }},
        {"$sort": { "_id": 1 }}
    ]
    days = {doc["_id"]: True for doc in mongo.db.muse_conversations.aggregate(pipeline)}
    return {"days": days}

@router.get("/by_day")
def get_messages_by_day(
    date: str = Query(..., description="YYYY-MM-DD"),
    source: str = Query(None, description="Optional source filter (Frontend, ChatGPT, Discord)"),
    project_id: Optional[str] = None
):
    # Parse to start/end of day (UTC)
    dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt_next = dt + timedelta(days=1)

    # Build query
    query = {
        "timestamp": {"$gte": dt, "$lt": dt_next}
    }
    if source:
        query["source"] = source.lower()
    else:
        query["source"] = {"$eq": "frontend"}
    if project_id:
        try:
            query["project_id"] = ObjectId(project_id)
        except Exception:
            # Invalid ObjectId string—fail gracefully, or skip filter
            pass

    logs = mongo.find_logs(
        collection_name=MONGO_CONVERSATION_COLLECTION,
        query=query,
        sort_field="timestamp",
        ascending=True,
        limit=1000  # Increase if needed
    )

    return {"messages": [
        {
            "_id": str(msg["_id"]),
            "from": msg.get("role"),
            "text": msg.get("message"),
            "timestamp": msg["timestamp"].isoformat() + "Z"
                if isinstance(msg["timestamp"], datetime) else str(msg["timestamp"]),
            "exported_on": msg.get("exported_on"),
            "username": (
                msg.get("metadata", {}).get("author_display_name")
                or msg.get("metadata", {}).get("author_name")
                or None
            ),
            "user_tags": msg.get("user_tags", []),
            "message_id": msg.get("message_id") or "",
            "source": msg.get("source", ""),
            "is_private": msg.get("is_private", False),
            "is_hidden": msg.get("is_hidden", False),
            "remembered": msg.get("remembered", False),
            "is_deleted": msg.get("is_deleted", False),
            "project_id": str(msg["project_id"]) if msg.get("project_id") else None,
            "flags": msg.get("flags", []),
            "metadata": msg.get("metadata", {}),
            # Add any other custom fields you need for the UI
        }
        for msg in logs
    ]}