#!/usr/bin/env python
# coding=utf-8
"""
This module contains the class for an audio tokenizer.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC, abstractmethod
from typing import List, Union
import librosa
import numpy as np
from transformers import Wav2Vec2Tokenizer
from auditok import ADSFactory, AudioRegion


class BaseTokenizer(ABC):
    """
    Abstract base class for tokenizers.
    """
    @abstractmethod
    def encode(self, data, **kwargs):
        pass

    @abstractmethod
    def decode(self, data, **kwargs):
        pass


class LibrosaWrapper:
    """
    A wrapper for librosa to make it compatible with AudioTokenizer.

    The LibrosaWrapper works by loading the input audio file using librosa's load method,
    and then converting the loaded audio file into a time-series representation.
    """
    def __init__(self, sr: int):
        self.sr = sr

    def encode(self, filepath: str, **kwargs) -> np.ndarray:
        y, _ = librosa.load(filepath, sr=self.sr, **kwargs)
        return y

    def decode(self, data: np.ndarray, **kwargs) -> None:
        librosa.output.write_wav('reconstructed.wav', data, self.sr, **kwargs)


class HuggingFaceWrapper:
    """
    A wrapper for Hugging Face's Wav2Vec2Tokenizer to make it compatible with AudioTokenizer.

    The HuggingFaceWrapper works by tokenizing the input audio file using Hugging Face's Wav2Vec2Tokenizer,
    and then converting each token into its corresponding ID using the Tokenizer's vocabulary.
    """
    def __init__(self, tokenizer: str):
        self.tokenizer = Wav2Vec2Tokenizer.from_pretrained(tokenizer)

    def encode(self, filepath: str, **kwargs):
        tokens = self.tokenizer(filepath, **kwargs)
        return tokens

    def decode(self, data, **kwargs):
        return self.tokenizer.decode(data, **kwargs)


class AuditokWrapper:
    """
    A wrapper for Auditok's audio segmentation tool to make it compatible with AudioTokenizer.

    The AuditokWrapper works by segmenting the input audio file using Auditok's ADSFactory and AudioRegion,
    and then converting each segment into a time-series representation.
    """
    def __init__(self, min_dur: float, max_dur: float):
        self.min_dur = min_dur
        self.max_dur = max_dur

    def encode(self, filepath: str, **kwargs):
        asource = ADSFactory.ads(filepath=filepath)
        region = AudioRegion.load(asource)
        segments = region.split_and_plot(self.min_dur, self.max_dur)
        return segments

    def decode(self, data, **kwargs):
        pass  # Auditok doesn't provide a straightforward way to convert segments back into an audio file


class AudioTokenizer(BaseTokenizer):
    """
    Create an AudioTokenizer that can use either a librosa, Hugging Face's Wav2Vec2Tokenizer, or Auditok.

    Args:
        tokenizer (Union[str, LibrosaWrapper, HuggingFaceWrapper, AuditokWrapper]): The tokenizer to use.
            - If str: The model name or path of a Hugging Face tokenizer
            - If LibrosaWrapper: A wrapper for Librosa's audio processing methods.
            - If HuggingFaceWrapper: A wrapper for Hugging Face's Wav2Vec2Tokenizer.
            - If AuditokWrapper: A wrapper for Auditok's audio segmentation methods.

    Raises:
        ValueError: If the `tokenizer` argument is not a str, LibrosaWrapper, HuggingFaceWrapper, or AuditokWrapper.
    """
    def __init__(self, tokenizer: Union[str, LibrosaWrapper, HuggingFaceWrapper, AuditokWrapper]):
        if isinstance(tokenizer, str):
            self.tokenizer = Wav2Vec2Tokenizer.from_pretrained(tokenizer)
        elif isinstance(tokenizer, LibrosaWrapper):
            self.tokenizer = tokenizer
        elif isinstance(tokenizer, HuggingFaceWrapper):
            self.tokenizer = tokenizer
        elif isinstance(tokenizer, AuditokWrapper):
            self.tokenizer = tokenizer
        else:
            raise ValueError("tokenizer must be a string, a LibrosaWrapper, a HuggingFaceWrapper, or an AuditokWrapper.")

    def encode(self, filepath: str, **kwargs):
        tokens = self.tokenizer.encode(filepath, **kwargs)
        return tokens

    def decode(self, data, **kwargs):
        return self.tokenizer.decode(data, **kwargs)


if __name__ == '__main__':
    # Test the AudioTokenizer with LibrosaWrapper
    tokenizer = AudioTokenizer(LibrosaWrapper(22050))
    tokens = tokenizer.encode('../data/example.wav')
    print(tokens.shape)
    tokenizer.decode(tokens)

    # Test the AudioTokenizer with HuggingFaceWrapper
    tokenizer = AudioTokenizer(HuggingFaceWrapper('facebook/wav2vec2-base'))
    tokens = tokenizer.encode('../data/example.wav')
    print(tokens)
    text = tokenizer.decode(tokens.input_values, skip_special_tokens=True)
    print(text)

    # Test the AudioTokenizer with AuditokWrapper
    tokenizer = AudioTokenizer(AuditokWrapper(0.1, 0.3))
    segments = tokenizer.encode('../data/example.wav')
    print([segment.shape for segment in segments])
