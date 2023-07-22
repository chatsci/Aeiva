from aeiva.data.base import BaseDataFormatter
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.sample_utils import draw_samples
from aeiva.util.file_utils import ensure_dir
from tqdm import tqdm
from typing import Any, Optional


class VqaDataFormatter(BaseDataFormatter):
    formatter_name = "vqa"
    
    def __init__(self, dataset_name: str, output_dir: str, max_samples: Optional[int] = None, save_output: bool = True):
        self.dataset_name = dataset_name
        self.output_dir = output_dir
        self.max_samples = max_samples
        self.save_output = save_output
    
    def format(self, input_filepaths_dict: dict[str, str]) -> dict[str, Any]:
        output_dir = self.output_dir
        max_samples = self.max_samples
        save_output = self.save_output

        # load raw data
        vqa_annotations = load_json(input_filepaths_dict["vqa_annotations_path"])['annotations']
        vqa_questions = load_json(input_filepaths_dict["vqa_questions_path"])
        vqa_questions = {e['question_id']: [e['image_id'], e['question']] for e in vqa_questions['questions']}
        total_raw_samples = len(vqa_annotations)

        # get sample indices
        if max_samples is None:
            max_samples = total_raw_samples
            random_indices = [i for i in range(total_raw_samples)]
        else:
            random_indices = draw_samples([i for i in range(total_raw_samples)], max_samples)
        random_indices = {i: i for i in random_indices}  # for quick check of existence of an index

        # process each example
        formatted_examples = []
        num_samples = 0
        for idx, e in enumerate(tqdm(vqa_annotations)):
            if num_samples >= max_samples:
                break
            if idx not in random_indices:
                continue

            # In vqa dataset, the image_id is the id of coco2014 dataset. E.g., "image_id": 262148.
            # In coco2014 dataset, the image name is padded with 0. E.g., "COCO_train2014_000000262148.jpg". 
            # So we zero pad image_id to 12 digits and format string
            image_id = str(e['image_id'])
            image_name = f"COCO_train2014_{image_id.zfill(12)}.jpg"

            formatted_e = {
                'instruction': vqa_questions[e['question_id']][1],  # question from vqa dataset question file
                'input': "",
                'output': e['multiple_choice_answer'],  # answer from vqa dataset annotation file
                'image': image_name,
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
