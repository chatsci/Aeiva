import sys
from tqdm import tqdm
from typing import Optional

from aeiva.common.types import DataSet
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.file_utils import ensure_dir
from aeiva.common.decorators import register_data_formatter


@register_data_formatter('macaw_coco')
def format_macaw_coco(input_filepaths_dict: dict[str, str],
                      output_dir: Optional[str],
                      max_samples: Optional[int] = sys.maxsize) -> DataSet:
    # load raw data
    dataset_name = "macaw_coco"
    raw_dataset = load_json(input_filepaths_dict["macaw_coco_dataset_path"])['data']

    # process each example
    formatted_examples = []
    for idx, e in enumerate(tqdm(raw_dataset)):
        if len(formatted_examples) >= max_samples:
            break
        # !!! WHY?? I don't know why this filtering criteria is needed. It is from the original macaw codebase.
        if 'caption' in e['instruction'] or 'caption' in e['response'] or ' no ' in e['response'] or 'not' in e['response']:
            continue

        formatted_e = {
            'instruction': e['instruction'],
            'input': "",
            'output': e['response'],
            'image': e['id'],
            'audio': None,
            'video': None
        }
        formatted_examples.append(formatted_e)
    print(f"Number of samples in formatted {dataset_name} dataset: {len(formatted_examples)}")

    # prepare output
    metadata = {
        "num_samples": len(formatted_examples)
    }
    formatted_dataset = {
        "data": formatted_examples,
        "metadata": metadata
    }
    if output_dir is not None:
        ensure_dir(output_dir)
        dump_json(formatted_dataset, f"{output_dir}/{dataset_name}_dataset.formatted.json")

    return formatted_dataset


@register_data_formatter('macaw_avsd')
def format_macaw_avsd(input_filepaths_dict: dict[str, str],
                      output_dir: Optional[str],
                      max_samples: Optional[int] = sys.maxsize) -> DataSet:
    # load raw data
    dataset_name = "macaw_avsd"
    raw_dataset = load_json(input_filepaths_dict["macaw_avsd_dataset_path"])['data']

    # process each example
    formatted_examples = []
    for idx, e in enumerate(tqdm(raw_dataset)):
        if len(formatted_examples) >= max_samples:
            break
        # !!! WHY?? I don't know why this filtering criteria is needed. It is from the original macaw codebase.
        if 'caption' in e['instruction'] or 'caption' in e['response'] or ' no ' in e['response'] or 'not' in e['response']:
            continue

        formatted_e = {
            'instruction': e['instruction'],
            'input': "",
            'output': e['response'],
            'image': None,
            'audio': None,
            'video': e['id'] + ".mp4"
        }
        formatted_examples.append(formatted_e)
    print(f"Number of samples in formatted {dataset_name} dataset: {len(formatted_examples)}")

    # prepare output
    metadata = {
        "num_samples": len(formatted_examples)
    }
    formatted_dataset = {
        "data": formatted_examples,
        "metadata": metadata
    }
    if output_dir is not None:
        ensure_dir(output_dir)
        dump_json(formatted_dataset, f"{output_dir}/{dataset_name}_dataset.formatted.json")

    return formatted_dataset
