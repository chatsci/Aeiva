from aeiva.data.formatter import BaseDataFormatter
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.file_utils import ensure_dir
from tqdm import tqdm
from typing import Any, Optional


class MacawCocoDataFormatter(BaseDataFormatter):
    formatter_name = "macaw_coco"
    
    def __init__(self, dataset_name: str, output_dir: str, max_samples: Optional[int] = None, save_output: bool = True):
        self.dataset_name = dataset_name
        self.output_dir = output_dir
        self.max_samples = max_samples
        self.save_output = save_output
    
    def execute(self, input_filepaths_dict: dict[str, str]) -> dict[str, Any]:
        output_dir = self.output_dir
        max_samples = self.max_samples
        save_output = self.save_output

        # load raw data
        raw_dataset = load_json(input_filepaths_dict["macaw_coco_dataset_path"])['data']

        # process each example
        formatted_examples = []
        num_samples = 0
        for idx, e in enumerate(tqdm(raw_dataset)):
            if num_samples >= max_samples:
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
            num_samples += 1
        print(f"Number of samples in formatted {self.dataset_name} dataset: {len(formatted_examples)}")

        # prepare output
        metadata = {
            "num_samples": len(formatted_examples)
        }
        formatted_dataset = {
            "data": formatted_examples,
            "metadata": metadata
        }
        if save_output:
            ensure_dir(output_dir)
            dump_json(formatted_dataset, f"{output_dir}/{self.dataset_name}_dataset.formatted.json")

        return formatted_dataset


class MacawAvsdDataFormatter(BaseDataFormatter):
    formatter_name = "macaw_avsd"
    
    def __init__(self, dataset_name: str, output_dir: str, max_samples: Optional[int] = None, save_output: bool = True):
        self.dataset_name = dataset_name
        self.output_dir = output_dir
        self.max_samples = max_samples
        self.save_output = save_output
    
    def execute(self, input_filepaths_dict: dict[str, str]) -> dict[str, Any]:
        output_dir = self.output_dir
        max_samples = self.max_samples
        save_output = self.save_output

        # load raw data
        raw_dataset = load_json(input_filepaths_dict["macaw_avsd_dataset_path"])['data']

        # process each example
        formatted_examples = []
        num_samples = 0
        for idx, e in enumerate(tqdm(raw_dataset)):
            if num_samples >= max_samples:
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
            num_samples += 1
        print(f"Number of samples in formatted {self.dataset_name} dataset: {len(formatted_examples)}")

        # prepare output
        metadata = {
            "num_samples": len(formatted_examples)
        }
        formatted_dataset = {
            "data": formatted_examples,
            "metadata": metadata
        }
        if save_output:
            ensure_dir(output_dir)
            dump_json(formatted_dataset, f"{output_dir}/{self.dataset_name}_dataset.formatted.json")

        return formatted_dataset
