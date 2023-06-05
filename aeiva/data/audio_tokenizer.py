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
import torch
import soundfile as sf
import numpy as np
from transformers import AutoTokenizer, AutoFeatureExtractor, AutoModelForCTC
from pydub import AudioSegment



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

    def decode(self, data: np.ndarray, filepath: str, **kwargs) -> None:
        sf.write(filepath, data, self.sr, **kwargs)


class HuggingFaceWrapper:
    """
    A wrapper for Hugging Face's Tokenizer to make it compatible with AudioTokenizer.
    The HuggingFaceWrapper works by extracting features from the input audio using Hugging Face's Feature Extractor,
    and then converting each token into its corresponding ID using the model's logits.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = AutoModelForCTC.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)

    def encode(self, filepath: str, **kwargs):
        audio = AudioSegment.from_wav(filepath)
        # Check if the audio is stereo
        if audio.channels == 2:
            # Convert to mono
            audio = audio.set_channels(1)
        audio.export(filepath, format="wav")

        audio_data, _ = sf.read(filepath)
        input_values = self.feature_extractor(audio_data, return_tensors="pt").input_values
        logits = self.model(input_values).logits[0]
        pred_ids = torch.argmax(logits, axis=-1)
        return pred_ids

    def decode(self, pred_ids, **kwargs):
        time_offset = self.model.config.inputs_to_logits_ratio / self.feature_extractor.sampling_rate
        outputs = self.tokenizer.decode(pred_ids, output_word_offsets=True)
        word_offsets = [
            {
                "word": d["word"],
                "start_time": round(d["start_offset"] * time_offset, 2),
                "end_time": round(d["end_offset"] * time_offset, 2),
            }
            for d in outputs.word_offsets
        ]
        words = " ".join([d["word"] for d in word_offsets])
        print(words)
        return word_offsets


class AudioTokenizer(BaseTokenizer):
    """
    Create an AudioTokenizer that can use either a librosa, or Hugging Face's Audio Tokenizer.

    Args:
        tokenizer (Union[str, LibrosaWrapper, HuggingFaceWrapper]): The tokenizer to use.
            - If str: The model name or path of a Hugging Face tokenizer
            - If LibrosaWrapper: A wrapper for Librosa's audio processing methods.
            - If HuggingFaceWrapper: A wrapper for Hugging Face's Wav2Vec2Tokenizer.

    Raises:
        ValueError: If the `tokenizer` argument is not a str, a LibrosaWrapper, or a HuggingFaceWrapper.
    """
    def __init__(self, tokenizer: Union[str, LibrosaWrapper, HuggingFaceWrapper]):
        if isinstance(tokenizer, str):
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer)
        elif isinstance(tokenizer, LibrosaWrapper):
            self.tokenizer = tokenizer
        elif isinstance(tokenizer, HuggingFaceWrapper):
            self.tokenizer = tokenizer
        else:
            raise ValueError("tokenizer must be a string, a LibrosaWrapper, or a HuggingFaceWrapper.")

    def encode(self, filepath: str, **kwargs):
        tokens = self.tokenizer.encode(filepath, **kwargs)
        return tokens

    def decode(self, data, **kwargs):
        return self.tokenizer.decode(data, **kwargs)


if __name__ == '__main__':
    # Test the AudioTokenizer with LibrosaWrapper
    tokenizer = AudioTokenizer(LibrosaWrapper(22050))
    tokens = tokenizer.encode('../data/sample_audio.wav')
    print(tokens.shape)
    tokenizer.decode(tokens, filepath='../data/reconstructed_sample_audio.wav')

    # Test the AudioTokenizer with HuggingFaceWrapper
    tokenizer = AudioTokenizer(HuggingFaceWrapper("facebook/wav2vec2-base-960h"))
    tokens = tokenizer.encode('../data/sample_audio.wav')
    print(tokens)
    text = tokenizer.decode(tokens, skip_special_tokens=True)
    print(text)
