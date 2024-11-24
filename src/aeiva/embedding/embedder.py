# embedder.py

from typing import Any, List, Union, Optional, Dict
from aeiva.embedding.embedder_config import EmbedderConfig
import litellm
import asyncio


class Embedder:
    """
    Embedder class that uses litellm to generate embeddings.
    Supports both synchronous and asynchronous methods.
    """

    def __init__(self, config: Dict):
        """
        Initialize the Embedder with the provided configuration.

        Args:
            config (EmbedderConfig): Configuration for the Embedder.
        """
        self.config_dict = config
        self.config = EmbedderConfig(
                provider_name=self.config_dict.get('provider_name', 'openai'),
                model_name=self.config_dict.get('model_name', 'text-embedding-ada-002'),
                api_key=self.config_dict.get('api_key')
            )
        self._setup_environment()

    def _setup_environment(self):
        """
        Sets up the environment variables and configurations for litellm.
        """
        if self.config.api_key:
            provider = self.config.provider_name.lower()
            api_key = self.config.api_key

            if provider == "openai":
                litellm.openai_api_key = api_key
            elif provider == "azure":
                litellm.azure_api_key = api_key
            elif provider == "cohere":
                litellm.cohere_api_key = api_key
            elif provider == "huggingface":
                litellm.huggingface_api_key = api_key
            elif provider == "bedrock":
                litellm.bedrock_access_key_id = api_key
                litellm.bedrock_secret_access_key = self.config.additional_params.get("secret_access_key", "")
                litellm.bedrock_region_name = self.config.additional_params.get("region_name", "")
            elif provider == "vertex_ai":
                litellm.vertex_api_key = api_key
            elif provider == "voyage":
                litellm.voyage_api_key = api_key
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        if self.config.api_base:
            litellm.api_base = self.config.api_base

    def embed(self, input_data: Union[str, List[str]], **kwargs) -> Any:
        """
        Synchronously generate embeddings for the input data.

        Args:
            input_data (Union[str, List[str]]): The text or list of texts to embed.
            **kwargs: Additional parameters for the embedding function.

        Returns:
            Any: The embedding result.
        """
        params = {
            'model': self._get_full_model_name(),
            'input': input_data,
            **self.config.additional_params,
            **kwargs
        }

        response = litellm.embedding(**params)
        return response

    async def aembed(self, input_data: Union[str, List[str]], **kwargs) -> Any:
        """
        Asynchronously generate embeddings for the input data.

        Args:
            input_data (Union[str, List[str]]): The text or list of texts to embed.
            **kwargs: Additional parameters for the embedding function.

        Returns:
            Any: The embedding result.
        """
        params = {
            'model': self._get_full_model_name(),
            'input': input_data,
            **self.config.additional_params,
            **kwargs
        }

        response = await litellm.aembedding(**params)
        return response

    def _get_full_model_name(self) -> str:
        """
        Constructs the full model name based on the provider.

        Returns:
            str: The full model name.
        """
        provider = self.config.provider_name.lower()
        model_name = self.config.model_name

        if provider == 'openai':
            return model_name
        elif provider == 'azure':
            return f'azure/{model_name}'
        elif provider == 'huggingface':
            return f'huggingface/{model_name}'
        elif provider == 'cohere':
            return model_name
        elif provider == 'vertex_ai':
            return f'vertex_ai/{model_name}'
        elif provider == 'bedrock':
            return f'bedrock/{model_name}'
        elif provider == 'voyage':
            return f'voyage/{model_name}'
        else:
            return model_name  # Default case