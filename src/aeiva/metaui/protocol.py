from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .component_catalog import supported_component_types

SPEC_VERSION = "1.0"
EVENT_VERSION = "1.0"

UI_COMPONENT_TYPES = frozenset(supported_component_types())

COMMAND_TYPES = {
    "create_surface",
    "update_components",
    "update_data_model",
    "delete_surface",
}


def new_ui_id() -> str:
    return f"ui_{uuid4().hex[:12]}"


def new_command_id() -> str:
    return f"cmd_{uuid4().hex[:12]}"


def new_event_id() -> str:
    return f"evt_{uuid4().hex[:12]}"


class MetaUIComponent(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64)
    props: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_type(self) -> "MetaUIComponent":
        if self.type not in UI_COMPONENT_TYPES:
            raise ValueError(
                f"Unsupported component type: {self.type}. Allowed: {sorted(UI_COMPONENT_TYPES)}"
            )
        return self


class MetaUISpec(BaseModel):
    spec_version: str = SPEC_VERSION
    ui_id: str = Field(default_factory=new_ui_id, min_length=4, max_length=128)
    session_id: Optional[str] = Field(default=None, max_length=128)
    title: str = Field(default="MetaUI", min_length=1, max_length=256)
    interaction_mode: Literal["interactive", "preview"] = "interactive"
    components: List[MetaUIComponent] = Field(default_factory=list)
    root: List[str] = Field(default_factory=list)
    state_bindings: Dict[str, Any] = Field(default_factory=dict)
    theme: Dict[str, Any] = Field(default_factory=dict)
    send_data_model: bool = False

    @model_validator(mode="after")
    def _validate_root(self) -> "MetaUISpec":
        if not self.root:
            raise ValueError("MetaUISpec.root must contain at least one component id.")
        component_ids = {component.id for component in self.components}
        for component_id in self.root:
            if component_id not in component_ids:
                raise ValueError(
                    f"Root component id '{component_id}' is missing from components."
                )
        return self


class MetaUICommand(BaseModel):
    command: Literal[
        "create_surface",
        "update_components",
        "update_data_model",
        "delete_surface",
    ]
    command_id: str = Field(default_factory=new_command_id, min_length=4, max_length=128)
    session_id: Optional[str] = Field(default=None, max_length=128)
    ui_id: Optional[str] = Field(default=None, max_length=128)
    payload: Dict[str, Any] = Field(default_factory=dict)
    ts: float = Field(default_factory=lambda: time.time())


class MetaUIEvent(BaseModel):
    event_version: str = EVENT_VERSION
    event_id: str = Field(default_factory=new_event_id, min_length=4, max_length=128)
    ui_id: str = Field(min_length=1, max_length=128)
    session_id: Optional[str] = Field(default=None, max_length=128)
    component_id: Optional[str] = Field(default=None, max_length=128)
    event_type: str = Field(min_length=1, max_length=64)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ts: float = Field(default_factory=lambda: time.time())
