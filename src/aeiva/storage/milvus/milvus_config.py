from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig


@dataclass
class MilvusConfig(BaseConfig):
    """
    Configuration for Milvus vector database.
    """

    uri: str = field(
        default="http://localhost:19530",
        metadata={"help": "Full URL for Milvus server."}
    )
    token: Optional[str] = field(
        default=None,
        metadata={"help": "Token for Milvus server authentication (if required)."}
    )
    collection_name: str = field(
        default="mem0",
        metadata={"help": "Name of the collection."}
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Dimensions of the embedding model."}
    )
    metric_type: str = field(
        default="L2",
        metadata={"help": "Metric type for similarity search (e.g., 'L2', 'IP', 'COSINE')."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Validate metric_type
        valid_metrics = {"L2", "IP", "COSINE", "HAMMING", "JACCARD"}
        if self.metric_type not in valid_metrics:
            raise ValueError(f"Invalid metric_type '{self.metric_type}'. Valid options are {valid_metrics}.")