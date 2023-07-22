from functools import partial
from transformers import LlamaTokenizer
from aeiva.util.token_utils import get_tokenizer
from transformers import CLIPConfig, WhisperConfig, LlamaTokenizer
from transformers import AutoConfig
from aeiva.model.macaw_model import MM_LLMs, MM_LLMs_Config
from functools import partial
from aeiva.data.util.dataitem_utils import get_transformed_image, load_video_frames, get_audio_mels
from aeiva.config import OmniConfig
from aeiva.data.operator.loader import collate_multimodal_batches
import torch
from aeiva.util.pipeline import Pipeline
from aeiva.util.file_utils import copy_file_to_dst
from aeiva.data.util.dataitem_utils import sample_frames_from_video, extract_audio_from_video
from aeiva.data.util.dataitem_utils import tokenize_and_label_text_for_instruction_tuning
from aeiva.util.constants import IGNORE_ID
import os
from aeiva.util.file_utils import print_dict_to_file


if __name__ == "__main__":
    # setup pretrained model
    clip_config = CLIPConfig.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    whisper_config = WhisperConfig.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/whisper_model/')
    llm_config = AutoConfig.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/llama7b_model/')
    tokenizer =  get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)
    llm_config.vocab_size = len(tokenizer)  # !!! because macaw model added some special tokens.
    print("llm_config: ", llm_config)

    model_config = MM_LLMs_Config(
        n_frames=6, 
        attention_heads=32, 
        image_conv_kernel=48, 
        image_conv_stride=36, 
        video_conv_kernel=36, 
        video_conv_stride=30, 
        audio_conv_kernel=240, 
        audio_conv_stride=220,
        clip_config=clip_config, whisper_config=whisper_config, llm_config=llm_config
    )

    # option 1: load from pretrained macaw model
    macaw_model = MM_LLMs.from_pretrained(
        '/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/',
        config = model_config,
        # load_in_8bit=True,
        # torch_dtype=torch.float16,
        # device_map=device_map,
    )
    TOKENIZER =  get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)

    # # option 2: test un-finetuned model
    # model = MM_LLMs(config=model_config)
    # model.image_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    # model.video_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    # model.audio_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/whisper_model/')
    # model.llm.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/llama7b_model/')
    # print("model config: ", model.llm.config)
    # # model.llm.config.use_return_dict = True #!!!!!!!!!  # seems it is None and read only. I cannot revise it....
    # model.llm.resize_token_embeddings(len(tokenizer))
    # macaw_model = model
    # # tokenizer_name_or_path = 'decapoda-research/llama-7b-hf'  #!!! the author used this.
    # tokenizer_name_or_path = 'yahma/llama-7b-hf'  #!!! currently different with the author. Suggested by Yu.
    # TOKENIZER = get_tokenizer(tokenizer_name_or_path, tokenizer_cls=LlamaTokenizer)

    print("==================== Step 1: loading pretrained model done")


    # setup omniconfig
    config_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"
    OmniConfig.create_omni_config()
    config = OmniConfig.from_yaml(config_path)
    print("omniconfig: ", config)

    config.image_dir = config.run_time_cache_dir
    config.audio_dir = config.run_time_cache_dir
    config.video_dir = config.run_time_cache_dir
    config.frame_dir = config.run_time_cache_dir

    DATA_PROCESS_PIPELINE = Pipeline([
        partial(tokenize_and_label_text_for_instruction_tuning, tokenizer=TOKENIZER, max_length=config.max_seq_len_for_preprocess, ignore_id=IGNORE_ID),
        partial(sample_frames_from_video, num_frames=config.num_frames_to_sample, video_dir=config.video_dir, frame_dir=config.frame_dir),  #!!! get frame indices
        partial(extract_audio_from_video, video_dir=config.video_dir, audio_dir=config.audio_dir)  # !!! get audio name
    ])
    DATA_LOADING_PIPELINE = Pipeline([
        partial(get_transformed_image, image_dir=config.image_dir),
        partial(load_video_frames, frame_dir=config.frame_dir, num_frames=config.num_frames_to_load),
        partial(get_audio_mels, audio_dir=config.audio_dir)
    ])
    print("==================== Step 2: setup omniconfig and pipelines done")

    # inputs that we can get from terminal or UI interfaces
    instruction = "Is the woman already in the room?"
    input = ""  # input can be empty 
    output = ""  # in running mode, output is always empty.
    image_path = ""  # None or image name
    video_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/videos/7UPGT.mp4"
    audio_path = ""

    image_name = None
    video_name = None
    audio_name = None
    if image_path:
        image_name = os.path.basename(image_path)
    if video_path:
        video_name = os.path.basename(video_path)
    if audio_path:
        audio_name = os.path.basename(audio_path)

    copy_file_to_dst(image_path, config.run_time_cache_dir)
    copy_file_to_dst(video_path, config.run_time_cache_dir)
    copy_file_to_dst(audio_path, config.run_time_cache_dir)


    formatted_input_e = {
        'instruction': instruction,
        'input': input,
        'output': "",
        'image': image_name,
        'audio': audio_name,
        'video': video_name,
    }
    
    model_input_e = DATA_LOADING_PIPELINE(DATA_PROCESS_PIPELINE(formatted_input_e))
    batch = [model_input_e]
    data_item = collate_multimodal_batches(batch, TOKENIZER)

    data_item.pop("labels")  #!!! remove these two keys for inference mode.
    data_item.pop("attention_mask")
    data_item['inference'] = True  #!!! if not set this, the model output will be logits rather than ids.
    eos_token_id = tokenizer.eos_token_id
    pad_token_id = tokenizer.pad_token_id
    print("data_item input_ids :", data_item["input_ids"])
    input_ids_list = data_item["input_ids"].tolist()[0]  #!!! get flattened 1D list
    input_ids_list = [x for x in input_ids_list if x != eos_token_id and x != pad_token_id]
    print("input_ids_list: ", input_ids_list)
    data_item["input_ids"] = torch.tensor(input_ids_list).unsqueeze(0)
    
    print("data_item: ", data_item)
    print("eos_token_id:", tokenizer.eos_token_id)
    print("input_ids: ", data_item["input_ids"])
    print_dict_to_file(data_item, "/Users/bangliu/Desktop/ChatSCI/Aeiva/outputs/data_item.txt")
    print("==================== Step 3: setup data item done")

    macaw_model.eval()
    with torch.no_grad():
        generate_ids = macaw_model(data_item)
    print("generate_ids: ", generate_ids)
    input_texts = TOKENIZER.batch_decode(data_item["input_ids"], skip_special_tokens=True, clean_up_tokenization_spaces=False)
    generated_texts = TOKENIZER.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    print("input_texts: ", input_texts)
    print("generated_texts: ", generated_texts)
    print("===================== Step 4: test inference done.")
