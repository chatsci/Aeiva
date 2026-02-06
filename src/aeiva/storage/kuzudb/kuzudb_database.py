import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from aeiva.storage.graph_database import (
    GraphDatabase,
    NodeNotFoundError,
    RelationshipNotFoundError,
    StorageError,
)

try:
    import kuzu
except ImportError:  # pragma: no cover - depends on optional runtime dependency
    kuzu = None

logger = logging.getLogger(__name__)

_RELATION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class KuzuDatabase(GraphDatabase):
    """Graph database implementation backed by embedded Kuzu."""

    _NODE_TABLE = "MemoryNode"

    def __init__(self, config: Dict[str, Any]) -> None:
        if kuzu is None:  # pragma: no cover - optional dependency runtime guard
            raise ImportError(
                "The 'kuzu' package is required for KuzuDatabase. Install with `pip install kuzu`."
            )

        self.config = config
        self.database_path = config.get("database", "storage/kuzu.db")
        self.read_only = bool(config.get("read_only", False))
        self._relation_tables: Set[str] = set()

        if not self.read_only:
            Path(self.database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )

        try:
            self._db = kuzu.Database(self.database_path, read_only=self.read_only)
            self._conn = kuzu.Connection(self._db)
            self._ensure_node_table()
            self._discover_relationship_tables()
        except Exception as exc:
            raise StorageError(f"Failed to initialize Kuzu database: {exc}") from exc

    def close(self) -> None:
        self._conn = None
        self._db = None

    def add_node(
        self,
        node_id: str,
        properties: Optional[Dict[str, Any]] = None,
        labels: Optional[List[str]] = None,
    ) -> None:
        props = self._to_json(properties or {})
        node_labels = self._to_json(labels or [])
        query = (
            f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
            f"RETURN n.id LIMIT 1;"
        )
        exists = bool(self._rows(query))

        if exists:
            upsert = (
                f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
                f"SET n.properties={self._sql_str(props)}, n.labels={self._sql_str(node_labels)};"
            )
        else:
            upsert = (
                f"CREATE (n:{self._NODE_TABLE} {{"
                f"id: {self._sql_str(node_id)}, "
                f"properties: {self._sql_str(props)}, "
                f"labels: {self._sql_str(node_labels)}"
                f"}});"
            )

        try:
            self._execute(upsert)
        except Exception as exc:
            raise StorageError(f"Failed to add node '{node_id}': {exc}") from exc

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        rel_type = self._normalize_relationship(relationship)
        self._ensure_relationship_table(rel_type)
        self._ensure_node_exists(source_id)
        self._ensure_node_exists(target_id)

        edge_properties = self._to_json(properties or {})
        query = (
            f"MATCH (a:{self._NODE_TABLE} {{id: {self._sql_str(source_id)}}}), "
            f"(b:{self._NODE_TABLE} {{id: {self._sql_str(target_id)}}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r.properties={self._sql_str(edge_properties)};"
        )
        try:
            self._execute(query)
        except Exception as exc:
            raise StorageError(
                f"Failed to add edge {source_id}-[{relationship}]->{target_id}: {exc}"
            ) from exc

    def get_node(self, node_id: str) -> Dict[str, Any]:
        query = (
            f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
            f"RETURN n.id, n.properties, n.labels LIMIT 1;"
        )
        try:
            rows = self._rows(query)
        except Exception as exc:
            raise StorageError(f"Failed to get node '{node_id}': {exc}") from exc

        if not rows:
            raise NodeNotFoundError(f"Node with id '{node_id}' not found.")

        row = rows[0]
        return {
            "id": row[0],
            "properties": self._from_json(row[1], default={}),
            "labels": self._from_json(row[2], default=[]),
        }

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
        current = self.get_node(node_id)
        merged = {**current["properties"], **(properties or {})}
        query = (
            f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
            f"SET n.properties={self._sql_str(self._to_json(merged))};"
        )
        try:
            self._execute(query)
        except Exception as exc:
            raise StorageError(f"Failed to update node '{node_id}': {exc}") from exc

    def delete_node(self, node_id: str) -> None:
        self._ensure_node_exists(node_id)
        query = (
            f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
            f"DETACH DELETE n;"
        )
        try:
            self._execute(query)
        except Exception as exc:
            raise StorageError(f"Failed to delete node '{node_id}': {exc}") from exc

    def delete_all(self) -> None:
        try:
            self.delete_all_edges()
            self._execute(f"MATCH (n:{self._NODE_TABLE}) DELETE n;")
        except Exception as exc:
            raise StorageError(f"Failed to delete all graph data: {exc}") from exc

    def delete_all_edges(self) -> None:
        try:
            for rel_type in list(self._relation_tables):
                self._execute(f"MATCH ()-[r:{rel_type}]->() DELETE r;")
        except Exception as exc:
            raise StorageError(f"Failed to delete all edges: {exc}") from exc

    def delete_edge(self, source_id: str, target_id: str, relationship: str) -> None:
        self.get_relationship(source_id, target_id, relationship)
        rel_type = self._normalize_relationship(relationship)
        query = (
            f"MATCH (a:{self._NODE_TABLE} {{id: {self._sql_str(source_id)}}})"
            f"-[r:{rel_type}]->"
            f"(b:{self._NODE_TABLE} {{id: {self._sql_str(target_id)}}}) "
            f"DELETE r;"
        )
        try:
            self._execute(query)
        except Exception as exc:
            raise StorageError(
                f"Failed to delete relationship '{relationship}' from '{source_id}' to '{target_id}': {exc}"
            ) from exc

    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Dict[str, Any],
    ) -> None:
        existing = self.get_relationship(source_id, target_id, relationship)
        merged = {**existing.get("properties", {}), **(properties or {})}
        rel_type = self._normalize_relationship(relationship)
        query = (
            f"MATCH (a:{self._NODE_TABLE} {{id: {self._sql_str(source_id)}}})"
            f"-[r:{rel_type}]->"
            f"(b:{self._NODE_TABLE} {{id: {self._sql_str(target_id)}}}) "
            f"SET r.properties={self._sql_str(self._to_json(merged))};"
        )
        try:
            self._execute(query)
        except Exception as exc:
            raise StorageError(
                f"Failed to update relationship '{relationship}' from '{source_id}' to '{target_id}': {exc}"
            ) from exc

    def get_relationship(
        self, source_id: str, target_id: str, relationship: str
    ) -> Dict[str, Any]:
        rel_type = self._normalize_relationship(relationship)
        if rel_type not in self._relation_tables:
            raise RelationshipNotFoundError(
                f"Relationship type '{relationship}' does not exist."
            )

        query = (
            f"MATCH (a:{self._NODE_TABLE} {{id: {self._sql_str(source_id)}}})"
            f"-[r:{rel_type}]->"
            f"(b:{self._NODE_TABLE} {{id: {self._sql_str(target_id)}}}) "
            f"RETURN r.properties LIMIT 1;"
        )
        try:
            rows = self._rows(query)
        except Exception as exc:
            raise StorageError(
                f"Failed to fetch relationship '{relationship}' from '{source_id}' to '{target_id}': {exc}"
            ) from exc

        if not rows:
            raise RelationshipNotFoundError(
                f"Relationship '{relationship}' from '{source_id}' to '{target_id}' not found."
            )
        return {
            "type": relationship,
            "properties": self._from_json(rows[0][0], default={}),
        }

    def get_neighbors(
        self,
        node_id: str,
        relationship: Optional[str] = None,
        direction: str = "both",
    ) -> List[Dict[str, Any]]:
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be one of: in, out, both")
        self._ensure_node_exists(node_id)

        if relationship:
            rel_tables = [self._normalize_relationship(relationship)]
        else:
            rel_tables = sorted(self._relation_tables)
        if not rel_tables:
            return []

        neighbors_by_id: Dict[str, Dict[str, Any]] = {}
        try:
            for rel_type in rel_tables:
                if rel_type not in self._relation_tables:
                    continue
                if direction in {"out", "both"}:
                    query = (
                        f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}})"
                        f"-[r:{rel_type}]->(m:{self._NODE_TABLE}) "
                        f"RETURN m.id, m.properties, m.labels;"
                    )
                    for row in self._rows(query):
                        neighbors_by_id[row[0]] = self._row_to_node(row)
                if direction in {"in", "both"}:
                    query = (
                        f"MATCH (m:{self._NODE_TABLE})-[r:{rel_type}]->"
                        f"(n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
                        f"RETURN m.id, m.properties, m.labels;"
                    )
                    for row in self._rows(query):
                        neighbors_by_id[row[0]] = self._row_to_node(row)
        except Exception as exc:
            raise StorageError(f"Failed to get neighbors for '{node_id}': {exc}") from exc

        return list(neighbors_by_id.values())

    def query_nodes(
        self, properties: Dict[str, Any], labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        query = f"MATCH (n:{self._NODE_TABLE}) RETURN n.id, n.properties, n.labels;"
        try:
            rows = self._rows(query)
        except Exception as exc:
            raise StorageError(f"Failed to query nodes: {exc}") from exc

        target_props = properties or {}
        target_labels = set(labels or [])
        matches: List[Dict[str, Any]] = []
        for row in rows:
            node = self._row_to_node(row)
            node_props = node["properties"]
            node_labels = set(node["labels"])
            if not all(node_props.get(k) == v for k, v in target_props.items()):
                continue
            if target_labels and not target_labels.intersection(node_labels):
                continue
            matches.append(node)
        return matches

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        rendered_query = query
        if parameters:
            for key, value in parameters.items():
                rendered_query = rendered_query.replace(
                    f"${key}", self._sql_literal(value)
                )
        try:
            return self._rows(rendered_query)
        except Exception as exc:
            raise StorageError(f"Failed to execute query: {exc}") from exc

    def _ensure_node_table(self) -> None:
        create_query = (
            f"CREATE NODE TABLE IF NOT EXISTS {self._NODE_TABLE} ("
            "id STRING, properties STRING, labels STRING, PRIMARY KEY (id));"
        )
        self._execute(create_query)

    def _ensure_relationship_table(self, rel_type: str) -> None:
        if rel_type in self._relation_tables:
            return
        create_query = (
            f"CREATE REL TABLE IF NOT EXISTS {rel_type} ("
            f"FROM {self._NODE_TABLE} TO {self._NODE_TABLE}, properties STRING);"
        )
        self._execute(create_query)
        self._relation_tables.add(rel_type)

    def _discover_relationship_tables(self) -> None:
        for query in ("CALL show_tables() RETURN *;", "CALL SHOW_TABLES() RETURN *;"):
            try:
                rows = self._rows(query)
            except Exception:
                continue
            for row in rows:
                if len(row) < 2:
                    continue
                table_name = str(row[0])
                table_type = str(row[1]).upper()
                if table_type == "REL":
                    self._relation_tables.add(table_name)
            if rows:
                break

    def _ensure_node_exists(self, node_id: str) -> None:
        if self._node_exists(node_id):
            return
        raise NodeNotFoundError(f"Node with id '{node_id}' not found.")

    def _node_exists(self, node_id: str) -> bool:
        query = (
            f"MATCH (n:{self._NODE_TABLE} {{id: {self._sql_str(node_id)}}}) "
            f"RETURN n.id LIMIT 1;"
        )
        return bool(self._rows(query))

    def _execute(self, query: str) -> None:
        if self._conn is None:
            raise StorageError("Kuzu connection is closed.")
        self._conn.execute(query)

    def _rows(self, query: str) -> List[Any]:
        if self._conn is None:
            raise StorageError("Kuzu connection is closed.")
        result = self._conn.execute(query)
        rows: List[Any] = []
        while result.has_next():
            rows.append(result.get_next())
        return rows

    @staticmethod
    def _normalize_relationship(relationship: str) -> str:
        relation = (relationship or "").strip()
        if not relation:
            raise ValueError("relationship must be a non-empty string")
        normalized = relation.upper().replace(" ", "_").replace("-", "_")
        if not _RELATION_NAME_RE.match(normalized):
            normalized = re.sub(r"[^A-Za-z0-9_]", "_", normalized)
        if not normalized or normalized[0].isdigit():
            normalized = f"REL_{normalized}"
        return normalized

    @staticmethod
    def _sql_str(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _sql_literal(value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return KuzuDatabase._sql_str(value)
        return KuzuDatabase._sql_str(
            json.dumps(value, ensure_ascii=True, sort_keys=True)
        )

    @staticmethod
    def _to_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def _from_json(value: Any, default: Any) -> Any:
        if value is None:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    def _row_to_node(self, row: Any) -> Dict[str, Any]:
        return {
            "id": row[0],
            "properties": self._from_json(row[1], default={}),
            "labels": self._from_json(row[2], default=[]),
        }
