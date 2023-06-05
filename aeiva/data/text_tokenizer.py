#!/usr/bin/env python
# coding=utf-8
from abc import ABC, abstractmethod
from typing import List, Union
from transformers import PreTrainedTokenizer
from tiktoken import Tokenizer
from tiktoken.models import Model


class BaseTokenizer(ABC):
    """
    Abstract base class for tokenizers.
    """

    @abstractmethod
    def tokenize(self, data):
        """
        Method to convert data into tokens. Should be implemented by all subclasses.
        """
        pass


class TextTokenizer(BaseTokenizer):
    """
    Create a TextTokenizer that can use either a Hugging Face tokenizer or a custom tokenizer.

    If a string is passed as the tokenizer, the TextTokenizer will use a Hugging Face tokenizer of
    the specified model. If an instance of a tokenizer is passed, it will be used directly.

    Args:
        tokenizer (Union[str, PreTrainedTokenizer]): The tokenizer to use.
            - If str: The model name or path of a Hugging Face tokenizer to use.
            - If PreTrainedTokenizer: A tokenizer instance that has a `__call__` method to tokenize text.

    Raises:
        ValueError: If the `tokenizer` argument is not a str or a PreTrainedTokenizer instance.
    """
    def __init__(self, tokenizer: Union[str, PreTrainedTokenizer]):
        if isinstance(tokenizer, str):
            self.tokenizer = PreTrainedTokenizer.from_pretrained(tokenizer)
        elif isinstance(tokenizer, PreTrainedTokenizer):
            self.tokenizer = tokenizer
        else:
            raise ValueError("tokenizer must be a string or a PreTrainedTokenizer instance")

    def tokenize(self, text: str) -> List[int]:
        """
        Tokenizes a piece of text.

        Args:
            text (str): The text to tokenize.

        Returns:
            tokens (List[int]): The tokenized text as a list of token ids.
        """
        tokens = self.tokenizer(text, truncation=True, padding='longest', return_tensors='pt')
        return tokens['input_ids']


class TikTokenWrapper:
    """
    A wrapper for tiktoken's Tokenizer to make it compatible with TextTokenizer.

    The TikTokenWrapper works by tokenizing the input text using tiktoken's Tokenizer,
    and then converting each token into its corresponding ID using a Model from tiktoken.models.

    Note: The TikTokenWrapper does not handle out-of-vocabulary tokens or special tokens like start-of-sequence 
    or end-of-sequence tokens. If you need to handle these types of tokens, you would need to modify 
    the TikTokenWrapper accordingly.
    """
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.model = Model()

    def __call__(self, text):
        tokens = self.tokenizer.tokenize(text)
        token_ids = [self.model.encoder[t] for t in tokens if t in self.model.encoder]
        return token_ids


if __name__ == '__main__':
    # Test the TextTokenizer
    tokenizer = TextTokenizer('gpt2-medium')
    tokens = tokenizer.tokenize('Hello, world!')
    print(tokens)

    # Test the TikTokenWrapper
    tokenizer = TextTokenizer(TikTokenWrapper())
    tokens = tokenizer.tokenize('Hello, world!')
    print(tokens)
