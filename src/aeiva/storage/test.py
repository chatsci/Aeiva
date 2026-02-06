"""Manual storage smoke tests for the default embedded backends."""

import logging
import tempfile
import uuid
from pathlib import Path

from aeiva.storage.database_factory import DatabaseConfigFactory, DatabaseFactory

logging.basicConfig(level=logging.INFO)


def test_chroma(base_dir: Path) -> None:
    print("\n--- Testing Chroma ---")
    config = DatabaseConfigFactory.create(
        "chroma",
        path=str(base_dir / "chroma"),
        collection_name="smoke_collection",
        embedding_model_dims=3,
        metric_type="COSINE",
    )
    db = DatabaseFactory.create("chroma", config)
    try:
        vector_id = uuid.uuid4().hex
        db.insert_vectors(
            collection_name=config.collection_name,
            vectors=[[0.1, 0.2, 0.3]],
            payloads=[{"kind": "smoke"}],
            ids=[vector_id],
        )
        result = db.get_vector(config.collection_name, vector_id)
        print("Chroma vector:", result["id"])
    finally:
        db.close()


def test_kuzu(base_dir: Path) -> None:
    print("\n--- Testing Kuzu ---")
    config = DatabaseConfigFactory.create(
        "kuzu",
        database=str(base_dir / "kuzu.db"),
    )
    db = DatabaseFactory.create("kuzu", config)
    try:
        db.add_node("node_a", {"kind": "person"}, ["Entity"])
        db.add_node("node_b", {"kind": "person"}, ["Entity"])
        db.add_edge("node_a", "node_b", "KNOWS", {"since": 2024})
        rel = db.get_relationship("node_a", "node_b", "KNOWS")
        print("Kuzu relationship:", rel["type"])
    finally:
        db.close()


def test_sqlite(base_dir: Path) -> None:
    print("\n--- Testing SQLite ---")
    config = DatabaseConfigFactory.create(
        "sqlite",
        database=str(base_dir / "sqlite.db"),
    )
    db = DatabaseFactory.create("sqlite", config)
    try:
        db.execute_sql("CREATE TABLE IF NOT EXISTS smoke (id TEXT PRIMARY KEY, val TEXT)")
        record_id = uuid.uuid4().hex
        db.insert_record("smoke", {"id": record_id, "val": "v"})
        result = db.get_record("smoke", record_id)
        print("SQLite record:", result)
    finally:
        db.close()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="aeiva-storage-smoke-") as tmp_dir:
        base_dir = Path(tmp_dir)
        test_chroma(base_dir)
        test_kuzu(base_dir)
        test_sqlite(base_dir)


if __name__ == "__main__":
    main()
