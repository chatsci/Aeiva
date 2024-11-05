from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig


@dataclass
class AzureAISearchConfig(BaseConfig):
    """
    Configuration for Azure Cognitive Search vector database.
    """

    collection_name: str = field(
        default="mem0",
        metadata={"help": "Name of the collection (index name)."}
    )
    service_name: Optional[str] = field(
        default=None,
        metadata={"help": "Azure Cognitive Search service name."}
    )
    api_key: Optional[str] = field(
        default=None,
        metadata={"help": "API key for the Azure Cognitive Search service."}
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Dimension of the embedding vector."}
    )
    use_compression: bool = field(
        default=False,
        metadata={"help": "Whether to use scalar quantization vector compression."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Validate that service_name and api_key are provided
        if not self.service_name or not self.api_key:
            raise ValueError("Both 'service_name' and 'api_key' must be provided.")