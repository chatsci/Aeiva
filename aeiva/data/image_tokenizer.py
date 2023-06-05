#!/usr/bin/env python
# coding=utf-8
"""
This module contains the class for an image tokenizer.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC, abstractmethod
from typing import Union
from PIL import Image
from torchvision import transforms
from torchvision.transforms import InterpolationMode
import torch


# Define constants for image size and normalization values
IMAGE_SIZE = (224, 224)
NORMALIZATION_MEAN = [0.485, 0.456, 0.406]
NORMALIZATION_STD = [0.229, 0.224, 0.225]


class BaseImageTokenizer(ABC):
    """
    Abstract base class for image tokenizers.
    """

    @abstractmethod
    def encode(self, data, **kwargs):
        pass

    @abstractmethod
    def decode(self, data, **kwargs):
        pass


class ImageTokenizer(BaseImageTokenizer):
    """
    A basic ImageTokenizer that takes in an image path and returns a PyTorch tensor.

    This tokenizer applies the following transforms to the image:
    - Resize to IMAGE_SIZE
    - Convert to tensor
    - Normalize with mean=NORMALIZATION_MEAN and std=NORMALIZATION_STD
    """
    def __init__(self):
        self.transform = transforms.Compose([
            transforms.Resize(IMAGE_SIZE, interpolation=InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize(mean=NORMALIZATION_MEAN, std=NORMALIZATION_STD)
        ])

    def encode(self, image_path: str, **kwargs) -> torch.Tensor:
        image = Image.open(image_path).convert("RGB")
        return self.transform(image)

    def decode(self, data: torch.Tensor, **kwargs) -> Image.Image:
        # Inverse normalization
        for t, m, s in zip(data, NORMALIZATION_MEAN, NORMALIZATION_STD):
            t.mul_(s).add_(m)
        # Convert to PIL Image
        return transforms.ToPILImage()(data.cpu())


if __name__ == '__main__':
    # Test the ImageTokenizer
    tokenizer = ImageTokenizer()
    image_path = '../data/sample_img.jpg'  # Replace this with your image path
    tensor = tokenizer.encode(image_path)
    print(tensor.shape)  # Should print torch.Size([3, 224, 224])
    print(tensor)
    image = tokenizer.decode(tensor)
    image.show()
