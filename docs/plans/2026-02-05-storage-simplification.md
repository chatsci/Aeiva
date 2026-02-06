# Storage Module Simplification — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace 9 database backends with 3 embedded ones (ChromaDB + KuzuDB + SQLite), enhance ABCs with shared lifecycle, and eliminate all server/Docker dependencies.

**Architecture:** Three abstract interfaces (`VectorDatabase`, `RelationalDatabase`, `GraphDatabase`) inherit from a new `Database` base that provides `close()` + context-manager. Factory maps 3 provider names to concrete implementations. `MemoryStorage` orchestrates all three. Config files updated to new defaults.

**Tech Stack:** chromadb, kuzu, sqlite3 (stdlib)

---

### Task 1: Add `Database` base class + update ABCs

**Files:**
- Create: `src/aeiva/storage/database.py`
- Modify: `src/aeiva/storage/vector_database.py`
- Modify: `src/aeiva/storage/graph_database.py`
- Modify: `src/aeiva/storage/relational_database.py`
- Test: `tests/storage/test_database_abc.py`

**Step 1: Write tests for the base class and ABC changes**

```python
# tests/storage/test_database_abc.py
"""Tests for Database base class and ABC enhancements."""
import pytest
from aeiva.storage.database import Database
from aeiva.storage.vector_database import VectorDatabase
from aeiva.storage.relational_database import RelationalDatabase
from aeiva.storage.graph_database import GraphDatabase


class TestDatabaseBase:
    def test_cannot_instantiate_database_directly(self):
        with pytest.raises(TypeError):
            Database()

    def test_database_has_close(self):
        assert hasattr(Database, "close")

    def test_context_manager_calls_close(self):
        class FakeDB(Database):
            def __init__(self):
                self.closed = False
            def close(self):
                self.closed = True

        db = FakeDB()
        with db:
            assert not db.closed
        assert db.closed

    def test_vector_database_inherits_database(self):
        assert issubclass(VectorDatabase, Database)

    def test_relational_database_inherits_database(self):
        assert issubclass(RelationalDatabase, Database)

    def test_graph_database_inherits_database(self):
        assert issubclass(GraphDatabase, Database)

    def test_graph_database_has_no_delete_relationships_by_type(self):
        """Removed unused method from ABC."""
        assert not hasattr(GraphDatabase, "delete_relationships_by_type")

    def test_vector_database_has_no_create_client(self):
        """Removed — connection setup belongs in __init__ of concrete classes."""
        abstract_methods = getattr(VectorDatabase, "__abstractmethods__", set())
        assert "create_client" not in abstract_methods
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/storage/test_database_abc.py -v`
Expected: FAIL — `Database` module does not exist yet.

**Step 3: Create `database.py` base class**

```python
# src/aeiva/storage/database.py
from abc import ABC, abstractmethod


class Database(ABC):
    """Common base for all database backends.

    Provides:
      - abstract ``close()`` — every backend must release resources
      - context-manager support (``with db: ...``)
    """

    @abstractmethod
    def close(self) -> None:
        """Release resources (connections, file handles, etc.)."""
        ...

    # ── context manager ──────────────────────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # don't suppress exceptions
```

**Step 4: Update `vector_database.py`**

Remove `create_client()` abstract method. Inherit from `Database`. Keep all other methods.

```python
# src/aeiva/storage/vector_database.py
from abc import abstractmethod
from typing import List, Any, Optional, Dict

from aeiva.storage.database import Database


class VectorDatabase(Database):
    """Abstract base class for vector storage operations."""

    @abstractmethod
    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        ...

    @abstractmethod
    def insert_vectors(self, collection_name: str, vectors: List[List[float]], payloads: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> None:
        ...

    @abstractmethod
    def search_vectors(self, collection_name: str, query_vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        ...

    @abstractmethod
    def update_vector(self, collection_name: str, vector_id: str, vector: Optional[List[float]] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        ...

    @abstractmethod
    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def list_collections(self) -> List[str]:
        ...

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        ...

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        ...
```

**Step 5: Update `relational_database.py`**

Inherit from `Database`. `close()` is already abstract in `Database`, remove duplicate declaration.

```python
# src/aeiva/storage/relational_database.py
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from aeiva.storage.database import Database


class RelationalDatabase(Database):
    """Abstract base class for relational database operations."""

    @abstractmethod
    def insert_record(self, table: str, record: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    def get_record(self, table: str, primary_key: Any) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update_record(self, table: str, primary_key: Any, updates: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete_record(self, table: str, primary_key: Any) -> None:
        ...

    @abstractmethod
    def query_records(self, table: str, conditions: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def execute_sql(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        ...

    @abstractmethod
    def begin_transaction(self) -> None:
        ...

    @abstractmethod
    def commit_transaction(self) -> None:
        ...

    @abstractmethod
    def rollback_transaction(self) -> None:
        ...
```

**Step 6: Update `graph_database.py`**

Inherit from `Database`. Remove `close()` (inherited), remove `delete_relationships_by_type()` (unused).

```python
# src/aeiva/storage/graph_database.py
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from aeiva.storage.database import Database


class NodeNotFoundError(Exception):
    """Exception raised when a node is not found in the graph database."""
    pass


class RelationshipNotFoundError(Exception):
    """Exception raised when a relationship is not found in the graph database."""
    pass


class StorageError(Exception):
    """Exception raised when there is a storage-related error in the graph database."""
    pass


class GraphDatabase(Database):
    """Abstract base class for graph database operations."""

    @abstractmethod
    def add_node(self, node_id: str, properties: Optional[Dict[str, Any]] = None, labels: Optional[List[str]] = None) -> None:
        ...

    @abstractmethod
    def add_edge(self, source_id: str, target_id: str, relationship: str, properties: Optional[Dict[str, Any]] = None) -> None:
        ...

    @abstractmethod
    def get_node(self, node_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        ...

    @abstractmethod
    def delete_all(self) -> None:
        ...

    @abstractmethod
    def delete_all_edges(self) -> None:
        ...

    @abstractmethod
    def delete_edge(self, source_id: str, target_id: str, relationship: str) -> None:
        ...

    @abstractmethod
    def update_edge(self, source_id: str, target_id: str, relationship: str, properties: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get_relationship(self, source_id: str, target_id: str, relationship: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_neighbors(self, node_id: str, relationship: Optional[str] = None, direction: str = "both") -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def query_nodes(self, properties: Dict[str, Any], labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        ...
```

