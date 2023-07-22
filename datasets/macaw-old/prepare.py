#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script illustrates how to prepare the Macaw multimodal alignment dataset.
Reference: https://github.com/lyuchenyang/Macaw-LLM/blob/main/preprocess_data.py
@Author: Bang Liu
@Date: 2023-06-19
"""
# OBJECTIVE: a prepare.py script is used to turn "raw_dataset" into "formatted_dataset".
#     - raw_dataset: the raw dataset downloaded from the Internet, e.g., COCO, AVSD, VQA, etc.
#     - formatted_dataset: the formatted dataset that can be used by DataLoaders and turn into tensors.
#         We can use a dictionary to represent a formatted dataset. For example, for the multimodal alignment dataset,
#         we can use a dictionary to represent a formatted dataset, where the keys are the names of the modalities,
#         and the values are the corresponding ids of different modalities.
#
# CODE ARCHITECTURE: the overall architecture of preparing the multimodal alignment dataset is as follows:
#     1. Collect and create <id, path> mapping for visual modalities (e.g., images, videos, etc.) and save them to files.
#         This aims to help storing the visual modalities in a more efficient way. By representing them as ids, we can
#         save a lot of disk space. Later, we can retrieve the visual modalities by using the <id, path> mapping.
#     2. Unify the format of different datasets. For example, for the multimodal alignment dataset, we need write a 
#         '_format_XXX_dataset(file_paths)' function for each XXX dataset to turn the raw dataset into a formatted dataset.
#         Each formatted dataset is a list of dictionaries, where each dictionary represents a sample. If we have more datasets,
#         we can write more '_format_XXX_dataset(file_paths)' functions to turn them into formatted datasets. Then we combine them
#         by a '_format_mm_dataset(file_paths, dataset_name)' function.
#     3. Preprocess formatted multimodal dataset: different datasets may have different fields in their data sample dictionaries.
#         The preprocess function aims to unify the fields of different datasets. See '_preprocess_mm_dataset_examples' function.
#     4. Lastly, we may want to merge and sample different datasets to create a new dataset.
#         Overall, the prepare process is "unify format (turn into a list of dict samples) -> unify fields (preprocess) -> merge and sample".
#
# PREPARATION: before running this script, you need to do the following:
#     0: Create folders: in the current folder of this script, create  './avsd/', './coco/', './vqa/';
#     1. Download datasets:
#         - Download the COCO image dataset (2014 Train images [83K/13GB], 2014 Val images [41K/6GB])
#             from: https://cocodataset.org/#download, unzip and put images into 'coco/train2014/', 'coco/val2014';
#         - Download the Macaw dataset: 
#             https://github.com/lyuchenyang/Macaw-LLM/blob/main/data/generated_examples_coco.json,
#             https://github.com/lyuchenyang/Macaw-LLM/blob/main/data/generated_examples_avsd.json,
#             put them in the current folder './';
#         - Download the Charades video dataset (Data (scaled to 480p, 13 GB)) from: 
#             https://prior.allenai.org/projects/charades, unzip (Charades_v1_480/), move all the videos 
#             from 'Charades_v1_480/' to './avsd/videos/'.
#         - Download the vqa dataset: from https://visualqa.org/download.html download 
#             "Training annotations 2017 v2.0*", "Validation annotations 2017 v2.0*", 
#             "Training questions 2017 v2.0*", "Validation questions 2017 v2.0*". 
#             Put them in "./vqa/" and unzip.
#         - Download AVSD dataset: from https://video-dialog.com/ download AVSD Dataset (4 files),
#             put them into "./avsd/".
#
# OUTPUT: what we get after running this script:
#     - raw datasets: downloaded from different sources
#     - formatted datasets: they will be formatted into a list of dictionaries, where each dictionary represents a sample.
#     - tokenizer: the tokenizer used to tokenize the text data.
#     - <id, path> mapping for visual modalities: we use <id, path> mapping to store the visual modalities in a more efficient way.
# 
# TODO: to further improve the code, I want to:
#     - move around constants and functions to make the code more readable;
#     - revise to unify file names;
#     - output file information in functions.
#
# NOTE: You can expand the dataset by getting more multimodal datasets and generate alignment datasets using methods similar to the ones used in the Macaw paper.
#   You can also improve the way to generate better alignment datasets.


import os
import sys
import numpy as np
import moviepy.editor as mp
import cv2
import json
import pickle
import codecs
import random
import torch
from os import listdir
from os.path import join
from tqdm import tqdm
from transformers import AutoTokenizer


os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"  # NOTE: This is just a workarouond. Ensure a single OpenMP runtime is linked is the best solution.

torch.random.manual_seed(0)

IGNORE_INDEX = -100
DEFAULT_PAD_TOKEN = "[PAD]"
DEFAULT_EOS_TOKEN = "</s>"
DEFAULT_BOS_TOKEN = "<s>"
DEFAULT_UNK_TOKEN = "<unk>"
MAX_LENGTH = 256

NUM_RANDOM_VQA_SAMPLES = 60000  # number of random samples to use from VQA dataset
NUM_RANDOM_MERGED_SAMPLES = 50000  # number of random samples to use from the final merged train dataset
MAX_NUM_SAMPLES_PER_DATASET = sys.maxsize  # max number of samples to preprocess for each dataset: vqa, alpaca, avsd

MAX_NUM_RANDOM_DEBUG_SAMPLES = 10  # when debugging, only preprocess a few random samples for each dataset
NUM_RANDOM_MERGED_DEBUG_SAMPLES = 5  # when debugging, only sample a few random samples from the final merged dataset as train dataset

PROMPT_DICT = {
    "task_description": (
        "Below is an instruction that describes a task, with or without input. "
        "Write a response that appropriately completes the request.\n\n"
    ),
    "instruction": "### Instruction:\n{}\n\n",
    "input": "### Input:\n{}\n\n",
    "response": "### Response:\n{}\n\n",
    "no_response": "### Response:\n\n",
}


def _format_text(instruction_text=None, input_text=None, response_text=None):
    """Format text for prompt.
    """
    assert isinstance(instruction_text, (str, type(None))), "Instruction text must be a string or None"
    assert isinstance(input_text, (str, type(None))), "Input text must be a string or None"
    assert isinstance(response_text, (str, type(None))), "Response text must be a string or None"

    formatted_text = PROMPT_DICT["task_description"]

    if instruction_text:
        formatted_text += PROMPT_DICT["instruction"].format(instruction_text)

    if input_text:
        formatted_text += PROMPT_DICT["input"].format(input_text)

    if response_text:
        formatted_text += PROMPT_DICT["response"].format(response_text)
    else:
        formatted_text += PROMPT_DICT["no_response"]

    return formatted_text


def prettyformat_json(file_path, output_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)


def load_json(file_path):
    with codecs.open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def dump_json(data, file_path):
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def draw_samples(input_list, sample_ratio_or_num_samples):
    """ Draw samples from a list.
    """
    num_samples = sample_ratio_or_num_samples if sample_ratio_or_num_samples > 1 else int(sample_ratio_or_num_samples * len(input_list))

    if num_samples > len(input_list):
        sampled_indices = np.random.choice(len(input_list), num_samples, replace=True)
    else:
        sampled_indices = np.random.choice(len(input_list), num_samples, replace=False)

    sampled_input = [input_list[i] for i in sampled_indices]

    return sampled_input


def is_video_file(filepath):
    video_file_extensions = ['.mp4', '.avi', '.mov', '.flv', '.mkv', '.wmv']
    _, extension = os.path.splitext(filepath)
    is_video = extension.lower() in video_file_extensions
    return is_video


def extract_audios_from_videos_dir(videos_folder_path, output_folder_path):
    """ Extract audio from videos.

    Args:
        videos_folder_path (str): The path to the folder containing videos.
        output_folder_path (str): The path to the folder to save the extracted audio.

    Returns:
        None
    """
    video_files = [f for f in listdir(videos_folder_path) if is_video_file(join(videos_folder_path, f))]

    for f in tqdm(video_files):
        video_path = join(videos_folder_path, f)
        clip = mp.VideoFileClip(video_path)
        clip.audio.write_audiofile(join(output_folder_path, '{}.wav'.format(f)))
        clip.close()


def sample_frames_from_videos_dir(videos_folder_path, output_folder_path, frames_per_video=120):
    """ Sample frames from videos.

    Args:
        videos_folder_path (str): The path to the folder containing videos.
        output_folder_path (str): The path to the folder to save the sampled frames.

    Returns:
        None
    """
    video_files = [f for f in listdir(videos_folder_path) if is_video_file(join(videos_folder_path, f))]

    for f in tqdm(video_files):
        # read the video from specified path
        cam = cv2.VideoCapture(join(videos_folder_path, f))

        # frame
        all_frames = []
        while (True):
            # reading from frame
            is_successful, frame = cam.read()
            if is_successful:
                all_frames.append(frame)
            else:
                break
        if not all_frames:
            print(f'No frames found in video file {f}, skipping.')
            continue

        lens = len(all_frames)
        if lens >= frames_per_video:
            interval = lens // frames_per_video
            frame_ind = [i * interval for i in range(frames_per_video)]
            for i in range(len(frame_ind)):
                if frame_ind[i] >= lens:
                    frame_ind[i] = lens - 1
            frame_ind[-1] = lens - 1
            sampled_frames = [all_frames[i] for i in frame_ind]
        else:
            sampled_frames = sorted(draw_samples([i for i in range(len(all_frames))], frames_per_video))
            sampled_frames = [all_frames[i] for i in sampled_frames]

        for ind, frame in enumerate(sampled_frames):
            cv2.imwrite(join(output_folder_path, '{}_{}.jpg'.format(f, str(ind))), frame)

        # Release all space and windows once done
        cam.release()
        cv2.destroyAllWindows()


def _get_image_names_of_coco2014dataset_for_vqadataset(vqadataset_path):
    """ This function aims to get the image name of coco2014 dataset from vqa dataset.
    
    coco2014 dataset: can be downloaded from https://cocodataset.org/#download. 
    We used the 2014 Train images [83K/13GB] and 2014 Val images [41K/6GB].
    After unzip, we get train2014/ and val2014/.
    vqa dataset: can be downloaded from https://visualqa.org/download.html.
    We used the Training annotations 2017 v2.0*, Validation annotations 2017 v2.0*,
    Training questions 2017 v2.0*, and Validation questions 2017 v2.0*. After unzip,
    we get v2_mscoco_train2014_annotations.json and v2_mscoco_val2014_annotations.json.

    Args:
        vqadataset_path (str): the path of vqa dataset.

    Returns:
        all_image_names (list): the image names of coco2014 dataset.

    Example usage:
        all_image_names = _get_image_names_of_coco2014dataset_for_vqadataset('vqa/v2_mscoco_train2014_annotations.json')
    """
    all_image_names = []
    all_examples = load_json(vqadataset_path)['annotations']

    for idx, e in enumerate(tqdm(all_examples)):
        if 'image_id' in e:
            # In vqa dataset, the image_id is the id of coco2014 dataset. E.g., "image_id": 262148.
            # In coco2014 dataset, the image name is padded with 0. E.g., "COCO_train2014_000000262148.jpg". 
            # So we zero pad image_id to 12 digits and format string
            image_id = str(e['image_id'])
            image_name = f"COCO_train2014_{image_id.zfill(12)}.jpg"
            all_image_names.append(image_name)
        else:
            print(f"image_id not found in {idx}th example.")
    return all_image_names


def _get_video_names_of_charadesdataset_for_avsddataset(avsddataset_path):
    """ This function aims to get the video name of charades dataset from avsd dataset.
    
    charades dataset: can be downloaded from: https://prior.allenai.org/projects/charades.
    We used the (Data (scaled to 480p, 13 GB)). After unzip, we get Charades_v1_480/.
    avsd dataset: can be downloaded from https://video-dialog.com/
    It has 4 files: avsd_train.json, avsd_val.json, train_options.json, val_options.json.

    Args:
        avsddataset_path (str): the path of avsd dataset.

    Returns:
        all_video_names (list): the video names of charades dataset.

    Example usage:
        all_video_names = _get_video_names_of_charadesdataset_for_avsddataset('avsd/avsd_train.json')
    """
    avsddata = load_json(avsddataset_path)
    # the keys in avsd_train.json and avsd_val.json are the video names of charades dataset.
    all_video_names = [video_name for video_name in tqdm(avsddata)]
    return all_video_names


def _get_image_and_video_names_for_vqa_and_avsd_datasets(vqadataset_paths, avsddataset_paths, save_path):
    """ This function aims to get the image and video names of coco2014 and charades datasets from vqa and avsd datasets.

    Args:
        vqadataset_paths (list): the paths of vqa datasets.
        avsddataset_paths (list): the paths of avsd datasets.
        save_path (str): the path to save the image and video names of coco2014 and charades datasets.

    Example usage:
        _get_image_and_video_names_for_vqa_and_avsd_datasets(
            ['vqa/v2_mscoco_train2014_annotations.json', 'vqa/v2_mscoco_val2014_annotations.json'],
            ['avsd/avsd_train.json', 'avsd/avsd_val.json'],
            'all_visual_names.vqa_avsd.json')
    """
    visual_data_names = []
    for vqadataset_path in vqadataset_paths:
        visual_data_names += _get_image_names_of_coco2014dataset_for_vqadataset(vqadataset_path)
    for avsddataset_path in avsddataset_paths:
        visual_data_names += _get_video_names_of_charadesdataset_for_avsddataset(avsddataset_path)
    
    visual_data_names_dict = {k:idx for idx, k in enumerate(visual_data_names)}  # {image_name: idx}
    visual_data_names = {'dict': visual_data_names_dict, 'list': visual_data_names}  # {'dict': {image_name: idx}, 'list': [image_name]}

    dump_json(visual_data_names, save_path)


def _get_image_and_video_names_from_macaw_generated_coco_and_avsd_datasets(macaw_coco_dataset_path, macaw_avsd_dataset_path, output_path):
    all_names = []

    image_examples = load_json(macaw_coco_dataset_path)['data']  # e.g., './generated_examples_coco.json'
    video_examples = load_json(macaw_avsd_dataset_path)['data']  # e.g., './generated_examples_avsd.json'

    for e in image_examples:
        all_names.append(e['id'])  # e.g., "COCO_train2014_000000344896.jpg"
    
    for e in video_examples:
        all_names.append(e['id'])  # e.g., "YSBN0"
    
    all_names_dict = {k:ind for ind, k in enumerate(all_names)}
    all_names = {'dict': all_names_dict, 'list': all_names}

    dump_json(all_names, output_path)


def _format_vqa_dataset(file_paths):
    vqa_annotations = load_json(file_paths["vqa_annotations_path"])['annotations']
    vqa_questions = load_json(file_paths["vqa_questions_path"])
    vqa_questions = {e['question_id']: [e['image_id'], e['question']] for e in vqa_questions['questions']}
    visual_data_names = load_json(file_paths["visual_data_names_path"])['dict']

    # Randomly sample NUM_RANDOM_VQA_SAMPLES examples from all_vqa_annotation_examples, and then turn the random_indices into a dictionary.
    # The reason for creating a dictionary instead of using the list directly is to quickly check
    # the existence of an index in the random_indices.
    random_indices = draw_samples([i for i in range(len(vqa_annotations))], NUM_RANDOM_VQA_SAMPLES)
    random_indices = {i: i for i in random_indices}

    # process each example
    all_examples = []
    num_samples = 0
    for ind, e in enumerate(tqdm(vqa_annotations)):
        if ind not in random_indices:
            continue

        # In vqa dataset, the image_id is the id of coco2014 dataset. E.g., "image_id": 262148.
        # In coco2014 dataset, the image name is padded with 0. E.g., "COCO_train2014_000000262148.jpg". 
        # So we zero pad image_id to 12 digits and format string
        image_id = str(e['image_id'])
        image_name = f"COCO_train2014_{image_id.zfill(12)}.jpg"
        image_id = visual_data_names[image_name]

        e = {
            'instruction': vqa_questions[e['question_id']][1],  # question from vqa dataset question file
            'input': "",
            'output': e['multiple_choice_answer'],  # answer from vqa dataset annotation file
            'image_name': image_name,
            'image_id': image_id,
            'audio_id': -1,  # NOTE: -1 means no audio. Similarly for other modalities.
            'video_id': -1
        }
        all_examples.append(e)
        num_samples += 1
        if num_samples >= MAX_NUM_SAMPLES_PER_DATASET:
            break
    print(f"Number of samples in standardized vqa dataset: {len(all_examples)}")
    return all_examples


def _format_avsd_dataset(file_paths):
    avsd_dataset = load_json(file_paths["avsd_dataset_path"])
    visual_data_names = load_json(file_paths["visual_data_names_path"])['dict']

    all_examples = []
    num_samples = 0
    should_break = False
    for ind, key in enumerate(tqdm(avsd_dataset)):
        if should_break:
            break
        video_metadata = avsd_dataset[key]  # key is video name, md is metadata of that video (contains dialogs and other meta data. See avsd_train.json for more info.)
        for dialog in video_metadata['data']:
            e = {
                'instruction': dialog['question'],
                'input': "",
                'output': dialog['answer'],
                'image_name': None,
                'image_id': -1,
                'audio_id': visual_data_names[key],  # !!! basically here we recorded the audio id stored in the all_visual_names dict. Frames and audios are not used yet.
                'video_id': visual_data_names[key],  # save as above
            }
            all_examples.append(e)
            num_samples += 1
            if num_samples >= MAX_NUM_SAMPLES_PER_DATASET:
                should_break = True
                break
    print(f"Number of samples in standardized avsd dataset: {len(all_examples)}")
    return all_examples


def _format_alpaca_dataset(file_paths):
    alpaca_dataset = load_json(file_paths["alpaca_dataset_path"])

    all_examples = []
    num_samples = 0
    for ind, e in enumerate(tqdm(alpaca_dataset)):
        e = {
            'instruction': e['instruction'],
            'input': e['input'],
            'output': e['output'],
            'image_name': None,
            'image_id': -1,
            'audio_id': -1,
            'video_id': -1,
        }
        all_examples.append(e)
        num_samples += 1
        if num_samples >= MAX_NUM_SAMPLES_PER_DATASET:
            break
    print(f"Number of samples in standardized alpaca dataset: {len(all_examples)}")
    return all_examples


def _format_macaw_coco_dataset(file_paths):
    macaw_coco_dataset = load_json(file_paths["macaw_coco_dataset_path"])['data']
    visual_data_names = load_json(file_paths["visual_data_names_path"])['dict']

    all_examples = []
    num_samples = 0
    for ind, e in enumerate(tqdm(macaw_coco_dataset)):
        # !!! WHY?? I don't know why this filtering criteria is needed. It is from the original macaw codebase.
        if 'caption' in e['instruction'] or 'caption' in e['response'] or ' no ' in e['response'] or 'not' in e['response']:
            continue

        e = {
            'instruction': e['instruction'],
            'input': "",
            'output': e['response'],
            'image_name': e['id'],
            'image_id': visual_data_names[e['id']],
            'audio_id': -1,
            'video_id': -1,
        }
        all_examples.append(e)
        num_samples += 1
        if num_samples >= MAX_NUM_SAMPLES_PER_DATASET:
            break
    print(f"Number of samples in standardized macaw coco dataset: {len(all_examples)}")
    return all_examples


def _format_macaw_avsd_dataset(file_paths):
    macaw_avsd_dataset = load_json(file_paths["macaw_avsd_dataset_path"])['data']
    visual_data_names = load_json(file_paths["visual_data_names_path"])['dict']

    all_examples = []
    num_samples = 0
    for ind, e in enumerate(tqdm(macaw_avsd_dataset)):
        # !!! WHY?? I don't know why this filtering criteria is needed. It is from the original macaw codebase.
        if 'caption' in e['instruction'] or 'caption' in e['response'] or ' no ' in e['response'] or 'not' in e['response']:
            continue

        e = {
            'instruction': e['instruction'],
            'input': "",
            'output': e['response'],
            'image_name': None,
            'image_id': -1,
            'audio_id': visual_data_names[e['id']],
            'video_id': visual_data_names[e['id']],
        }
        all_examples.append(e)
        num_samples += 1
        if num_samples >= MAX_NUM_SAMPLES_PER_DATASET:
            break
    print(f"Number of samples in standardized macaw avsd dataset: {len(all_examples)}")
    return all_examples


# NOTE: we can add more _format_<dataset_name>_dataset() functions here if we want to support more datasets.


def _format_mm_dataset(file_paths, dataset_name):
    # NOTE: if you want to add more datasets, you can add more dataset_name
    # and use corresponding _format_<dataset_name>_dataset() functions in this function.
    assert dataset_name in ['vqa', 'alpaca', 'avsd', 'macaw_coco', 'macaw_avsd']
    all_examples = []
    if dataset_name == 'vqa':
        all_examples = _format_vqa_dataset(file_paths)
    elif dataset_name == 'alpaca':
        all_examples = _format_alpaca_dataset(file_paths)
    elif dataset_name == 'avsd':
        all_examples = _format_avsd_dataset(file_paths)
    elif dataset_name == 'macaw_coco':
        all_examples = _format_macaw_coco_dataset(file_paths)
    elif dataset_name == 'macaw_avsd':
        all_examples = _format_macaw_avsd_dataset(file_paths)
    else:
        raise NotImplementedError
    return all_examples


def pad_or_truncate_tokens(tokens, max_length, pad_token_id):
    """ This function aims to pad or truncate tokens to max_length.

    Args:
        tokens (list): the list of tokens.
        max_length (int): the max length of tokens.
        pad_token_id (int): the id of pad token.

    Returns:
        tokens (list): the list of tokens after padding or truncating.
    """
    if len(tokens) > max_length:
        tokens = tokens[:max_length]
    elif len(tokens) < max_length:
        tokens = tokens + [pad_token_id] * (max_length - len(tokens))
    return tokens


def _preprocess_text(formatted_mm_dataset_example, tokenizer, max_length=MAX_LENGTH):
    instruction_text = formatted_mm_dataset_example['instruction']
    input_text = formatted_mm_dataset_example['input']
    response_text = formatted_mm_dataset_example['output']

    # Format the text without output.
    prompt_without_output = _format_text(instruction_text, input_text, None)
    # Tokenize the formatted_text
    # if we use llama tokenizer, for each item it will looks like:
    #  {'input_ids': [1, 5796, 28826, 338, 263, 282, 335], 'token_type_ids': [0, 0, 0, 0, 0, 0, 0], 'attention_mask': [1, 1, 1, 1, 1, 1, 1]}
    # but if we use .encode function, only the input_ids will be returned.
    prompt_without_output_tokens = tokenizer.encode(prompt_without_output)

    # Append the output to the formatted text.
    prompt_with_output = _format_text(instruction_text, input_text, response_text)
    prompt_with_output_tokens = tokenizer.encode(prompt_with_output)
    prompt_with_output_tokens = pad_or_truncate_tokens(prompt_with_output_tokens, max_length, tokenizer.pad_token_id)

    # Create the labels.
    # - For the prefix part (everything up to the answer), labels are filled with IGNORE_INDEX.
    # - For the answer part, labels are the tokens of the answer.
    # IGNORE_INDEX is used to ignore the tokens that are part of the prompt or question when calculating the loss. 
    # We only want to calculate the loss for the part of the output sequence that corresponds to the answer.
    prefix_length = len(prompt_without_output_tokens) - 1
    labels = [IGNORE_INDEX] * prefix_length + prompt_with_output_tokens[prefix_length:]
    labels = pad_or_truncate_tokens(labels, max_length, IGNORE_INDEX)
    # We shall make the padded part as IGNORE_INDEX as well. 
    labels = [(l if l != tokenizer.pad_token_id else IGNORE_INDEX) for l in labels]

    result = {
        'prompt_with_output': prompt_with_output,
        'prompt_without_output': prompt_without_output,
        'prompt_with_output_tokens': prompt_with_output_tokens,
        'prompt_without_output_tokens': prompt_without_output_tokens,
        'labels': labels
    }

    return result


def _preprocess_image(formatted_mm_dataset_example):
    # NOTE: this function aims to prepare for future more complex image preprocessing.
    result = {
        'image_id': formatted_mm_dataset_example['image_id'],
    }
    return result


def _preprocess_audio(formatted_mm_dataset_example):
    # NOTE: this function aims to prepare for future more complex audio preprocessing.
    result = {
        'audio_id': formatted_mm_dataset_example['audio_id'],
    }
    return result


def _preprocess_video(formatted_mm_dataset_example):
    # NOTE: this function aims to prepare for future more complex video preprocessing.
    result = {
        'video_id': formatted_mm_dataset_example['video_id'],
    }
    return result


# NOTE: we can add more preprocess functions here for more modalities, e.g., table, chart, etc.


def _preprocess_mm_dataset_examples(all_formatted_mm_dataset_examples, tokenizer, max_length=MAX_LENGTH):
    # NOTE: we can add more preprocess functions here for more modalities, e.g., table, chart, etc.
    all_results = {
        # each element is a formatted text
        'texts': [],
        # each element is a list of token ids of the formatted text.
        # length: max_length=MAX_LENGTH=256, !!! padded with pad_token_id=32000
        'text_token_ids': [],
        # each element is a list of label ids of the formatted text. 
        # The input part is set as [IGNORE_ID=-100], and the remaining part is the same as text_token_ids. 
        # length: max_length=MAX_LENGTH=256, !!! padded with IGNORE_INDEX=-100
        #!!! NOTE: seems we shall make the padded part as IGNORE_INDEX=-100 as well. 
        'labels': [],
        'image_ids': [],
        'audio_ids': [],
        'video_ids': [],
    }
    for ind, e in enumerate(tqdm(all_formatted_mm_dataset_examples)):
        # Use the _preprocess_text function to format, tokenize and create labels
        text_preprocess_result = _preprocess_text(e, tokenizer, max_length)
        image_preprocess_result = _preprocess_image(e)
        audio_preprocess_result = _preprocess_audio(e)
        video_preprocess_result = _preprocess_video(e)

        # If the length of tokens without the output (answer) is longer than or equal to max_length, skip this iteration
        if len(text_preprocess_result["prompt_without_output_tokens"]) >= max_length:
            continue

        # Update the result lists
        all_results['texts'].append(text_preprocess_result['prompt_with_output'])
        all_results['text_token_ids'].append(text_preprocess_result['prompt_with_output_tokens'])
        all_results['labels'].append(text_preprocess_result["labels"])
        all_results['image_ids'].append(image_preprocess_result['image_id'])
        all_results['audio_ids'].append(audio_preprocess_result['audio_id'])
        all_results['video_ids'].append(video_preprocess_result['video_id'])

    return all_results


def preprocess_mm_dataset(file_paths, dataset_name, tokenizer, max_length=MAX_LENGTH):
    all_formatted_mm_dataset_examples = _format_mm_dataset(file_paths, dataset_name)
    result = _preprocess_mm_dataset_examples(all_formatted_mm_dataset_examples, tokenizer, max_length)
    return result


def _get_tokenizer():
    # prepare llama tokenizer
    # NOTE: The authors of macaw used https://huggingface.co/decapoda-research/llama-7b-hf. However, this version tokenizer has
    # some bugs (see: https://github.com/huggingface/transformers/issues/22222).
    # So we use the tokenizer from https://huggingface.co/yahma/llama-7b-hf.
    # Also, in many llama tokenizer versions, their bos, eos id seems to be 0, making models hard to learn 
    # when to stop. Therefore, it is more recommended to use 'yahma/llama-7b-hf' or 'yahma/llama-13b-hf'.
    # Credit to Yu Song for the bug of LLaMA tokenizer.
    tokenizer = AutoTokenizer.from_pretrained('yahma/llama-7b-hf')  #!!!

    # special_tokens_dict = {'additional_special_tokens': ['<image>', '</image>', '<audio>', '</audio>', '<video>', '</video>']}
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({'pad_token': DEFAULT_PAD_TOKEN})  #!!! NOTE: currently, the pad_token_id is 32000. It is not the same with the macaw implementation. I don't know why.
    tokenizer.padding_side = "right"
    tokenizer.add_special_tokens({
        "eos_token": DEFAULT_EOS_TOKEN,
        "bos_token": DEFAULT_BOS_TOKEN,
        "unk_token": DEFAULT_UNK_TOKEN,
    })
    tokenizer.save_pretrained('./llama_tokenizer')
    return tokenizer
    

def preprocess_merge_and_sample_mm_datasets(input_file_paths, dataset_names, output_path, max_length=MAX_LENGTH):
    # Prepare tokenizer
    tokenizer = _get_tokenizer()

    # preprocess all datasets: vqa, alpaca, avsd
    preprocess_mm_dataset_results = {}
    for dataset_name in dataset_names:
        preprocess_mm_dataset_results[dataset_name] = preprocess_mm_dataset(input_file_paths, dataset_name, tokenizer, max_length)
        pickle.dump(preprocess_mm_dataset_results[dataset_name], open(f'./preprocess_{dataset_name}_result.pkl', "wb"), protocol=4)

    # merge all preprocessed datasets
    merged_result = {}
    all_keys = ['texts', 'text_token_ids', 'labels', 'image_ids', 'audio_ids', 'video_ids']
    for key in all_keys:
        merged_result[key] = []
        for dataset_name in dataset_names:
            merged_result[key] += preprocess_mm_dataset_results[dataset_name][key]
    
    # randomly sample merged dataset
    n_elements = len(merged_result['texts'])
    random_indices = random.sample(range(n_elements), NUM_RANDOM_MERGED_SAMPLES)
    for key in all_keys:
        merged_result[key] = [merged_result[key][i] for i in random_indices]

    # save the sampled dataset to a pickle file as the final training dataset
    pickle.dump(merged_result, open(output_path, "wb"), protocol=4)
    training_dataset = merged_result 

    return training_dataset


def _tests_for_debug(input_file_paths, dataset_names, output_path):
    all_keys = ['texts', 'text_token_ids', 'labels', 'image_ids', 'audio_ids', 'video_ids']

    train = pickle.load(open(output_path, "rb"))
    print("number of elements in train:", len(train['texts']))
    print("one element in train:")
    for key in all_keys:
        print(train[key][0])

    preprocess_mm_dataset_results = {}
    for dataset_name in dataset_names:
        preprocess_mm_dataset_results[dataset_name] = pickle.load(open('preprocess_{}_result.pkl'.format(dataset_name), "rb"))
        print("number of elements in {}:".format(dataset_name), len(preprocess_mm_dataset_results[dataset_name]['texts']))
        print("one element in {} results:".format(dataset_name))
        for key in all_keys:
            print(preprocess_mm_dataset_results[dataset_name][key][0])

    for dataset_name in dataset_names:
        print("find the same element in train and {} results:".format(dataset_name))
        num_overlap = 0
        for i in range(len(train['texts'])):
            for j in range(len(preprocess_mm_dataset_results[dataset_name]['texts'])):
                if train['texts'][i] == preprocess_mm_dataset_results[dataset_name]['texts'][j]:
                    print(i, j)
                    assert train['texts'][i] == preprocess_mm_dataset_results[dataset_name]['texts'][j]
                    assert train['text_token_ids'][i] == preprocess_mm_dataset_results[dataset_name]['text_token_ids'][j]
                    assert train['labels'][i] == preprocess_mm_dataset_results[dataset_name]['labels'][j]
                    assert train['image_ids'][i] == preprocess_mm_dataset_results[dataset_name]['image_ids'][j]
                    assert train['audio_ids'][i] == preprocess_mm_dataset_results[dataset_name]['audio_ids'][j]
                    assert train['video_ids'][i] == preprocess_mm_dataset_results[dataset_name]['video_ids'][j]
                    num_overlap += 1
                    break
        print("there are {} overlaps between train and {} dataset".format(num_overlap, dataset_name))
    print("Done checking!")


if __name__ == '__main__':
    # # Stage 1: extract audio and frames from videos.
    # # Given a folder contain videos, for each video, we extract the audio and sample 120 frames from it.
    # videos_folder_path = os.path.join(os.path.dirname(__file__), 'avsd/videos/')
    # audios_folder_path = os.path.join(os.path.dirname(__file__), 'avsd/audios/')
    # frames_folder_path = os.path.join(os.path.dirname(__file__), 'avsd/frames/')
    # sample_frames_from_videos_dir(videos_folder_path, frames_folder_path)
    # extract_audios_from_videos_dir(videos_folder_path, audios_folder_path)

    # # Stage 2: format the json files to make them easier to read.
    # vqa_folder_path = os.path.join(os.path.dirname(__file__), 'vqa/')
    # avsd_folder_path = os.path.join(os.path.dirname(__file__), 'avsd/')

    # prettyformat_json(join(vqa_folder_path, 'v2_mscoco_train2014_annotations.json'), join(vqa_folder_path, 'v2_mscoco_train2014_annotations.pretty.json'))
    # prettyformat_json(join(vqa_folder_path, 'v2_mscoco_val2014_annotations.json'), join(vqa_folder_path, 'v2_mscoco_val2014_annotations.pretty.json'))
    # prettyformat_json(join(vqa_folder_path, 'v2_OpenEnded_mscoco_train2014_questions.json'), join(vqa_folder_path, 'v2_OpenEnded_mscoco_train2014_questions.pretty.json'))
    # prettyformat_json(join(vqa_folder_path, 'v2_OpenEnded_mscoco_val2014_questions.json'), join(vqa_folder_path, 'v2_OpenEnded_mscoco_val2014_questions.pretty.json'))

    # prettyformat_json(join(avsd_folder_path, 'avsd_train.json'), join(avsd_folder_path, 'avsd_train.pretty.json'))
    # prettyformat_json(join(avsd_folder_path, 'avsd_val.json'), join(avsd_folder_path, 'avsd_val.pretty.json'))
    # prettyformat_json(join(avsd_folder_path, 'train_options.json'), join(avsd_folder_path, 'train_options.pretty.json'))
    # prettyformat_json(join(avsd_folder_path, 'val_options.json'), join(avsd_folder_path, 'val_options.pretty.json'))

    # # Stage 3: get all the image names and video names of vqa and avsd datasets, macaw generated coco and avsd datasets.
    # _get_image_and_video_names_for_vqa_and_avsd_datasets(
    #     ['vqa/v2_mscoco_train2014_annotations.json', 'vqa/v2_mscoco_val2014_annotations.json'],
    #     ['avsd/avsd_train.json', 'avsd/avsd_val.json'],
    #     'all_visual_names.vqa_avsd.json')

    # _get_image_and_video_names_from_macaw_generated_coco_and_avsd_datasets(
    #     macaw_coco_dataset_path = './generated_examples_coco.json',
    #     macaw_avsd_dataset_path = './generated_examples_avsd.json',
    #     output_path = './all_visual_names.macaw_coco_avsd.json',
    # )

    # # Stage 4: process all the datasets (vqa, alpaca, avsd), merge, and sample.
    # input_file_paths = {
    #     'vqa_annotations_path': 'vqa/v2_mscoco_train2014_annotations.json',
    #     'vqa_questions_path': 'vqa/v2_OpenEnded_mscoco_train2014_questions.json',
    #     'alpaca_dataset_path': 'alpaca/alpaca_data.json',
    #     'avsd_dataset_path': 'avsd/avsd_train.json',
    #     'visual_data_names_path': 'all_visual_names.vqa_avsd.json',
    # }
    # dataset_names = ['vqa', 'alpaca', 'avsd']
    # output_path = 'train.vqa_alpaca_avsd.sampled.pkl'

    # # debug    
    # DEBUG_MODE = True
    # MAX_NUM_SAMPLES_PER_DATASET = MAX_NUM_RANDOM_DEBUG_SAMPLES
    # NUM_RANDOM_MERGED_SAMPLES = NUM_RANDOM_MERGED_DEBUG_SAMPLES
    # print('DEBUG_MODE: ', DEBUG_MODE)
    # print('MAX_NUM_SAMPLES_PER_DATASET: ', MAX_NUM_SAMPLES_PER_DATASET)
    # print('NUM_RANDOM_MERGED_SAMPLES: ', NUM_RANDOM_MERGED_SAMPLES)

    # preprocess_merge_and_sample_mm_datasets(input_file_paths, dataset_names, output_path, max_length=MAX_LENGTH)
    # _tests_for_debug(input_file_paths, dataset_names, output_path)

    # # once debug successed, run the following code    
    # DEBUG_MODE = False
    # MAX_NUM_SAMPLES_PER_DATASET = sys.maxsize  # NOTE: same as the top of this file
    # NUM_RANDOM_MERGED_SAMPLES = 50000  # NOTE: same as the top of this file
    # print('DEBUG_MODE: ', DEBUG_MODE)
    # print('MAX_NUM_SAMPLES_PER_DATASET: ', MAX_NUM_SAMPLES_PER_DATASET)
    # print('NUM_RANDOM_MERGED_SAMPLES: ', NUM_RANDOM_MERGED_SAMPLES)

    # preprocess_merge_and_sample_mm_datasets(input_file_paths, dataset_names, output_path, max_length=MAX_LENGTH)

    # # Stage 5: process the macaw generated coco and avsd datasets
    # input_file_paths = {
    #     'macaw_coco_dataset_path': './generated_examples_coco.json',
    #     'macaw_avsd_dataset_path': './generated_examples_avsd.json',
    #     'visual_data_names_path': 'all_visual_names.macaw_coco_avsd.json',
    # }
    # dataset_names = ['macaw_coco', 'macaw_avsd']
    # output_path = 'train.macaw_coco_avsd.sampled.pkl'

    # # debug    
    # DEBUG_MODE = True
    # MAX_NUM_SAMPLES_PER_DATASET = MAX_NUM_RANDOM_DEBUG_SAMPLES
    # NUM_RANDOM_MERGED_SAMPLES = NUM_RANDOM_MERGED_DEBUG_SAMPLES
    # print('DEBUG_MODE: ', DEBUG_MODE)
    # print('MAX_NUM_SAMPLES_PER_DATASET: ', MAX_NUM_SAMPLES_PER_DATASET)
    # print('NUM_RANDOM_MERGED_SAMPLES: ', NUM_RANDOM_MERGED_SAMPLES)

    # preprocess_merge_and_sample_mm_datasets(input_file_paths, dataset_names, output_path, max_length=MAX_LENGTH)
    # _tests_for_debug(input_file_paths, dataset_names, output_path)

    # # once debug successed, run the following code
    # DEBUG_MODE = False
    # MAX_NUM_SAMPLES_PER_DATASET = sys.maxsize  # NOTE: same as the top of this file
    # NUM_RANDOM_MERGED_SAMPLES = 50000  # NOTE: same as the top of this file
    # print('DEBUG_MODE: ', DEBUG_MODE)
    # print('MAX_NUM_SAMPLES_PER_DATASET: ', MAX_NUM_SAMPLES_PER_DATASET)
    # print('NUM_RANDOM_MERGED_SAMPLES: ', NUM_RANDOM_MERGED_SAMPLES)

    # preprocess_merge_and_sample_mm_datasets(input_file_paths, dataset_names, output_path, max_length=MAX_LENGTH)
    pass