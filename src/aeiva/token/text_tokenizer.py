# coding=utf-8
#
# Copyright (C) 2023 Bang Liu - All Rights Reserved.
# This source code is licensed under the license found in the LICENSE file
# in the root directory of this source tree.
"""
This module contains the class for a text tokenizer.
"""
from typing import List, Union
from transformers import AutoTokenizer
import tiktoken
import pickle
from base_tokenizer import BaseTokenizer


class TikTokenWrapper(BaseTokenizer):
    """
    A wrapper for tiktoken's Tokenizer to make it compatible with TextTokenizer.
    """

    def __init__(self, tokenizer: str):
        self.tokenizer = tiktoken.get_encoding(tokenizer)

    def encode(self, text: str, **kwargs) -> List[int]:
        tokens = self.tokenizer.encode(text, **kwargs)
        return tokens

    def decode(self, data: List[int], **kwargs) -> str:
        return self.tokenizer.decode(data, **kwargs)


class HuggingFaceWrapper(BaseTokenizer):
    """
    A wrapper for Hugging Face's Tokenizer to make it compatible with TextTokenizer.
    """

    def __init__(self, tokenizer: str):
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer)

    def encode(self, text: str, **kwargs) -> List[int]:
        tokens = self.tokenizer.encode(text, **kwargs)
        return tokens

    def decode(self, data: List[int], **kwargs) -> str:
        return self.tokenizer.decode(data, **kwargs)


class TokenizerFromPickle(BaseTokenizer):
    """
    A wrapper for loading a tokenizer from a pickle file.
    """

    def __init__(self, meta_path: str):
        self.meta_path = meta_path
        self.stoi = None
        self.itos = None
    
    def _load(self):
        if not self.stoi or not self.itos:
            self.meta = pickle.load(open(self.meta_path, 'rb'))
            self.stoi = self.meta.get('stoi')
            self.itos = self.meta.get('itos')

            if not self.stoi or not self.itos:
                raise ValueError(f'Pickle file {self.meta_path} does not contain stoi or itos')
    
    def encode(self, text: str, **kwargs) -> List[int]:
        self._load()
        tokens = [self.stoi.get(c, self.stoi.get('<UNK>')) for c in text]
        return tokens
    
    def decode(self, data: List[int], **kwargs) -> str:
        self._load()
        text = ''.join([self.itos.get(i, '<UNK>') for i in data])
        return text


class TextTokenizer(BaseTokenizer):
    """
    A TextTokenizer that can use a Hugging Face tokenizer, a tiktoken tokenizer or a custom tokenizer.
    """

    def __init__(self, tokenizer: Union[str, TikTokenWrapper, HuggingFaceWrapper, TokenizerFromPickle]):
        if isinstance(tokenizer, str):
            self.tokenizer = HuggingFaceWrapper(tokenizer)
        elif isinstance(tokenizer, (TikTokenWrapper, HuggingFaceWrapper, TokenizerFromPickle)):
            self.tokenizer = tokenizer
        else:
            raise ValueError("tokenizer must be a string, a TikTokenWrapper, a HuggingFaceWrapper, or a TokenizerFromPickle.")

    def encode(self, text: str, **kwargs) -> List[int]:
        tokens = self.tokenizer.encode(text, **kwargs)
        return tokens
    
    def decode(self, data: List[int], **kwargs) -> str:
        return self.tokenizer.decode(data, **kwargs)


if __name__ == '__main__':
    # Test the TextTokenizer
    tokenizer = TextTokenizer('gpt2')
    tokens = tokenizer.encode('Hello, world!')
    print(tokens)
    text = tokenizer.decode(tokens)
    print(text)

    # Test the TikTokenWrapper
    tokenizer = TextTokenizer(TikTokenWrapper('gpt2'))
    tokens = tokenizer.encode('Hello, nice to meet you!', allowed_special={"Hello"})
    print(tokens)
    text = tokenizer.decode(tokens)
    print(text)

    # Test the HuggingFaceWrapper
    tokenizer = TextTokenizer(HuggingFaceWrapper('gpt2'))
    tokens = tokenizer.encode('Hello, nice to meet huggingface!')
    print(tokens)
    text = tokenizer.decode(tokens)
    print(text)

    # Test the TokenizerFromPickle
    tokenizer = TextTokenizer(TokenizerFromPickle('../../../datasets/shakespeare_char/meta.pkl'))
    tokens = tokenizer.encode('Hello, nice to meet you!')
    print(tokens)
    text = tokenizer.decode(tokens)
    print(text)