**Step 7: Run tests to verify they pass**

Run: `pytest tests/storage/test_database_abc.py -v`
Expected: All PASS.

**Step 8: Commit**

```bash
git add src/aeiva/storage/database.py src/aeiva/storage/vector_database.py \
  src/aeiva/storage/relational_database.py src/aeiva/storage/graph_database.py \
  tests/storage/test_database_abc.py
git commit -m "refactor(storage): add Database base class, clean ABCs

- New Database ABC with close() + context-manager
- VectorDatabase: remove create_client() from interface
- GraphDatabase: remove unused delete_relationships_by_type()
- All three ABCs now inherit from Database"
```

---

### Task 2: Rewrite ChromaDB implementation

**Files:**
- Create: `src/aeiva/storage/chromadb/__init__.py`
- Create: `src/aeiva/storage/chromadb/chromadb_config.py`
- Create: `src/aeiva/storage/chromadb/chromadb_database.py`
- Test: `tests/storage/test_chromadb.py`

**Step 1: Write tests**

```python
# tests/storage/test_chromadb.py
"""Tests for ChromaDB vector database implementation."""
import pytest
import tempfile
import shutil

from aeiva.storage.chromadb.chromadb_config import ChromaDBConfig
from aeiva.storage.chromadb.chromadb_database import ChromaDBDatabase
from aeiva.storage.vector_database import VectorDatabase
from aeiva.storage.database import Database


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def db(tmp_dir):
    config = ChromaDBConfig(path=tmp_dir, collection_name="test_col")
    database = ChromaDBDatabase(config.to_dict())
    yield database
    database.close()


class TestChromaDBConfig:
    def test_defaults(self):
        cfg = ChromaDBConfig(path="/tmp/test_chroma")
        assert cfg.collection_name == "default"
        assert cfg.path == "/tmp/test_chroma"

    def test_to_dict(self):
        cfg = ChromaDBConfig(path="/tmp/test_chroma", collection_name="my_col")
        d = cfg.to_dict()
        assert d["path"] == "/tmp/test_chroma"
        assert d["collection_name"] == "my_col"


class TestChromaDBDatabase:
    def test_inherits_vector_database(self):
        assert issubclass(ChromaDBDatabase, VectorDatabase)

    def test_inherits_database(self):
        assert issubclass(ChromaDBDatabase, Database)

    def test_insert_and_search(self, db):
        db.insert_vectors(
            collection_name="test_col",
            vectors=[[0.1, 0.2, 0.3]],
            payloads=[{"type": "note"}],
            ids=["v1"],
        )
        results = db.search_vectors(
            collection_name="test_col",
            query_vector=[0.1, 0.2, 0.3],
            top_k=1,
        )
        assert len(results) == 1
        assert results[0]["id"] == "v1"

    def test_get_vector(self, db):
        db.insert_vectors("test_col", [[1.0, 2.0]], ids=["v2"])
        result = db.get_vector("test_col", "v2")
        assert result["id"] == "v2"

    def test_delete_vector(self, db):
        db.insert_vectors("test_col", [[1.0, 2.0]], ids=["v3"])
        db.delete_vector("test_col", "v3")
        with pytest.raises(KeyError):
            db.get_vector("test_col", "v3")

    def test_update_vector(self, db):
        db.insert_vectors("test_col", [[1.0, 2.0]], payloads=[{"a": "b"}], ids=["v4"])
        db.update_vector("test_col", "v4", payload={"a": "c"})
        result = db.get_vector("test_col", "v4")
        assert result["payload"]["a"] == "c"

    def test_list_collections(self, db):
        names = db.list_collections()
        assert "test_col" in names

    def test_delete_collection(self, db):
        db.delete_collection("test_col")
        assert "test_col" not in db.list_collections()

    def test_get_collection_info(self, db):
        info = db.get_collection_info("test_col")
        assert info["name"] == "test_col"

    def test_context_manager(self, tmp_dir):
        config = ChromaDBConfig(path=tmp_dir, collection_name="ctx_col")
        with ChromaDBDatabase(config.to_dict()) as db:
            db.insert_vectors("ctx_col", [[1.0, 2.0]], ids=["v1"])
        # after exit, client should be None
        assert db.client is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/storage/test_chromadb.py -v`
Expected: FAIL — modules don't exist.

**Step 3: Create `chromadb_config.py`**

```python
# src/aeiva/storage/chromadb/chromadb_config.py
from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig


@dataclass
class ChromaDBConfig(BaseConfig):
    """Configuration for ChromaDB vector database."""

    path: str = field(
        default="storage/chromadb",
        metadata={"help": "Path to the ChromaDB persistent directory."},
    )
    collection_name: str = field(
        default="default",
        metadata={"help": "Name of the default collection."},
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Dimensionality of embedding vectors."},
    )
    distance_metric: str = field(
        default="cosine",
        metadata={"help": "Distance metric: cosine, l2, or ip."},
    )
```

**Step 4: Create `chromadb_database.py`**

