from aeiva.data.formatter import BaseDataFormatter
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.file_utils import ensure_dir
from tqdm import tqdm
from typing import Any, Optional


class AvsdDataFormatter(BaseDataFormatter):
    formatter_name = "avsd"
    
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
        raw_dataset = load_json(input_filepaths_dict["avsd_dataset_path"])

        # process each example
        formatted_examples = []
        num_samples = 0
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
                num_samples += 1
                if num_samples >= max_samples:
                    should_break = True
                    break
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
