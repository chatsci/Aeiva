import sys
from tqdm import tqdm
from typing import Optional

from aeiva.common.types import DataSet
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.file_utils import ensure_dir
from aeiva.util.sample_utils import draw_samples
from aeiva.common.decorators import register_data_formatter


@register_data_formatter('vqa')
def format_vqa(input_filepaths_dict: dict[str, str],
               output_dir: Optional[str],
               max_samples: Optional[int] = sys.maxsize) -> DataSet:
    # load raw data
    dataset_name = "vqa"
    vqa_annotations = load_json(input_filepaths_dict["vqa_annotations_path"])['annotations']
    vqa_questions = load_json(input_filepaths_dict["vqa_questions_path"])
    vqa_questions = {e['question_id']: [e['image_id'], e['question']] for e in vqa_questions['questions']}
    total_raw_samples = len(vqa_annotations)

    # get sample indices
    if max_samples is None:
        max_samples = total_raw_samples
        random_indices = set(i for i in range(total_raw_samples))
    else:
        random_indices = set(draw_samples([i for i in range(total_raw_samples)], max_samples))

    # process each example
    formatted_examples = []
    for idx, e in enumerate(tqdm(vqa_annotations)):
        if len(formatted_examples) >= max_samples:
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