```python
# src/aeiva/storage/chromadb/chromadb_database.py
import logging
from typing import List, Dict, Any, Optional

from aeiva.storage.vector_database import VectorDatabase

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError("chromadb is required: pip install chromadb")

logger = logging.getLogger(__name__)


class ChromaDBDatabase(VectorDatabase):
    """ChromaDB vector database implementation."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.collection_name = config.get("collection_name", "default")
        self.path = config.get("path", "storage/chromadb")

        settings = Settings(
            anonymized_telemetry=False,
            persist_directory=self.path,
            is_persistent=True,
        )
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        logger.info("ChromaDB initialized at %s", self.path)

    def close(self) -> None:
        self.client = None
        self.collection = None

    def create_collection(
        self, collection_name: str, vector_size: int, distance_metric: str
    ) -> None:
        self.client.get_or_create_collection(name=collection_name)

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        col = self._get_collection(collection_name)
        if ids is None:
            ids = [str(i) for i in range(len(vectors))]
        if payloads is None:
            payloads = [{} for _ in vectors]
        col.add(ids=ids, embeddings=vectors, metadatas=payloads)

    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        col = self._get_collection(collection_name)
        results = col.query(
            query_embeddings=[query_vector],
            where=filters if filters else None,
            n_results=top_k,
        )
        output = []
        for ids, dists, metas in zip(
            results["ids"], results["distances"], results["metadatas"]
        ):
            for i in range(len(ids)):
                output.append(
                    {"id": ids[i], "score": dists[i], "payload": metas[i]}
                )
        return output

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        col = self._get_collection(collection_name)
        col.delete(ids=[vector_id])

    def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: Optional[List[float]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        col = self._get_collection(collection_name)
        col.update(
            ids=[vector_id],
            embeddings=[vector] if vector else None,
            metadatas=[payload] if payload else None,
        )

    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        col = self._get_collection(collection_name)
        result = col.get(ids=[vector_id], include=["embeddings", "metadatas"])
        if not result["ids"]:
            raise KeyError(f"Vector {vector_id!r} not found in {collection_name!r}")
        return {
            "id": result["ids"][0],
            "vector": result["embeddings"][0] if result.get("embeddings") else None,
            "payload": result["metadatas"][0] if result.get("metadatas") else {},
        }

    def list_collections(self) -> List[str]:
        return [c.name for c in self.client.list_collections()]

    def delete_collection(self, collection_name: str) -> None:
        self.client.delete_collection(name=collection_name)

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        col = self.client.get_collection(name=collection_name)
        return {"name": col.name, "metadata": col.metadata}

    # ── internal ─────────────────────────────────────────────────────
    def _get_collection(self, collection_name: str):
        if collection_name == self.collection_name and self.collection is not None:
            return self.collection
        return self.client.get_collection(name=collection_name)
```

**Step 5: Create `__init__.py`**

```python
# src/aeiva/storage/chromadb/__init__.py
```

(Empty file.)

**Step 6: Run tests**

Run: `pytest tests/storage/test_chromadb.py -v`
Expected: All PASS.

**Step 7: Commit**

```bash
git add src/aeiva/storage/chromadb/ tests/storage/test_chromadb.py
git commit -m "feat(storage): add ChromaDB vector database implementation

Embedded, persistent, zero-config. Replaces Milvus as default vector backend."
```

---

### Task 3: Create KuzuDB graph database implementation

**Files:**
- Create: `src/aeiva/storage/kuzudb/__init__.py`
- Create: `src/aeiva/storage/kuzudb/kuzudb_config.py`
- Create: `src/aeiva/storage/kuzudb/kuzudb_database.py`
- Test: `tests/storage/test_kuzudb.py`

**Step 1: Write tests**

```python
# tests/storage/test_kuzudb.py
"""Tests for KuzuDB graph database implementation."""
import pytest
import tempfile
import shutil

from aeiva.storage.kuzudb.kuzudb_config import KuzuDBConfig
from aeiva.storage.kuzudb.kuzudb_database import KuzuDBDatabase
from aeiva.storage.graph_database import GraphDatabase, NodeNotFoundError
from aeiva.storage.database import Database


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def db(tmp_dir):
    config = KuzuDBConfig(database_path=tmp_dir)
    database = KuzuDBDatabase(config.to_dict())
    yield database
    database.close()


class TestKuzuDBConfig:
    def test_defaults(self):
        cfg = KuzuDBConfig()
        assert cfg.database_path == "storage/kuzudb"

    def test_to_dict(self):
        cfg = KuzuDBConfig(database_path="/tmp/kuzu")
        assert cfg.to_dict()["database_path"] == "/tmp/kuzu"


class TestKuzuDBDatabase:
    def test_inherits_graph_database(self):
        assert issubclass(KuzuDBDatabase, GraphDatabase)

    def test_inherits_database(self):
        assert issubclass(KuzuDBDatabase, Database)

    def test_add_and_get_node(self, db):
        db.add_node("n1", properties={"content": "hello"}, labels=["Note"])
        node = db.get_node("n1")
        assert node["id"] == "n1"
        assert node["properties"]["content"] == "hello"

    def test_get_nonexistent_node(self, db):
        with pytest.raises(NodeNotFoundError):
            db.get_node("nonexistent")

    def test_update_node(self, db):
        db.add_node("n1", properties={"content": "old"})
        db.update_node("n1", {"content": "new"})
        node = db.get_node("n1")
        assert node["properties"]["content"] == "new"

    def test_delete_node(self, db):
        db.add_node("n1")
        db.delete_node("n1")
        with pytest.raises(NodeNotFoundError):
            db.get_node("n1")

    def test_add_and_get_edge(self, db):
        db.add_node("a")
        db.add_node("b")
        db.add_edge("a", "b", "RELATED_TO", {"weight": 0.5})
        rel = db.get_relationship("a", "b", "RELATED_TO")
        assert rel is not None

    def test_get_neighbors(self, db):
        db.add_node("a")
        db.add_node("b")
        db.add_node("c")
        db.add_edge("a", "b", "KNOWS")
        db.add_edge("a", "c", "KNOWS")
        neighbors = db.get_neighbors("a", relationship="KNOWS", direction="out")
        ids = {n["id"] for n in neighbors}
        assert ids == {"b", "c"}

    def test_delete_edge(self, db):
        db.add_node("a")
        db.add_node("b")
        db.add_edge("a", "b", "LINKS")
        db.delete_edge("a", "b", "LINKS")
        neighbors = db.get_neighbors("a", direction="out")
        assert len(neighbors) == 0

    def test_delete_all(self, db):
        db.add_node("a")
        db.add_node("b")
        db.add_edge("a", "b", "KNOWS")
        db.delete_all()
        with pytest.raises(NodeNotFoundError):
            db.get_node("a")

    def test_query_nodes(self, db):
        db.add_node("n1", properties={"type": "note"})
        db.add_node("n2", properties={"type": "event"})
        results = db.query_nodes({"type": "note"})
        assert len(results) == 1
        assert results[0]["id"] == "n1"

    def test_context_manager(self, tmp_dir):
        config = KuzuDBConfig(database_path=tmp_dir)
        with KuzuDBDatabase(config.to_dict()) as db:
            db.add_node("n1")
        assert db._db is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/storage/test_kuzudb.py -v`
