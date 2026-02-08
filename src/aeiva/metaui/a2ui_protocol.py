from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from .capabilities import SUPPORTED_FEATURES, SUPPORTED_PROTOCOL_VERSIONS

A2UI_PROTOCOL_VERSION = "1.0"


class MetaUIComponentPayload(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    props: Dict[str, Any] = Field(default_factory=dict)


class SurfaceComponent(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    component: Dict[str, MetaUIComponentPayload] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_component_wrapper(self) -> "SurfaceComponent":
        if len(self.component) != 1:
            raise ValueError("surface component wrapper must contain exactly one component key")
        return self


class BeginRenderingMessage(BaseModel):
    surfaceId: str = Field(min_length=1, max_length=128)
    root: str = Field(min_length=1, max_length=128)
    catalogId: Optional[str] = Field(default=None, max_length=256)
    sendDataModel: Optional[bool] = None
    styles: Optional[Dict[str, Any]] = None


class SurfaceUpdateMessage(BaseModel):
    surfaceId: str = Field(min_length=1, max_length=128)
    components: List[SurfaceComponent] = Field(default_factory=list)


class DataModelTypedValue(BaseModel):
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
    key: str = Field(min_length=1, max_length=128)


DataModelTypedValue.model_rebuild()


class DataModelUpdateMessage(BaseModel):
    surfaceId: str = Field(min_length=1, max_length=128)
    path: str = Field(default="/", min_length=1, max_length=512)
    contents: List[DataModelContentEntry] = Field(default_factory=list)


class DeleteSurfaceMessage(BaseModel):
    surfaceId: str = Field(min_length=1, max_length=128)


class ServerToClientEnvelope(BaseModel):
    beginRendering: Optional[BeginRenderingMessage] = None
    surfaceUpdate: Optional[SurfaceUpdateMessage] = None
    dataModelUpdate: Optional[DataModelUpdateMessage] = None
    deleteSurface: Optional[DeleteSurfaceMessage] = None

    @model_validator(mode="after")
    def _validate_exactly_one_message(self) -> "ServerToClientEnvelope":
        active = [
            self.beginRendering is not None,
            self.surfaceUpdate is not None,
            self.dataModelUpdate is not None,
            self.deleteSurface is not None,
        ]
        if sum(1 for item in active if item) != 1:
            raise ValueError("ServerToClientEnvelope requires exactly one message variant")
        return self


class CatalogSnapshot(BaseModel):
    catalogId: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=32)
    componentTypes: List[str] = Field(default_factory=list)


class ClientHello(BaseModel):
    type: Literal["hello"] = "hello"
    client_id: Optional[str] = Field(default=None, max_length=128)
    token: Optional[str] = Field(default=None, max_length=256)
    protocol_versions: List[str] = Field(default_factory=list)
    supported_components: List[str] = Field(default_factory=list)
    supported_commands: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)


class HelloAck(BaseModel):
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
    }
