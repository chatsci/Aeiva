from functools import partial

from transformers import LlamaTokenizer

from aeiva.common.constants import IGNORE_ID
from aeiva.config import OmniConfig
from aeiva.util.json_utils import dump_json
from aeiva.util.file_utils import ensure_dir
from aeiva.util.token_utils import get_tokenizer
from aeiva.operator.dataitem_ops import sample_frames_from_video, extract_audio_from_video, tokenize_and_label_text_for_instruction_tuning
from aeiva.operator.dataset_ops import build_dataset, merge_datasets, sample_dataset, filter_dataset_by_keys


if __name__ == "__main__":
    # load config
    config_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"
    OmniConfig.create_omni_config()
    CONFIG = OmniConfig.from_yaml(config_path)
    print("config: ", CONFIG)
    print("==================== Step 0: loading config done")

    # shared by all datasets
    # tokenizer_name_or_path = 'yahma/llama-7b-hf'  #!!! currently different with the author. Maybe we can just load from the downloaded tokenizer.
    # TOKENIZER = get_tokenizer(tokenizer_name_or_path, add_special_tokens=True, special_tokens_dict=TOKENIZER_SPECIAL_TOKENS)
    TOKENIZER =  get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)

    DATA_PROCESS_PIPELINE = [
        partial(tokenize_and_label_text_for_instruction_tuning, tokenizer=TOKENIZER, max_length=CONFIG.max_seq_len_for_preprocess, ignore_id=IGNORE_ID),
        partial(sample_frames_from_video, num_frames=CONFIG.num_frames_to_sample, video_dir=CONFIG.video_dir, frame_dir=CONFIG.frame_dir),  #!!! get frame indices
        partial(extract_audio_from_video, video_dir=CONFIG.video_dir, audio_dir=CONFIG.audio_dir)  # !!! get audio name
    ]

    # process each single dataset
    processed_datasets = {}

    # process avsd
    dataset_name = "avsd"
    input_filepaths_dict = {
        "avsd_dataset_path": "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/avsd_train.json"
    }
    output_dir = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/output/"
    processed_data = build_dataset(dataset_name, input_filepaths_dict, DATA_PROCESS_PIPELINE, output_dir, CONFIG.num_samples_per_dataset)
    processed_datasets["avsd"] = processed_data

    # process alpaca
    dataset_name = "alpaca"
    input_filepaths_dict = {
        "alpaca_dataset_path": "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/alpaca/alpaca_data.json"
    }
    output_dir = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/alpaca/output/"
    processed_data = build_dataset(dataset_name, input_filepaths_dict, DATA_PROCESS_PIPELINE, output_dir, CONFIG.num_samples_per_dataset)
    processed_datasets["alpaca"] = processed_data

    # process macaw_coco
    dataset_name = "macaw_coco"
    input_filepaths_dict = {
        "macaw_coco_dataset_path": "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/macaw/generated_examples_coco.json",
    }
    output_dir = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/macaw/output/"
    processed_data = build_dataset(dataset_name, input_filepaths_dict, DATA_PROCESS_PIPELINE, output_dir, CONFIG.num_samples_per_dataset)
    processed_datasets["macaw_coco"] = processed_data

    # process macaw_avsd
    dataset_name = "macaw_avsd"
    input_filepaths_dict = {
        "macaw_avsd_dataset_path": "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/macaw/generated_examples_avsd.json",
    }
    output_dir = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/macaw/output/"
    processed_data = build_dataset(dataset_name, input_filepaths_dict, DATA_PROCESS_PIPELINE, output_dir, CONFIG.num_samples_per_dataset)
    processed_datasets["macaw_avsd"] = processed_data

    # process vqa
    dataset_name = "vqa"
    input_filepaths_dict = {
        "vqa_annotations_path": "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/vqa/v2_mscoco_train2014_annotations.json",
        "vqa_questions_path": "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/vqa/v2_OpenEnded_mscoco_train2014_questions.json",
        }
    output_dir = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/vqa/output/"
    processed_data = build_dataset(dataset_name, input_filepaths_dict, DATA_PROCESS_PIPELINE, output_dir, CONFIG.num_samples_per_dataset)
    processed_datasets["vqa"] = processed_data

    print("==================== Step 1: format and process datasets done")

    # merge and sample datasets
    keys_to_preserve = ['text', 'text_token_ids', 'attention_mask', 'labels', 'image', 'audio', 'video', 'sampled_video_frame_indices']  #!!!!!

    # merge 1
    datasets_to_merge = ["avsd", "alpaca", "vqa"]
    output_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/merge/avsd_alpaca_vqa.json"
    merged_datasets = [processed_datasets[dataset_name] for dataset_name in datasets_to_merge]
    merged_datasets = merge_datasets(merged_datasets)
    merged_datasets = sample_dataset(merged_datasets, CONFIG.num_samples_per_merged_dataset)
    merged_datasets = filter_dataset_by_keys(merged_datasets, keys_to_preserve)
    ensure_dir(output_path)
    dump_json(merged_datasets, output_path)

    # merge 2
    datasets_to_merge = ["macaw_coco", "macaw_avsd"]
    output_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/merge/macaw_coco_avsd.json"
    merged_datasets = [processed_datasets[dataset_name] for dataset_name in datasets_to_merge]
    merged_datasets = merge_datasets(merged_datasets)
    merged_datasets = sample_dataset(merged_datasets, CONFIG.num_samples_per_merged_dataset)
    merged_datasets = filter_dataset_by_keys(merged_datasets, keys_to_preserve)
    ensure_dir(output_path)
    dump_json(merged_datasets, output_path)

    print("==================== Step 2: merge and sample datasets done")