Expected: FAIL — modules don't exist.

**Step 3: Create `kuzudb_config.py`**

```python
# src/aeiva/storage/kuzudb/kuzudb_config.py
from dataclasses import dataclass, field
from aeiva.config.base_config import BaseConfig


@dataclass
class KuzuDBConfig(BaseConfig):
    """Configuration for KuzuDB embedded graph database."""

    database_path: str = field(
        default="storage/kuzudb",
        metadata={"help": "Path to the KuzuDB database directory."},
    )
    read_only: bool = field(
        default=False,
        metadata={"help": "Open database in read-only mode."},
    )
```

**Step 4: Create `kuzudb_database.py`**

This is the most complex new file. KuzuDB uses Cypher and has a specific schema model
(node/rel tables must be created before inserting data). We use a generic schema to
match the `GraphDatabase` ABC contract: a single `Node` table and per-relationship-type
`Rel` tables created on demand.

```python
# src/aeiva/storage/kuzudb/kuzudb_database.py
"""KuzuDB embedded graph database implementation.

KuzuDB requires explicit schema (node tables, relationship tables) before
inserting data.  This implementation uses:
  - A single ``Node`` node-table with columns: id STRING, properties STRING, labels STRING
  - Relationship tables created on-demand per relationship type, each with a
    ``properties`` STRING column.  Table name = relationship type.

Complex property values are JSON-serialized into the ``properties`` column.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from aeiva.storage.graph_database import (
    GraphDatabase,
    NodeNotFoundError,
    RelationshipNotFoundError,
    StorageError,
)

try:
    import kuzu
except ImportError:
    raise ImportError("kuzu is required: pip install kuzu")

logger = logging.getLogger(__name__)


class KuzuDBDatabase(GraphDatabase):
    """KuzuDB graph database implementation."""

    _NODE_TABLE = "Node"

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        db_path = config.get("database_path", "storage/kuzudb")
        read_only = config.get("read_only", False)
        self._db = kuzu.Database(db_path, read_only=read_only)
        self._conn = kuzu.Connection(self._db)
        self._ensure_node_table()
        self._rel_tables: set = set()
        self._discover_existing_rel_tables()
        logger.info("KuzuDB initialized at %s", db_path)

    def close(self) -> None:
        self._conn = None
        self._db = None

    # ── node operations ──────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        properties: Optional[Dict[str, Any]] = None,
        labels: Optional[List[str]] = None,
    ) -> None:
        props_json = json.dumps(properties or {})
        labels_json = json.dumps(labels or [])
        try:
            self._conn.execute(
                f"MERGE (n:{self._NODE_TABLE} {{id: $id}}) "
                f"SET n.properties = $props, n.labels = $labels",
                {"id": node_id, "props": props_json, "labels": labels_json},
            )
        except Exception as e:
            raise StorageError(f"Failed to add node {node_id!r}: {e}")

    def get_node(self, node_id: str) -> Dict[str, Any]:
        try:
            result = self._conn.execute(
                f"MATCH (n:{self._NODE_TABLE} {{id: $id}}) RETURN n.id, n.properties, n.labels",
                {"id": node_id},
            )
            if not result.has_next():
                raise NodeNotFoundError(f"Node {node_id!r} not found")
            row = result.get_next()
            return {
                "id": row[0],
                "properties": json.loads(row[1]) if row[1] else {},
                "labels": json.loads(row[2]) if row[2] else [],
            }
        except NodeNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get node {node_id!r}: {e}")

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
        existing = self.get_node(node_id)  # raises NodeNotFoundError
        merged = {**existing["properties"], **properties}
        props_json = json.dumps(merged)
        try:
            self._conn.execute(
                f"MATCH (n:{self._NODE_TABLE} {{id: $id}}) SET n.properties = $props",
                {"id": node_id, "props": props_json},
            )
        except Exception as e:
            raise StorageError(f"Failed to update node {node_id!r}: {e}")

    def delete_node(self, node_id: str) -> None:
        self.get_node(node_id)  # raises NodeNotFoundError
        try:
            self._conn.execute(
                f"MATCH (n:{self._NODE_TABLE} {{id: $id}}) DETACH DELETE n",
                {"id": node_id},
            )
        except Exception as e:
            raise StorageError(f"Failed to delete node {node_id!r}: {e}")

    def delete_all(self) -> None:
        try:
            # Delete all relationships first
            for rel_table in list(self._rel_tables):
                self._conn.execute(f"MATCH ()-[r:{rel_table}]->() DELETE r")
            # Delete all nodes
            self._conn.execute(f"MATCH (n:{self._NODE_TABLE}) DELETE n")
        except Exception as e:
            raise StorageError(f"Failed to delete all: {e}")

    # ── edge operations ──────────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._ensure_rel_table(relationship)
        props_json = json.dumps(properties or {})
        try:
            self._conn.execute(
                f"MATCH (a:{self._NODE_TABLE} {{id: $src}}), (b:{self._NODE_TABLE} {{id: $tgt}}) "
                f"CREATE (a)-[r:{relationship} {{properties: $props}}]->(b)",
                {"src": source_id, "tgt": target_id, "props": props_json},
            )
        except Exception as e:
            raise StorageError(
                f"Failed to add edge {source_id!r}-[{relationship}]->{target_id!r}: {e}"
            )

    def delete_edge(
        self, source_id: str, target_id: str, relationship: str
    ) -> None:
        if relationship not in self._rel_tables:
            raise RelationshipNotFoundError(
                f"Relationship type {relationship!r} does not exist"
            )
        try:
            self._conn.execute(
                f"MATCH (a:{self._NODE_TABLE} {{id: $src}})-[r:{relationship}]->(b:{self._NODE_TABLE} {{id: $tgt}}) "
                f"DELETE r",
                {"src": source_id, "tgt": target_id},
            )
        except Exception as e:
            raise StorageError(f"Failed to delete edge: {e}")

    def delete_all_edges(self) -> None:
        try:
            for rel_table in list(self._rel_tables):
                self._conn.execute(f"MATCH ()-[r:{rel_table}]->() DELETE r")
        except Exception as e:
            raise StorageError(f"Failed to delete all edges: {e}")

    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Dict[str, Any],
    ) -> None:
        if relationship not in self._rel_tables:
            raise RelationshipNotFoundError(
                f"Relationship type {relationship!r} does not exist"
            )
        # Merge with existing properties
        existing = self.get_relationship(source_id, target_id, relationship)
        merged = {**existing.get("properties", {}), **properties}
        props_json = json.dumps(merged)
        try:
            self._conn.execute(
                f"MATCH (a:{self._NODE_TABLE} {{id: $src}})-[r:{relationship}]->(b:{self._NODE_TABLE} {{id: $tgt}}) "
                f"SET r.properties = $props",
                {"src": source_id, "tgt": target_id, "props": props_json},
            )
        except Exception as e:
            raise StorageError(f"Failed to update edge: {e}")

    def get_relationship(
        self, source_id: str, target_id: str, relationship: str
    ) -> Dict[str, Any]:
        if relationship not in self._rel_tables:
            raise RelationshipNotFoundError(
                f"Relationship type {relationship!r} does not exist"
            )
        try:
            result = self._conn.execute(
                f"MATCH (a:{self._NODE_TABLE} {{id: $src}})-[r:{relationship}]->(b:{self._NODE_TABLE} {{id: $tgt}}) "
                f"RETURN r.properties",
                {"src": source_id, "tgt": target_id},
            )
            if not result.has_next():
                raise RelationshipNotFoundError(
                    f"No {relationship!r} between {source_id!r} and {target_id!r}"
                )
            row = result.get_next()
            return {
                "type": relationship,
                "properties": json.loads(row[0]) if row[0] else {},
            }
        except RelationshipNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to get relationship: {e}")

    def get_neighbors(
        self,
        node_id: str,
        relationship: Optional[str] = None,
        direction: str = "both",
    ) -> List[Dict[str, Any]]:
        self.get_node(node_id)  # raises NodeNotFoundError

        # Determine which rel tables to query
        rel_tables = [relationship] if relationship else list(self._rel_tables)
        if not rel_tables:
            return []

        neighbors = []
        for rel in rel_tables:
            if rel not in self._rel_tables:
                continue
            for d in self._direction_patterns(direction):
                query = (
                    f"MATCH (a:{self._NODE_TABLE} {{id: $id}}){d[0]}[r:{rel}]{d[1]}"
                    f"(neighbor:{self._NODE_TABLE}) "
                    f"RETURN neighbor.id, neighbor.properties, neighbor.labels"
                )
                try:
                    result = self._conn.execute(query, {"id": node_id})
                    while result.has_next():
                        row = result.get_next()
                        neighbors.append({
                            "id": row[0],
                            "properties": json.loads(row[1]) if row[1] else {},
                            "labels": json.loads(row[2]) if row[2] else [],
                        })
                except Exception as e:
                    logger.warning("Neighbor query failed for rel %s: %s", rel, e)
        # Deduplicate by id
        seen = set()
        unique = []
        for n in neighbors:
            if n["id"] not in seen:
                seen.add(n["id"])
                unique.append(n)
        return unique

    def query_nodes(
        self,
        properties: Dict[str, Any],
        labels: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            result = self._conn.execute(
                f"MATCH (n:{self._NODE_TABLE}) RETURN n.id, n.properties, n.labels"
            )
            nodes = []
            while result.has_next():
                row = result.get_next()
                node_props = json.loads(row[1]) if row[1] else {}
                node_labels = json.loads(row[2]) if row[2] else []
                # Filter by properties
                if all(node_props.get(k) == v for k, v in properties.items()):
                    # Filter by labels if specified
                    if labels and not any(l in node_labels for l in labels):
                        continue
                    nodes.append({
                        "id": row[0],
                        "properties": node_props,
                        "labels": node_labels,
                    })
            return nodes
        except Exception as e:
            raise StorageError(f"Failed to query nodes: {e}")

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        try:
            result = self._conn.execute(query, parameters or {})
            rows = []
            while result.has_next():
                rows.append(result.get_next())
            return rows
        except Exception as e:
            raise StorageError(f"Failed to execute query: {e}")

    # ── internal helpers ─────────────────────────────────────────────

    def _ensure_node_table(self) -> None:
        """Create the Node table if it doesn't exist."""
        try:
            self._conn.execute(
                f"CREATE NODE TABLE IF NOT EXISTS {self._NODE_TABLE} "
                f"(id STRING, properties STRING, labels STRING, PRIMARY KEY (id))"
            )
        except Exception as e:
            logger.debug("Node table creation note: %s", e)

    def _ensure_rel_table(self, relationship: str) -> None:
        """Create a relationship table on demand."""
        if relationship in self._rel_tables:
            return
        try:
            self._conn.execute(
                f"CREATE REL TABLE IF NOT EXISTS {relationship} "
                f"(FROM {self._NODE_TABLE} TO {self._NODE_TABLE}, properties STRING)"
            )
            self._rel_tables.add(relationship)
        except Exception as e:
            # Table might already exist
            self._rel_tables.add(relationship)
            logger.debug("Rel table %s creation note: %s", relationship, e)

    def _discover_existing_rel_tables(self) -> None:
        """Populate _rel_tables from existing schema."""
        try:
            result = self._conn.execute("CALL show_tables() RETURN *")
            while result.has_next():
                row = result.get_next()
                # row format: [name, type, ...]
                # type = 'REL' for relationship tables
                if len(row) >= 2 and str(row[1]).upper() == "REL":
                    self._rel_tables.add(row[0])
        except Exception:
            pass  # Fresh database has no tables

    @staticmethod
    def _direction_patterns(direction: str):
        """Return Cypher arrow patterns for the given direction."""
        if direction == "out":
            return [("-", "->")]
        elif direction == "in":
            return [("<-", "-")]
        else:  # both
            return [("-", "->"), ("<-", "-")]
```

