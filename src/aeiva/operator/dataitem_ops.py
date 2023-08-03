#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the data item processing functions.

For a data item processing function, it takes a data example (a dict) as input
and return a processed data example.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-11

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
import os
import torch
import whisper
import cv2
import PIL
from PIL import Image
import moviepy.editor as mp
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize
from aeiva.util.token_utils import pad_or_truncate_tokens
from aeiva.util.sample_utils import draw_samples
from aeiva.prompt import INSTRUCTION_TUNING_PROMPT_COMPONENTS
from aeiva.common.constants import OPENAI_CLIP_MEAN, OPENAI_CLIP_STD
try:
    from torchvision.transforms import InterpolationMode
    BICUBIC = InterpolationMode.BICUBIC
except ImportError:
    BICUBIC = Image.BICUBIC

N_PX = 224  # image width and height


def _format_text_for_instruction_tuning(instruction_text=None, input_text=None, response_text=None):
    """Format text for prompt.
    """
    assert isinstance(instruction_text, (str, type(None))), "Instruction text must be a string or None"
    assert isinstance(input_text, (str, type(None))), "Input text must be a string or None"
    assert isinstance(response_text, (str, type(None))), "Response text must be a string or None"

    formatted_text = INSTRUCTION_TUNING_PROMPT_COMPONENTS["task_description"]
    if instruction_text:
        formatted_text += INSTRUCTION_TUNING_PROMPT_COMPONENTS["instruction"].format(instruction_text)
    if input_text:
        formatted_text += INSTRUCTION_TUNING_PROMPT_COMPONENTS["input"].format(input_text)
    if response_text:
        formatted_text += INSTRUCTION_TUNING_PROMPT_COMPONENTS["response"].format(response_text)
    else:
        formatted_text += INSTRUCTION_TUNING_PROMPT_COMPONENTS["no_response"]

    return formatted_text


def tokenize_and_label_text_for_instruction_tuning(example, tokenizer, max_length, ignore_id):
    instruction_text = example['instruction']
    input_text = example['input']
    response_text = example['output']

    # Format the text without output.
    prompt_without_output = _format_text_for_instruction_tuning(instruction_text, input_text, None)
    # Tokenize the formatted_text
    # if we use llama tokenizer, for each item it will looks like:
    #  {'input_ids': [1, 5796, 28826, 338, 263, 282, 335], 'token_type_ids': [0, 0, 0, 0, 0, 0, 0], 'attention_mask': [1, 1, 1, 1, 1, 1, 1]}
    # but if we use .encode function, only the input_ids will be returned.
    prompt_without_output_tokens = tokenizer.encode(prompt_without_output)

    # Append the output to the formatted text.
    prompt_with_output = _format_text_for_instruction_tuning(instruction_text, input_text, response_text)
    tokenized_result = tokenizer(prompt_with_output, max_length=max_length, padding='max_length', truncation=True)
    prompt_with_output_tokens = pad_or_truncate_tokens(tokenized_result['input_ids'], max_length, tokenizer.pad_token_id)

    # Create the labels.
    # - For the prefix part (everything up to the answer), labels are filled with ignore_id.
    # - For the answer part, labels are the tokens of the answer.
    # ignore_id is used to ignore the tokens that are part of the prompt or question when calculating the loss. 
    # We only want to calculate the loss for the part of the output sequence that corresponds to the answer.
    prefix_length = len(prompt_without_output_tokens) - 1
    labels = [ignore_id] * prefix_length + prompt_with_output_tokens[prefix_length:]
    labels = pad_or_truncate_tokens(labels, max_length, ignore_id)
    # We shall make the padded part as ignore_id as well. 
    labels = [(l if l != tokenizer.pad_token_id else ignore_id) for l in labels]

    result = {
        'text': prompt_with_output,
        'text_token_ids': prompt_with_output_tokens,
        'attention_mask': tokenized_result['attention_mask'],
        'labels': labels
    }
    example.update(result)

    return example


def _transform_image(image: PIL.Image, n_pixel=N_PX):
    """A specific way to normalize images or video frames for our model."""
    preprocess = Compose([
        Resize(n_pixel, interpolation=BICUBIC),        # Resize the image
        CenterCrop(n_pixel),                           # Crop the center of the image
        lambda img: img.convert("RGB"),                # Convert the image to RGB
        ToTensor(),                                    # Convert the image to a PyTorch tensor
        Normalize(OPENAI_CLIP_MEAN, OPENAI_CLIP_STD)   # Normalize the image
    ])
    processed_image = preprocess(image)
    return processed_image


def get_transformed_image(example, image_dir):
    image_name = example['image']
    if image_name is None:
        transformed_image = torch.zeros(1, 3, 224, 224)
    else:
        image_path = os.path.join(image_dir, image_name)
        transformed_image = _transform_image(Image.open(image_path))
        transformed_image = transformed_image.unsqueeze(0)
    example['transformed_image'] = transformed_image
    return example


def _naming_extracted_video_frame(video_name, frame_idx):
    """We automatically get output frame path based on the video name and frame index."""
    return '{}_{}.jpg'.format(video_name, str(frame_idx))


def _naming_extracted_video_audio(video_name):
    return '{}.wav'.format(video_name)


