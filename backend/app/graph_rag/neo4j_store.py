import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD is not configured.")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
)


def verify_connection():
    with driver.session() as session:
        session.run("RETURN 1 AS ok").single()


def initialize_graph():
    verify_connection()

    with driver.session() as session:
        # Constraints for deterministic IDs
        session.run(
            """
            CREATE CONSTRAINT document_id_unique IF NOT EXISTS
            FOR (d:Document) REQUIRE d.id IS UNIQUE
            """
        )
        session.run(
            """
            CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
            FOR (e:Entity) REQUIRE e.id IS UNIQUE
            """
        )
        session.run(
            """
            CREATE CONSTRAINT relationship_id_unique IF NOT EXISTS
            FOR ()-[r:RELATES_TO]-() REQUIRE r.id IS UNIQUE
            """
        )


def clear_document_graph(document_id: str):
    """Delete graph artifacts previously created for this document."""
    with driver.session() as session:
        session.run(
            """
            MATCH (d:Document {id: $document_id})
            OPTIONAL MATCH ()-[r:RELATES_TO]->()
            WHERE r.document_id = $document_id
            DELETE r
            """,
            document_id=document_id,
        )
        session.run(
            """
            MATCH (d:Document {id: $document_id})
            OPTIONAL MATCH (e:Entity)-[m:MENTIONED_IN]->(d)
            DELETE m
            """,
            document_id=document_id,
        )
        session.run(
            """
            MATCH (d:Document {id: $document_id})
            DETACH DELETE d
            """,
            document_id=document_id,
        )


def create_document_node(document_id: str, filename: str, file_type: str):
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Document {id: $document_id})
            SET d.filename = $filename,
                d.file_type = $file_type
            """,
            document_id=document_id,
            filename=filename,
            file_type=file_type,
        )


def create_entity_nodes(entities: list):
    if not entities:
        return

    with driver.session() as session:
        session.run(
            """
            UNWIND $entities AS e
            MERGE (n:Entity {id: e.id})
            SET n.name = coalesce(n.name, e.name),
                n.normalized_name = e.normalized_name,
                n.type = coalesce(n.type, e.type),
                n.description = coalesce(e.description, n.description)
            """,
            entities=entities,
        )


def create_mentions(mentions: list):
    if not mentions:
        return

    with driver.session() as session:
        session.run(
            """
            UNWIND $mentions AS m
            MATCH (e:Entity {id: m.entity_id})
            MATCH (d:Document {id: m.document_id})
            MERGE (e)-[r:MENTIONED_IN {
                chunk_id: m.chunk_id,
                document_id: m.document_id
            }]->(d)
            SET r.evidence = m.evidence
            """,
            mentions=mentions,
        )


def create_relationships(relationships: list):
    if not relationships:
        return

    with driver.session() as session:
        session.run(
            """
            UNWIND $relationships AS rel
            MATCH (s:Entity {id: rel.source_id})
            MATCH (t:Entity {id: rel.target_id})
            MERGE (s)-[r:RELATES_TO {id: rel.id}]->(t)
            SET r.relation_type = rel.relation_type,
                r.evidence = rel.evidence,
                r.document_id = rel.document_id,
                r.chunk_id = rel.chunk_id,
                r.extraction_method = rel.extraction_method
            """,
            relationships=relationships,
        )


def get_graph_statistics():
    with driver.session() as session:
        node_result = session.run("MATCH (n) RETURN count(n) AS c").single()
        rel_result = session.run(
            "MATCH ()-[r]->() RETURN count(r) AS c"
        ).single()
        return {
            "total_nodes": node_result["c"],
            "total_relationships": rel_result["c"],
        }