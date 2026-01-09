# graphdb_connector.py

from gqlalchemy import Memgraph
from app.config import muse_config
from app.core.utils import write_system_log

host = muse_config.get("GRAPHDB_HOST")
port = muse_config.get("GRAPHDB_PORT")

class GraphDBConnector:
    def __init__(self, host=host, port=port):
        self.host = host
        self.port = port
        self.mg = None
        self._connect()

    def _connect(self):
        try:
            self.mg = Memgraph(self.host, self.port)
            # Light ping to confirm connectivity
            self.mg.execute("RETURN 1;")
            write_system_log(
                level="debug", module="databases", component="graphdb",
                function="_connect", action="connect", host=self.host, port=self.port
            )
        except Exception as e:
            write_system_log(
                level="error", module="databases", component="graphdb",
                function="_connect", action="connect_error",
                host=self.host, port=self.port, error=str(e)
            )
            self.mg = None

    def run_cypher(self, query, params=None):
        if not self.mg:
            write_system_log(
                level="error", module="databases", component="graphdb",
                function="run_cypher", action="no_connection",
                query=query, params=params
            )
            return []
        try:
            return list(self.mg.execute_and_fetch(query, params or {}))
        except Exception as e:
            write_system_log(
                level="error", module="databases", component="graphdb",
                function="run_cypher", action="query_error",
                query=query, params=params, error=str(e)
            )
            return []

    # --- New helper methods ---

    def expand_entities(self, entity_names, depth=2):
        """
        Expand outward from any node whose name matches one of the given entity_names.
        Works natively in Memgraph (no APOC dependency).
        Filters out hidden/deleted messages and projects.
        Returns dict with nodes, rels, and message_ids.
        """
        query = """
            MATCH (n)
            WHERE n.name IN $entity_names
            MATCH p = (n)-[*1..$depth]-(m)
            WITH collect(DISTINCT n) + collect(DISTINCT m) AS nodes,
                 collect(DISTINCT relationships(p)) AS rel_lists
            UNWIND rel_lists AS sublist
            UNWIND sublist AS r
            WITH nodes, collect(DISTINCT r) AS rels
            
            // Filter visible messages
            WITH nodes, rels,
                 [m IN nodes
                  WHERE 'Message' IN labels(m)
                    AND coalesce(m.is_hidden,false)=false
                    AND coalesce(m.is_deleted,false)=false
                    AND ALL(pr IN [(m)-[:IN_PROJECT]->(proj:Project) | coalesce(proj.is_hidden,false)] WHERE pr=false)
                 ] AS visible_msgs
            
            UNWIND visible_msgs AS m
            WITH nodes, rels, collect(m.message_id) AS message_ids
            
            // Build rich maps now that the parser’s calm
            WITH
                [nd IN nodes | {
                    name: coalesce(nd.name, ""),
                    canonical_name: coalesce(nd.canonical_name, nd.name, ""),
                    labels: labels(nd),
                    type: coalesce(nd.type, head(labels(nd)), ""),
                    real_name: coalesce(nd.real_name, nd.name, ""),
                    description: coalesce(nd.description, ""),
                    descriptions: coalesce(nd.descriptions, []),
                    is_hidden: coalesce(nd.is_hidden, false),
                    is_deleted: coalesce(nd.is_deleted, false)
                }] AS nodes,
                [r IN rels | {
                    start: startNode(r).name,
                    end: endNode(r).name,
                    type: type(r),
                    description: coalesce(r.description, "")
                }] AS rels,
                message_ids
            
            RETURN nodes, rels, message_ids;
        """
        entity_list = "[" + ",".join(f'"{e}"' for e in entity_names) + "]"
        query = query.replace("$entity_names", entity_list)
        query = query.replace("$depth", str(int(depth)))
        result = self.run_cypher(query)

        if not result:
            return {"nodes": [], "rels": [], "message_ids": []}

        record = result[0]
        return {
            "nodes": record.get("nodes", []),
            "rels": record.get("rels", []),
            "message_ids": record.get("message_ids", [])
        }

    def clear_graph(self):
        """Utility: wipe all nodes and relationships. Use carefully."""
        return self.run_cypher("MATCH (n) DETACH DELETE n;")

    def count_nodes(self):
        """Quick sanity check on graph size."""
        result = self.run_cypher("MATCH (n) RETURN count(n) AS nodes;")
        return result[0]["nodes"] if result else 0


    # --- Example Retrieval Methods ---

    def get_user_by_name(self, name):
        return self.run_cypher(
            "MATCH (u:User {author_name: $name}) RETURN u LIMIT 1;",
            {"name": name}
        )

    def get_recent_messages_by_user(self, name, limit=10):
        return self.run_cypher(
            """
            MATCH (u:User {author_name: $name})-[:SENT]->(m:Message)
            RETURN m ORDER BY m.timestamp DESC LIMIT $limit;
            """,
            {"name": name, "limit": limit}
        )

    def get_facts_by_tag(self, tag, limit=10):
        return self.run_cypher(
            """
            MATCH (f:Fact)-[:TAGGED_AS]->(t:Tag {name: $tag})
            RETURN f LIMIT $limit;
            """,
            {"tag": tag, "limit": limit}
        )

    def get_related_users(self, user_name, limit=10):
        return self.run_cypher(
            """
            MATCH (u:User {author_name: $user_name})--(m:Message)--(other:User)
            WHERE other.author_name <> $user_name
            RETURN DISTINCT other.author_name AS related_user
            LIMIT $limit;
            """,
            {"user_name": user_name, "limit": limit}
        )

    def get_random_facts(self, limit=3):
        return self.run_cypher(
            """
            MATCH (f:Fact)
            WITH f, rand() AS r
            RETURN f ORDER BY r LIMIT $limit;
            """,
            {"limit": limit}
        )

    def get_messages_between_users(self, user1, user2, limit=10):
        return self.run_cypher(
            """
            MATCH (u1:User {author_name: $user1})-[:SENT]->(m:Message)<-[:SENT]-(u2:User {author_name: $user2})
            RETURN m ORDER BY m.timestamp DESC LIMIT $limit;
            """,
            {"user1": user1, "user2": user2, "limit": limit}
        )

    def get_top_tags(self, limit=10):
        return self.run_cypher(
            """
            MATCH (t:Tag)<-[:TAGGED_AS]-()
            RETURN t.name AS tag, count(*) AS count
            ORDER BY count DESC
            LIMIT $limit;
            """,
            {"limit": limit}
        )

    def get_node_counts(self):
        return self.run_cypher(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total ORDER BY total DESC;"
        )

    def get_total_relationships(self):
        return self.run_cypher(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS total ORDER BY total DESC;"
        )

    # --- Utility for ad hoc Cypher ---
    def query(self, cypher, params=None):
        return self.run_cypher(cypher, params)

    # --- Reconnect in case of connection loss ---
    def reconnect(self):
        self._connect()