**Step 5: Create `__init__.py`**

```python
# src/aeiva/storage/kuzudb/__init__.py
```

**Step 6: Run tests**

Run: `pytest tests/storage/test_kuzudb.py -v`
Expected: All PASS. (Requires `pip install kuzu` first.)

**Step 7: Commit**

```bash
git add src/aeiva/storage/kuzudb/ tests/storage/test_kuzudb.py
git commit -m "feat(storage): add KuzuDB embedded graph database implementation

Replaces Neo4j. Embedded, file-based, zero-server.
Uses generic Node table + on-demand relationship tables."
```

---

### Task 4: Update SQLite to inherit from new Database base

**Files:**
- Modify: `src/aeiva/storage/sqlite/sqlite_database.py`
- Test: `tests/storage/test_sqlite.py`

**Step 1: Write a quick inheritance test**

```python
# tests/storage/test_sqlite.py
"""Tests for SQLite database implementation with new Database base."""
import pytest
from aeiva.storage.sqlite.sqlite_database import SQLiteDatabase
from aeiva.storage.relational_database import RelationalDatabase
from aeiva.storage.database import Database


class TestSQLiteDatabase:
    def test_inherits_relational_database(self):
        assert issubclass(SQLiteDatabase, RelationalDatabase)

    def test_inherits_database(self):
        assert issubclass(SQLiteDatabase, Database)

    def test_context_manager(self):
        with SQLiteDatabase({"database": ":memory:"}) as db:
            db.execute_sql("CREATE TABLE t (id TEXT PRIMARY KEY, val TEXT)")
            db.execute_sql("INSERT INTO t VALUES ('k', 'v')")
            result = db.execute_sql("SELECT val FROM t WHERE id = 'k'")
            assert result.fetchone()[0] == "v"
        # After exit, connection should be closed
        assert db.connection is None or not db.connection

    def test_insert_and_query(self):
        db = SQLiteDatabase({"database": ":memory:"})
        db.execute_sql("CREATE TABLE items (id TEXT PRIMARY KEY, name TEXT)")
        db.insert_record("items", {"id": "1", "name": "test"})
        record = db.get_record("items", "1")
        assert record["name"] == "test"
        db.close()
```

