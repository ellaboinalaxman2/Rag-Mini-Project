from app.graph_rag.query_processor import (
    preprocess_query,
    extract_keywords,
    extract_candidate_phrases,
)
from app.graph_rag.entity_matcher import (
    match_entities_by_keywords,
    get_entity_by_id,
)
from app.graph_rag.neo4j_store import driver

MAX_TRAVERSAL_DEPTH = 2
MAX_RELATIONSHIPS = 50
MAX_ENTITIES = 20


def _run_query(cypher: str, **params):
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


def _traverse_one_hop(entity_ids: list[str], document_id: str | None = None):
    if not entity_ids:
        return [], []

    cypher = """
    MATCH (s:Entity)-[r:RELATES_TO]-(t:Entity)
    WHERE s.id IN $entity_ids
      AND ($document_id IS NULL OR r.document_id = $document_id)
    RETURN s.id AS source_id, s.name AS source_name, s.type AS source_type,
           t.id AS target_id, t.name AS target_name, t.type AS target_type,
           r.relation_type AS relation_type,
           r.evidence AS evidence,
           r.document_id AS document_id,
           r.chunk_id AS chunk_id
    LIMIT $limit
    """
    rows = _run_query(
        cypher,
        entity_ids=entity_ids,
        document_id=document_id,
        limit=MAX_RELATIONSHIPS,
    )

    relationships = []
    new_entity_ids = set()

    for row in rows:
        relationships.append(
            {
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "source_type": row["source_type"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "target_type": row["target_type"],
                "relation_type": row["relation_type"],
                "evidence": row.get("evidence") or "",
                "document_id": row.get("document_id"),
                "chunk_id": row.get("chunk_id"),
                "depth": 1,
            }
        )
        new_entity_ids.add(row["source_id"])
        new_entity_ids.add(row["target_id"])

    return relationships, list(new_entity_ids)


def _traverse_multi_hop(
    entity_ids: list[str],
    depth: int = 2,
    document_id: str | None = None,
):
    if not entity_ids:
        return [], []

    depth = max(1, min(depth, MAX_TRAVERSAL_DEPTH))

    cypher = f"""
    MATCH path = (s:Entity)-[:RELATES_TO*1..{depth}]-(t:Entity)
    WHERE s.id IN $entity_ids
      AND ALL(rel IN relationships(path)
              WHERE $document_id IS NULL OR rel.document_id = $document_id)
    UNWIND relationships(path) AS r
    RETURN DISTINCT
        startNode(r).id AS source_id,
        startNode(r).name AS source_name,
        startNode(r).type AS source_type,
        endNode(r).id AS target_id,
        endNode(r).name AS target_name,
        endNode(r).type AS target_type,
        r.relation_type AS relation_type,
        r.evidence AS evidence,
        r.document_id AS document_id,
        r.chunk_id AS chunk_id
    LIMIT $limit
    """
    rows = _run_query(
        cypher,
        entity_ids=entity_ids,
        document_id=document_id,
        limit=MAX_RELATIONSHIPS,
    )

    relationships = []
    new_entity_ids = set()

    for row in rows:
        relationships.append(
            {
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "source_type": row["source_type"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "target_type": row["target_type"],
                "relation_type": row["relation_type"],
                "evidence": row.get("evidence") or "",
                "document_id": row.get("document_id"),
                "chunk_id": row.get("chunk_id"),
                "depth": depth,
            }
        )
        new_entity_ids.add(row["source_id"])
        new_entity_ids.add(row["target_id"])

    return relationships, list(new_entity_ids)


def _fetch_mentions(
    entity_ids: list[str], document_id: str | None = None
):
    if not entity_ids:
        return []

    cypher = """
    MATCH (e:Entity)-[m:MENTIONED_IN]->(d:Document)
    WHERE e.id IN $entity_ids
      AND ($document_id IS NULL OR d.id = $document_id)
    RETURN DISTINCT
        e.id AS entity_id,
        e.name AS entity_name,
        m.chunk_id AS chunk_id,
        d.id AS document_id,
        d.filename AS filename
    LIMIT $limit
    """
    return _run_query(
        cypher,
        entity_ids=entity_ids,
        document_id=document_id,
        limit=MAX_ENTITIES * 5,
    )


def retrieve_graph_evidence(
    query: str, depth: int = 2, document_id: str | None = None
):
    """
    Full Graph RAG retrieval pipeline:
      1. Preprocess query
      2. Extract keywords / candidate phrases
      3. Match entities in Neo4j
      4. 1-hop + multi-hop traversal
      5. Fetch document provenance
      6. Deduplicate and return structured evidence
    """
    query = preprocess_query(query)
    if depth < 1 or depth > MAX_TRAVERSAL_DEPTH:
        depth = min(max(depth, 1), MAX_TRAVERSAL_DEPTH)

    candidate_phrases = extract_candidate_phrases(query)
    keywords = extract_keywords(query)

    matched_entities = match_entities_by_keywords(
        candidate_phrases + keywords, max_results=MAX_ENTITIES
    )

    if document_id and matched_entities:
        seed_mentions = _fetch_mentions(
            [entity["id"] for entity in matched_entities], document_id
        )
        document_entity_ids = {
            mention["entity_id"] for mention in seed_mentions
        }
        matched_entities = [
            entity
            for entity in matched_entities
            if entity["id"] in document_entity_ids
        ]

    if not matched_entities:
        return {
            "query": query,
            "keywords": keywords,
            "matched_entities": [],
            "relationships": [],
            "mentions": [],
            "traversal_depth": depth,
        }

    seed_ids = [e["id"] for e in matched_entities]

    # 1-hop traversal
    one_hop_rels, one_hop_ids = _traverse_one_hop(seed_ids, document_id)

    # Multi-hop (only if requested depth > 1)
    multi_hop_rels = []
    multi_hop_ids = []
    if depth > 1:
        multi_hop_rels, multi_hop_ids = _traverse_multi_hop(
            seed_ids, depth=depth, document_id=document_id
        )

    # Deduplicate relationships by (source_id, target_id, relation_type, chunk_id)
    seen = set()
    all_relationships = []
    for rel in one_hop_rels + multi_hop_rels:
        key = (
            rel["source_id"],
            rel["target_id"],
            rel["relation_type"],
            rel.get("chunk_id") or "",
        )
        if key in seen:
            continue
        seen.add(key)
        all_relationships.append(rel)

    all_entity_ids = set(seed_ids) | set(one_hop_ids) | set(multi_hop_ids)

    mentions = _fetch_mentions(list(all_entity_ids), document_id)

    return {
        "query": query,
        "keywords": keywords,
        "matched_entities": matched_entities,
        "relationships": all_relationships,
        "mentions": mentions,
        "traversal_depth": depth,
    }


def get_entity_details(entity_id: str):
    entity = get_entity_by_id(entity_id)
    if not entity:
        return None

    # 1-hop neighbors
    neighbors_cypher = """
    MATCH (e:Entity {id: $entity_id})-[r:RELATES_TO]-(n:Entity)
    RETURN n.id AS id, n.name AS name, n.type AS type,
           r.relation_type AS relation_type,
           r.evidence AS evidence,
           r.document_id AS document_id,
           r.chunk_id AS chunk_id
    LIMIT 100
    """
    neighbors = _run_query(neighbors_cypher, entity_id=entity_id)

    # Source documents
    docs_cypher = """
    MATCH (e:Entity {id: $entity_id})-[m:MENTIONED_IN]->(d:Document)
    RETURN DISTINCT d.id AS document_id, d.filename AS filename,
           m.chunk_id AS chunk_id
    LIMIT 50
    """
    sources = _run_query(docs_cypher, entity_id=entity_id)

    return {
        "entity": entity,
        "neighbors": neighbors,
        "sources": sources,
    }