# Helper functions
def create_tag(mg, tag):
    mg.execute("""
        MERGE (t:Tag {name: $tag})
    """, {"tag": tag})

def create_user(mg, user_id, name, source=None):
    mg.execute("""
        MERGE (u:User {user_id: $user_id})
        SET u.name = $name
        SET u.source = $source
    """, {"user_id": user_id, "name": name, "source": source})

def create_fact(mg, fact):
    mg.execute("""
        MERGE (f:Fact {fact_id: $fact_id})
        SET f.text = $text,
            f.type = $type,
            f.tags = $tags,
            f.created_at = $created_at,
            f.source = $source
    """, {
        "fact_id": str(fact["_id"]),
        "text": fact.get("text", ""),
        "type": fact.get("type", ""),
        "tags": fact.get("tags", []),
        "created_at": fact.get("created_at") or fact.get("timestamp"),
        "source": fact.get("source", None),
    })
    for tag in fact.get("tags", []):
        create_tag(mg, tag)
        mg.execute("""
            MATCH (f:Fact {fact_id: $fact_id}), (t:Tag {name: $tag})
            MERGE (f)-[:TAGGED_AS]->(t)
        """, {"fact_id": str(fact["_id"]), "tag": tag})

def create_message_and_user(mg, msg, user_key="author_id", user_name_key="author_name"):
    msg_id = msg.get("_id", None) or msg.get("msg_id", None) or msg.get("timestamp", None)
    role = msg.get("role", "")
    text = msg.get("message", "")
    source = msg.get("source", "")
    timestamp = msg.get("timestamp", "")
    meta = msg.get("metadata", {})
    auto_tags = msg.get("auto_tags")
    if not isinstance(auto_tags, list):
        auto_tags = []
    user_tags = msg.get("user_tags")
    if not isinstance(user_tags, list):
        user_tags = []

    # User node from metadata (Discord/web)
    author_id = meta.get(user_key, "unknown")
    author_name = meta.get(user_name_key, "unknown")
    channel = meta.get("channel", None)
    server = meta.get("server", None)

    create_user(mg, author_id, author_name, source)

    mg.execute("""
        MERGE (m:Message {msg_id: $msg_id})
        SET m.text = $text,
            m.role = $role,
            m.source = $source,
            m.timestamp = $timestamp,
            m.channel = $channel,
            m.server = $server
    """, {
        "msg_id": str(msg_id),
        "text": text,
        "role": role,
        "source": source,
        "timestamp": timestamp,
        "channel": channel,
        "server": server,
    })

    mg.execute("""
        MATCH (u:User {user_id: $user_id}), (m:Message {msg_id: $msg_id})
        MERGE (u)-[:SENT]->(m)
    """, {"user_id": author_id, "msg_id": str(msg_id)})

    # --- Handle auto_tags and user_tags ---
    for tag in auto_tags:
        create_tag(mg, tag)
        mg.execute("""
            MATCH (m:Message {msg_id: $msg_id}), (t:Tag {name: $tag})
            MERGE (m)-[:TAGGED_AS_AUTO]->(t)
        """, {"msg_id": str(msg_id), "tag": tag})

    for tag in user_tags:
        create_tag(mg, tag)
        mg.execute("""
            MATCH (m:Message {msg_id: $msg_id}), (t:Tag {name: $tag})
            MERGE (m)-[:TAGGED_AS_USER]->(t)
        """, {"msg_id": str(msg_id), "tag": tag})


def delete_fact_by_id(mg, fact_id):
    mg.execute(
        "MATCH (f:Fact {fact_id: $fact_id}) DETACH DELETE f",
        {"fact_id": str(fact_id)}
    )

# --- Initialization Helper ---

import logging

def get_graphdb_connector():
    host = muse_config.get("GRAPHDB_HOST")
    port = muse_config.get("GRAPHDB_PORT")
    return GraphDBConnector(host=host, port=port)
