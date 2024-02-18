import sys
from tqdm import tqdm
from typing import Optional

from aeiva.common.types import DataSet
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.file_utils import ensure_dir
from aeiva.common.decorators import register_data_formatter


@register_data_formatter('avsd')
def format_avsd(input_filepaths_dict: dict[str, str],
                output_dir: Optional[str],
                max_samples: Optional[int] = sys.maxsize) -> DataSet:
    # load raw data
    dataset_name = "avsd"
    raw_dataset = load_json(input_filepaths_dict["avsd_dataset_path"])

    # process each example
    formatted_examples = []
    should_break = False
    for idx, key in enumerate(tqdm(raw_dataset)):
        if should_break:
            break
        video_metadata = raw_dataset[key]  # key is video name in the Charades video dataset
        for dialog in video_metadata['data']:
            formatted_e = {
                'instruction': dialog['question'],
                'input': "",
                'output': dialog['answer'],
                'image': None,
                'audio': None,  # we use the audio extracted from the video
                'video': key + ".mp4",
            }
            formatted_examples.append(formatted_e)
            if len(formatted_examples) >= max_samples:
                should_break = True
                break
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
