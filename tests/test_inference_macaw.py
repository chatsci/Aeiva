from functools import partial
from transformers import LlamaTokenizer
import aeiva.data.formatter  # For registering data formatters and processors.
from aeiva.util.token_utils import get_tokenizer
from aeiva.util.json_utils import load_json, dump_json
from aeiva.util.file_utils import ensure_dir
from transformers import CLIPModel, LlamaModel
from transformers import WhisperForConditionalGeneration
from transformers import CLIPProcessor, CLIPModel, CLIPConfig, LlamaConfig, WhisperConfig, WhisperModel, LlamaModel, LlamaTokenizer
from transformers import AutoConfig, AutoModel
from aeiva.model.macaw_model import MM_LLMs, MM_LLMs_Config
import clip
import whisper
from functools import partial
from aeiva.data.util.dataitem_utils import get_transformed_image, load_video_frames, get_audio_mels
from aeiva.config import OmniConfig
from aeiva.data.operator.loader import MultiModalDataset, collate_multimodal_batches
from torch.utils.data import DataLoader
import torch


if __name__ == "__main__":

    # # save whisper, clip, and llama models for future use.
    # from transformers import CLIPModel, LlamaModel
    # clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16")
    # from transformers import WhisperForConditionalGeneration
    # whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base")
    # llama7b_model = LlamaModel.from_pretrained("decapoda-research/llama-7b-hf")
    # ensure_dir('trained_models/clip_model/')
    # ensure_dir('trained_models/whisper_model/')
    # ensure_dir('trained_models/llama7b_model/')
    # clip_model.save_pretrained('trained_models/clip_model/')
    # whisper_model.save_pretrained('trained_models/whisper_model/')
    # llama7b_model.save_pretrained('trained_models/llama7b_model/')



    # test how to load a model for inference
    # load model
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
    print("==================== Step 1: setup config done.")

    macaw_model = MM_LLMs.from_pretrained(
        '/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/',
        config = model_config,
        # load_in_8bit=True,
        # torch_dtype=torch.float16,
        # device_map=device_map,
    )
    print("==================== Step 2: loading pretrained model done")


    # setup omniconfig
    config_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"
    OmniConfig.create_omni_config()
    config = OmniConfig.from_yaml(config_path)
    print("omniconfig: ", config)

    # setup dataloader
    DATA_LOADING_PIPELINE = [
        partial(get_transformed_image, image_dir=config.image_dir),
        partial(load_video_frames, frame_dir=config.frame_dir, num_frames=config.num_frames_to_load),
        partial(get_audio_mels, audio_dir=config.audio_dir)
        # partial(generate_image_id, id_generator=ID_GENERATOR),
        # partial(generate_audio_id, id_generator=ID_GENERATOR),
        # partial(generate_video_id, id_generator=ID_GENERATOR)
    ]

    dataset = MultiModalDataset(config, tokenizer, DATA_LOADING_PIPELINE)
    dataloader = DataLoader(dataset, batch_size=config.batch_size, collate_fn=partial(collate_multimodal_batches, tokenizer=tokenizer))
    print("==================== Step 3: setup dataloader done")

    data_item = next(iter(dataloader))
    # prepare input for model inference
    data_item.pop("labels")  #!!! remove these two keys for inference mode.
    data_item.pop("attention_mask")
    data_item['inference'] = True  #!!! if not set this, the model output will be logits rather than ids.

    macaw_model.eval()
    with torch.no_grad():
        generate_ids = macaw_model(data_item)
    print("generate_ids: ", generate_ids)
    input_texts = tokenizer.batch_decode(data_item["input_ids"], skip_special_tokens=True, clean_up_tokenization_spaces=False)
    generated_texts = tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    print("input_texts: ", input_texts)
    print("generated_texts: ", generated_texts)
    print("===================== Step 4: test inference done.")
