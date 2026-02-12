from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .capabilities import SUPPORTED_FEATURES, SUPPORTED_PROTOCOL_VERSIONS
from .interaction_contract import get_interaction_contract_snapshot
from .protocol import MetaUISpec

A2UI_PROTOCOL_VERSION = "v0.10"


class SurfaceComponent(BaseModel):
    """
    A2UI v0.10 updateComponents entry.

    Strict shape:
    {
      "id": "...",
      "component": "Button",
      ...component props...
    }
    """

    # Component-specific fields (e.g. Text.text, Button.action) are intentionally
    # top-level in A2UI updateComponents payloads, so we must allow extras here.
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1, max_length=128)
    component: str = Field(min_length=1, max_length=64)

    def as_mapping(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CreateSurfaceMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaceId: str = Field(min_length=1, max_length=128)
    catalogId: str = Field(min_length=1, max_length=256)
    sendDataModel: Optional[bool] = None
    theme: Optional[Dict[str, Any]] = None


class SurfaceUpdateMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaceId: str = Field(min_length=1, max_length=128)
    components: List[SurfaceComponent] = Field(default_factory=list)


class DataModelTypedValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valueString: Optional[str] = None
    valueNumber: Optional[float] = None
    valueBoolean: Optional[bool] = None
    valueMap: Optional[List["DataModelContentEntry"]] = None
    valueList: Optional[List["DataModelTypedValue"]] = None
    valueNull: Optional[bool] = None

    @model_validator(mode="after")
    def _validate_one_value_field(self) -> "DataModelTypedValue":
        active = [
            self.valueString is not None,
            self.valueNumber is not None,
            self.valueBoolean is not None,
            self.valueMap is not None,
            self.valueList is not None,
            self.valueNull is True,
        ]
        if sum(1 for item in active if item) != 1:
            raise ValueError("typed data value must contain exactly one value* field")
        return self


class DataModelContentEntry(DataModelTypedValue):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=128)


DataModelTypedValue.model_rebuild()


class DataModelUpdateMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaceId: str = Field(min_length=1, max_length=128)
    path: str = Field(default="/", min_length=1, max_length=512)
    value: Optional[Any] = None
    contents: List[DataModelContentEntry] = Field(default_factory=list)


class DeleteSurfaceMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaceId: str = Field(min_length=1, max_length=128)


class ServerToClientEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default=A2UI_PROTOCOL_VERSION, min_length=1, max_length=32)
    createSurface: Optional[CreateSurfaceMessage] = None
    updateComponents: Optional[SurfaceUpdateMessage] = None
    updateDataModel: Optional[DataModelUpdateMessage] = None
    deleteSurface: Optional[DeleteSurfaceMessage] = None

    @model_validator(mode="after")
    def _validate_exactly_one_message(self) -> "ServerToClientEnvelope":
        if self.version not in set(SUPPORTED_PROTOCOL_VERSIONS):
            raise ValueError(
                f"Unsupported protocol version '{self.version}'. "
                f"Supported versions: {list(SUPPORTED_PROTOCOL_VERSIONS)}"
            )
        active = [
            self.createSurface is not None,
            self.updateComponents is not None,
            self.updateDataModel is not None,
            self.deleteSurface is not None,
        ]
        if sum(1 for item in active if item) != 1:
            raise ValueError("ServerToClientEnvelope requires exactly one message variant")
        return self


class CatalogSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalogId: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=32)
    componentTypes: List[str] = Field(default_factory=list)


class ClientHello(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["hello"] = "hello"
    client_id: Optional[str] = Field(default=None, max_length=128)
    token: Optional[str] = Field(default=None, max_length=256)
    protocol_versions: List[str] = Field(default_factory=list)
    supported_components: List[str] = Field(default_factory=list)
    supported_commands: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)


class HelloAck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["hello_ack"] = "hello_ack"
    client_id: str = Field(min_length=1, max_length=128)
    protocol: str = Field(min_length=1, max_length=32)
    auto_ui: bool = True
    active_sessions: int = 0
    catalog: Optional[CatalogSnapshot] = None
    negotiated_features: Tuple[str, ...] = ()


def get_protocol_schema_bundle() -> Dict[str, Any]:
    return {
        "version": A2UI_PROTOCOL_VERSION,
        "supported_protocol_versions": list(SUPPORTED_PROTOCOL_VERSIONS),
        "supported_features": list(SUPPORTED_FEATURES),
        "server_to_client": ServerToClientEnvelope.model_json_schema(),
        "client_hello": ClientHello.model_json_schema(),
        "hello_ack": HelloAck.model_json_schema(),
        "catalog_snapshot": CatalogSnapshot.model_json_schema(),
        "metaui_spec": MetaUISpec.model_json_schema(),
        "interaction_contract": get_interaction_contract_snapshot(),
    }
