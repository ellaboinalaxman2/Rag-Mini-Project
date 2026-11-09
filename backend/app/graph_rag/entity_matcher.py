from app.graph_rag.normalizer import normalize_name
from app.graph_rag.neo4j_store import driver


def _run_query(cypher: str, **params):
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


def match_entities_by_keywords(keywords: list[str], max_results: int = 10):
    """
    Match Entity nodes whose normalized_name contains any of the keywords.
    Case-insensitive substring match.
    """
    if not keywords:
        return []

    normalized = [normalize_name(k) for k in keywords if k and k.strip()]
    normalized = [n for n in normalized if n]

    if not normalized:
        return []

    cypher = """
    MATCH (e:Entity)
    WHERE any(kw IN $keywords WHERE e.normalized_name CONTAINS kw)
    RETURN e.id AS id, e.name AS name, e.type AS type,
           e.normalized_name AS normalized_name,
           e.description AS description
    LIMIT $limit
    """
    return _run_query(cypher, keywords=normalized, limit=max_results)


def get_entity_by_id(entity_id: str):
    cypher = """
    MATCH (e:Entity {id: $entity_id})
    RETURN e.id AS id, e.name AS name, e.type AS type,
           e.normalized_name AS normalized_name,
           e.description AS description
    """
    rows = _run_query(cypher, entity_id=entity_id)
    return rows[0] if rows else None