**Step 2: Run test**

Run: `pytest tests/storage/test_sqlite.py -v`
Expected: Likely PASS already (SQLiteDatabase already has close()), but `test_inherits_database` will FAIL if we haven't updated the import chain yet. (It will pass once Task 1 is done.)

**Step 3: Update `sqlite_database.py` — ensure `close()` nulls connection**

The only change needed: null out `self.connection` in `close()` so the context manager test passes cleanly.

In `sqlite_database.py`, update `close()`:

```python
    def close(self) -> None:
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None
```

**Step 4: Run tests**

Run: `pytest tests/storage/test_sqlite.py tests/memory/test_memory_storage.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/aeiva/storage/sqlite/sqlite_database.py tests/storage/test_sqlite.py
git commit -m "refactor(storage): update SQLite to inherit from Database base

Nulls connection on close() for clean context-manager lifecycle."
```

---

### Task 5: Simplify DatabaseFactory

**Files:**
- Modify: `src/aeiva/storage/database_factory.py`
- Test: `tests/storage/test_database_factory.py`

**Step 1: Write tests**

```python
# tests/storage/test_database_factory.py
"""Tests for simplified DatabaseFactory."""
import pytest
from aeiva.storage.database_factory import DatabaseConfigFactory, DatabaseFactory


class TestDatabaseConfigFactory:
    def test_create_chromadb(self):
        config = DatabaseConfigFactory.create("chromadb", path="/tmp/test_chroma")
        assert config.path == "/tmp/test_chroma"

    def test_create_kuzudb(self):
        config = DatabaseConfigFactory.create("kuzudb", database_path="/tmp/kuzu")
        assert config.database_path == "/tmp/kuzu"

    def test_create_sqlite(self):
        config = DatabaseConfigFactory.create("sqlite", database=":memory:")
        assert config.database == ":memory:"

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            DatabaseConfigFactory.create("milvus")

    def test_supported_providers(self):
        assert set(DatabaseConfigFactory.provider_to_class.keys()) == {
            "chromadb", "kuzudb", "sqlite"
        }


class TestDatabaseFactory:
    def test_create_sqlite(self):
        config = DatabaseConfigFactory.create("sqlite", database=":memory:")
        db = DatabaseFactory.create("sqlite", config)
        db.execute_sql("SELECT 1")
        db.close()

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            DatabaseFactory.create("neo4j", {})

    def test_supported_providers(self):
        assert set(DatabaseFactory.provider_to_class.keys()) == {
            "chromadb", "kuzudb", "sqlite"
        }
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/storage/test_database_factory.py -v`
Expected: FAIL — factory still has 9 providers.