def _generate_evenly_spaced_frame_indices(total_frames: int, num_indices: int = 6) -> list:
    """
    Function to generate a list of indices for frames evenly spaced across the total number of frames,
    always including the last frame. Useful for selecting a subset of frames at regular intervals from a video or audio file.

    Args:
        total_frames (int): The total number of frames in the video or audio file.
        num_indices (int): The number of indices to generate. Defaults to 6.

    Returns:
        list: A list of frame indices.

    Example usage:
    ----------------
    # Suppose we have a video with 120 frames, and we want to select 6 frames at regular intervals.
    frame_indices = generate_evenly_spaced_frame_indices(total_frames=120, num_indices=6)
    print(frame_indices)  # Outputs: [0, 20, 40, 60, 80, 119]
    """
    interval = total_frames // num_indices

    frame_indices = [i * interval for i in range(num_indices)]
    
    # Ensure that none of the indices exceed the total number of frames.
    frame_indices = [min(index, total_frames - 1) for index in frame_indices]

    # Always include the last frame.
    frame_indices[-1] = total_frames - 1

    return frame_indices


def _sample_frames_from_video(input_video_path, output_frames_dir, num_frames):
    video_name = os.path.basename(input_video_path)
    cam = cv2.VideoCapture(input_video_path)

    # frame
    all_frames = []
    while (True):
        # reading from frame
        is_successful, frame = cam.read()
        if is_successful:
            all_frames.append(frame)
        else:
            break
    if len(all_frames) == 0:
        print(f'No frames found in video file {input_video_path}, skipping.')
        return None

    num_total_video_frames = len(all_frames)
    if num_total_video_frames >= num_frames:
        frame_indices = _generate_evenly_spaced_frame_indices(num_total_video_frames, num_frames)
    else:
        frame_indices = sorted(draw_samples([i for i in range(len(all_frames))], num_frames))

    # Create output frame paths for each sampled frame
    output_frame_paths = [os.path.join(output_frames_dir, _naming_extracted_video_frame(video_name, idx)) for idx in frame_indices]

    # Check if all the frames are already extracted, only extract if any is missing
    if not all(os.path.exists(path) for path in output_frame_paths):
        # Get sampled frames from the original frames list
        sampled_frames = [all_frames[i] for i in frame_indices]
        for frame_idx, frame in enumerate(sampled_frames):
            cv2.imwrite(output_frame_paths[frame_idx], frame)
    else:
        print(f'All frames already extracted from video file {input_video_path}, skipping.')

    # Release all space and windows once done
    cam.release()
    cv2.destroyAllWindows()

    return frame_indices


def sample_frames_from_video(example: dict, num_frames: int, video_dir: str, frame_dir: str) -> dict:
    if example['video'] is None:
        example["sampled_video_frame_indices"] = None
        return example
    video_name = example['video']
    input_video_path = os.path.join(video_dir, video_name)
    frame_indices = _sample_frames_from_video(input_video_path, frame_dir, num_frames)
    example["sampled_video_frame_indices"] = frame_indices
    return example


def _extract_audio_from_video(input_video_path, output_audio_path):
    clip = mp.VideoFileClip(input_video_path)
    clip.audio.write_audiofile(output_audio_path)
    clip.close()


def extract_audio_from_video(example: dict, video_dir, audio_dir: str) -> dict:
    if example['video'] is None:
        return example
    video_name = example['video']
    audio_name = _naming_extracted_video_audio(video_name)
    example['audio'] = audio_name
    input_video_path = os.path.join(video_dir, video_name)
    output_audio_path = os.path.join(audio_dir, audio_name)
    if os.path.exists(output_audio_path):
        print(f'Audio {output_audio_path} exists.')
        return example
    _extract_audio_from_video(input_video_path, output_audio_path)
    return example


def _load_video_frames(frame_dir, video_name, frame_indices):   #!!!! to revise
    all_video_frames = []
    for frame_idx in frame_indices:
        if video_name == None:
            frame = torch.zeros(1, 3, 224, 224)  # empty frame
        else:
            frame = _transform_image(
                Image.open(os.path.join(frame_dir, _naming_extracted_video_frame(video_name, frame_idx)))
            )
            frame = frame.unsqueeze(0)
        all_video_frames.append(frame)
    all_video_frames = torch.cat(all_video_frames, dim=0).unsqueeze(0)
    return all_video_frames


def load_video_frames(example, frame_dir, num_frames):
    video_name = example["video"]
    if video_name is None:
        frame_indices = [i for i in range(1, num_frames + 1)]  #!! if not video, we generate empty frames. So we need frame_indices. We may change later.
    else:
        sampled_frame_indices = example["sampled_video_frame_indices"]
        frame_indices = _generate_evenly_spaced_frame_indices(len(sampled_frame_indices), num_frames)
        frame_indices = [sampled_frame_indices[i] for i in frame_indices]  # NOTE: we sample the second time when load frames for model input
    example["video_frames"] = _load_video_frames(frame_dir, video_name, frame_indices)  #!!! one potential bug: what if the len(frame_indices) is not equal to num_frames?
    return example


def _get_audio_mels(audio_path):
    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio_path)
    audio = whisper.pad_or_trim(audio)
    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio)
    mel = mel.unsqueeze(0)
    # audio_features = model.embed_audio(mel.unsqueeze(0)).squeeze()
    return mel


def get_audio_mels(example, audio_dir):
    audio_name = example['audio']
    if audio_name is None:
        mel = torch.zeros(1, 80, 3000)  #!!!!
    else:
        audio_path = os.path.join(audio_dir, audio_name)
        mel = _get_audio_mels(audio_path)
    example['audio_mels'] = mel
    return example