**Step 3: Rewrite `database_factory.py`**

```python
# src/aeiva/storage/database_factory.py
"""Database factory — maps provider names to concrete implementations.

Supported providers:
  - chromadb  (VectorDatabase)
  - kuzudb    (GraphDatabase)
  - sqlite    (RelationalDatabase)
"""

import importlib
from typing import Any, Type


def load_class(class_path: str) -> Type:
    """Dynamically load a class from a dotted path string."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class DatabaseConfigFactory:
    """Create config dataclass instances by provider name."""

    provider_to_class = {
        "chromadb": "aeiva.storage.chromadb.chromadb_config.ChromaDBConfig",
        "kuzudb": "aeiva.storage.kuzudb.kuzudb_config.KuzuDBConfig",
        "sqlite": "aeiva.storage.sqlite.sqlite_config.SQLiteConfig",
    }

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> Any:
        class_path = cls.provider_to_class.get(provider_name.lower())
        if not class_path:
            raise ValueError(f"Unsupported database provider: {provider_name}")
        config_class = load_class(class_path)
        return config_class(**kwargs)


class DatabaseFactory:
    """Create database instances by provider name + config."""

    provider_to_class = {
        "chromadb": "aeiva.storage.chromadb.chromadb_database.ChromaDBDatabase",
        "kuzudb": "aeiva.storage.kuzudb.kuzudb_database.KuzuDBDatabase",
        "sqlite": "aeiva.storage.sqlite.sqlite_database.SQLiteDatabase",
    }

    @classmethod
    def create(cls, provider_name: str, config: Any) -> Any:
        class_path = cls.provider_to_class.get(provider_name.lower())
        if not class_path:
            raise ValueError(f"Unsupported database provider: {provider_name}")
        db_class = load_class(class_path)
        if isinstance(config, dict):
            return db_class(config)
        elif hasattr(config, "to_dict"):
            return db_class(config.to_dict())
        elif hasattr(config, "__dict__"):
            return db_class(vars(config))
        else:
            raise TypeError("Config must be a dict or have to_dict()/__dict__")
```

**Step 4: Run tests**

Run: `pytest tests/storage/test_database_factory.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/aeiva/storage/database_factory.py tests/storage/test_database_factory.py
git commit -m "refactor(storage): simplify factory to 3 providers

Only chromadb, kuzudb, sqlite. Removed 6 unused backends."
```

---

### Task 6: Update MemoryStorage + StorageConfig defaults

**Files:**
- Modify: `src/aeiva/cognition/memory/memory_storage.py`
- Modify: `src/aeiva/cognition/memory/storage_config.py`
- Test: `tests/memory/test_memory_storage.py` (existing — must still pass)

**Step 1: Update `storage_config.py`**

No structural changes needed, just make sure defaults align. The dataclass doesn't hardcode provider names — it's provider-agnostic. No changes required.

**Step 2: Update `memory_storage.py`**

Change default provider names from `"milvus"` → `"chromadb"` and `"neo4j"` → `"kuzudb"`. Remove `hasattr` checks in `close()` since `Database.close()` is now guaranteed.

In `MemoryStorage.setup()`, update these default values:
- `vector_db_conf_dict.get('provider_name', 'milvus')` → `'chromadb'`
- `graph_db_conf_dict.get('provider_name', 'neo4j')` → `'kuzudb'`
- Default vector uri: `'storage/milvus_demo.db'` → `'storage/chromadb'`
- Default graph config params: remove neo4j-specific defaults (user, password, encrypted), add `database_path`

In `MemoryStorage.close()`, simplify:
```python
def close(self) -> None:
    """Close all configured database connections (best-effort)."""
    for name, db in [("vector", self.vector_db),
                     ("graph", self.graph_db),
                     ("relational", self.relational_db)]:
        if db is not None:
            try:
                db.close()
            except Exception as e:
                logger.warning("Error closing %s DB: %s", name, e)
```

**Step 3: Run existing tests**

Run: `pytest tests/memory/test_memory_storage.py -v`
Expected: All PASS (these tests use SQLite directly, unaffected by default changes).

**Step 4: Commit**

```bash
git add src/aeiva/cognition/memory/memory_storage.py src/aeiva/cognition/memory/storage_config.py
git commit -m "refactor(memory): update MemoryStorage defaults to chromadb/kuzudb

Defaults now use embedded providers. Simplified close() using Database base."
```

---

### Task 7: Update config files

**Files:**
- Modify: `configs/agent_config.yaml`
- Modify: `configs/agent_config_realtime.yaml`

**Step 1: Update `agent_config.yaml` storage section**

```yaml
storage_config:
  vector_db_config:
    provider_name: "chromadb"
    path: "storage/chromadb"
    collection_name: "memory_collection"
    embedding_model_dims: 1536
    distance_metric: "cosine"
  graph_db_config:
    provider_name: "kuzudb"
    database_path: "storage/kuzudb"
  relational_db_config:
    provider_name: "sqlite"
    database: "storage/aeiva.db"
```

**Step 2: Update `agent_config_realtime.yaml` storage section**

```yaml
storage_config:
  vector_db_config:
    provider_name: "chromadb"
    path: "storage/chromadb_realtime"
    collection_name: "realtime_collection"
    embedding_model_dims: 1536
    distance_metric: "cosine"
  graph_db_config:
    provider_name: "kuzudb"
    database_path: "storage/kuzudb_realtime"
  relational_db_config:
    provider_name: "sqlite"
    database: "storage/aeiva_realtime.db"
```

**Step 3: Commit**

```bash
git add configs/agent_config.yaml configs/agent_config_realtime.yaml
git commit -m "config: update storage to chromadb/kuzudb/sqlite

Removed all server-based DB references (Milvus, Neo4j).
All databases are now embedded and zero-config."
```

---

### Task 8: Delete old backend directories

**Files:**
- Delete: `src/aeiva/storage/milvus/`
- Delete: `src/aeiva/storage/chroma/` (old version, replaced by `chromadb/`)
- Delete: `src/aeiva/storage/azure_ai_search/`
- Delete: `src/aeiva/storage/pgvector/`
- Delete: `src/aeiva/storage/qdrant/`
- Delete: `src/aeiva/storage/weaviate/`
- Delete: `src/aeiva/storage/postgresql/`
- Delete: `src/aeiva/storage/neo4jdb/`

**Step 1: Delete directories**

```bash
rm -rf src/aeiva/storage/milvus
rm -rf src/aeiva/storage/chroma
rm -rf src/aeiva/storage/azure_ai_search
rm -rf src/aeiva/storage/pgvector
rm -rf src/aeiva/storage/qdrant
rm -rf src/aeiva/storage/weaviate
rm -rf src/aeiva/storage/postgresql
rm -rf src/aeiva/storage/neo4jdb
```

**Step 2: Delete old storage data files (Milvus .db files)**

```bash
rm -f storage/milvus_demo.db
rm -f storage/milvus_realtime.db
rm -f storage/test_database.db
```

**Step 3: Run all storage + memory tests to confirm nothing broke**

Run: `pytest tests/storage/ tests/memory/ -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore(storage): delete 8 unused database backends

Removed: milvus, chroma (old), azure_ai_search, pgvector, qdrant,
weaviate, postgresql, neo4jdb. ~36 files deleted."
```

---

### Task 9: Update `pyproject.toml` — remove unused DB dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Remove these dependencies from the `dependencies` list:**

- `pymilvus==2.4.9` — removed (Milvus)
- `neo4j==5.26.0` — removed (Neo4j)
- `psycopg2-binary==2.9.10` — removed (PostgreSQL)
- `qdrant-client==1.12.1` — removed (Qdrant)

**Step 2: Ensure these remain (or add if missing):**

- `chromadb==0.5.20` — keep (already present)
- `kuzu` — add (new dependency for KuzuDB)

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "deps: remove unused DB packages, add kuzu

Removed: pymilvus, neo4j, psycopg2-binary, qdrant-client.
Added: kuzu. Kept: chromadb."
```

---

### Task 10: Update `storage/__init__.py` with clean exports

**Files:**
- Modify: `src/aeiva/storage/__init__.py`

**Step 1: Write exports**

```python
# src/aeiva/storage/__init__.py
"""Storage module — abstract database interfaces + embedded implementations."""

from aeiva.storage.database import Database
from aeiva.storage.vector_database import VectorDatabase
from aeiva.storage.relational_database import RelationalDatabase
from aeiva.storage.graph_database import (
    GraphDatabase,
    NodeNotFoundError,
    RelationshipNotFoundError,
    StorageError,
)
from aeiva.storage.database_factory import DatabaseFactory, DatabaseConfigFactory

__all__ = [
    "Database",
    "VectorDatabase",
    "RelationalDatabase",
    "GraphDatabase",
    "NodeNotFoundError",
    "RelationshipNotFoundError",
    "StorageError",
    "DatabaseFactory",
    "DatabaseConfigFactory",
]
```

**Step 2: Commit**

```bash
git add src/aeiva/storage/__init__.py
git commit -m "refactor(storage): add clean module exports"
```

---

### Task 11: Update README — remove Neo4j prerequisite

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md` (if it has the same prerequisite)

**Step 1: In README.md, remove the Neo4j prerequisite line:**

Change:
```
- Python 3.10+
- Neo4j (for graph memory). Set `NEO4J_HOME` if needed.
```
To:
```
- Python 3.10+
```

**Step 2: Commit**

```bash
git add README.md README_CN.md
git commit -m "docs: remove Neo4j prerequisite from README

All databases are now embedded. No external services required."
```

---

### Task 12: Final verification — run full test suite

**Step 1: Run all tests**

```bash
pytest tests/storage/ tests/memory/ -v
```

Expected: All PASS.

**Step 2: Quick smoke test — verify aeiva can start**

```bash
python -c "from aeiva.storage import Database, VectorDatabase, RelationalDatabase, GraphDatabase, DatabaseFactory; print('Storage module OK')"
python -c "from aeiva.storage.chromadb.chromadb_database import ChromaDBDatabase; print('ChromaDB OK')"
python -c "from aeiva.storage.kuzudb.kuzudb_database import KuzuDBDatabase; print('KuzuDB OK')"
python -c "from aeiva.storage.sqlite.sqlite_database import SQLiteDatabase; print('SQLite OK')"
```

Expected: All print OK.

---

## Summary

| Before | After |
|--------|-------|
| 9 backends, ~44 files | 3 backends, ~12 files |
| Milvus (server/file), Neo4j (server), SQLite | ChromaDB (embedded), KuzuDB (embedded), SQLite |
| No common base class | `Database` ABC with `close()` + context manager |
| `create_client()` in VectorDatabase ABC | Removed — connection in `__init__` |
| `delete_relationships_by_type()` in GraphDatabase | Removed — unused |
| pymilvus, neo4j, psycopg2, qdrant-client deps | chromadb, kuzu deps |
| Neo4j server prerequisite | Zero external services |
| `hasattr(db, "close")` checks | Direct `db.close()` — guaranteed by ABC |

Total: 12 tasks, ~8 files created, ~36 files deleted, 6 files modified.
