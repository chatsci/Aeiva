# Standard library imports
from functools import partial
import os

# Related third-party imports
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger
import torch
from transformers import AutoConfig, CLIPConfig, CLIPModel, LlamaModel, LlamaTokenizer, WhisperConfig, WhisperForConditionalGeneration

# Local application/library specific imports
from aeiva.config import OmniConfig
from aeiva.data.dataitem_operators import (
    extract_audio_from_video, get_audio_mels, get_transformed_image,
    load_video_frames, sample_frames_from_video, tokenize_and_label_text_for_instruction_tuning)
from aeiva.data.loader import collate_multimodal_batches, multimodal_loader
from aeiva.model.macaw_model import MM_LLMs, MM_LLMs_Config
from aeiva.trainer.pl_trainer import LightningTrainer, LoggingCallback
from aeiva.util.constants import IGNORE_ID
from aeiva.util.file_utils import copy_file_to_dst, ensure_dir
from aeiva.util.pipeline import Pipeline
from aeiva.util.token_utils import get_tokenizer


def load_config(ctx):
    config_path = ctx["config_path"]

    OmniConfig.create_omni_config()
    config = OmniConfig.from_json_or_yaml(config_path)
    parser = config.get_argparse_parser()
    args = parser.parse_args()
    config.update_from_args(args)

    ctx.update({"config": config})
    return ctx


def setup_model(ctx):
    config = ctx["config"]

    # setup pretrained model
    clip_config = CLIPConfig.from_pretrained(config.clip_model_name_or_path)
    whisper_config = WhisperConfig.from_pretrained(config.whisper_model_name_or_path)
    llm_config = AutoConfig.from_pretrained(config.llama7b_model_name_or_path)

    tokenizer =  get_tokenizer(config.tokenizer_name_or_path, tokenizer_cls=LlamaTokenizer)
    llm_config.vocab_size = len(tokenizer)  # !!! because macaw model added some special tokens.

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
        config.macaw_model_name_or_path,
        config = model_config,
        # load_in_8bit=True,
        # torch_dtype=torch.float16,
        # device_map=device_map,
    )

    ctx.update({"model": macaw_model, "tokenizer": tokenizer})
    return ctx


def init_model(ctx):
    config = ctx["config"]

    # setup pretrained model
    clip_config = CLIPConfig.from_pretrained(config.clip_model_name_or_path)
    whisper_config = WhisperConfig.from_pretrained(config.whisper_model_name_or_path)
    llm_config = AutoConfig.from_pretrained(config.llama7b_model_name_or_path)

    tokenizer =  get_tokenizer(config.tokenizer_name_or_path, tokenizer_cls=LlamaTokenizer)
    llm_config.vocab_size = len(tokenizer)  # !!! because macaw model added some special tokens.

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

    model = MM_LLMs(config=model_config)
    model.image_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    model.video_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    model.audio_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/whisper_model/')
    model.llm.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/llama7b_model/')
    # model.llm.config.use_return_dict = True #!!!!!!!!!  # seems it is None and read only. I cannot revise it....
    model.llm.resize_token_embeddings(len(tokenizer))
    print("model loaded successfully")

    ctx.update({"model": model, "tokenizer": tokenizer})
    return ctx


def setup_pipeline(ctx):
    config = ctx["config"]
    tokenizer = ctx["tokenizer"]

    data_preprocess_pipeline = Pipeline([
        partial(tokenize_and_label_text_for_instruction_tuning, tokenizer=tokenizer, max_length=config.max_seq_len_for_preprocess, ignore_id=IGNORE_ID),
        partial(sample_frames_from_video, num_frames=config.num_frames_to_sample, video_dir=config.run_time_cache_dir, frame_dir=config.run_time_cache_dir),  #!!! get frame indices
        partial(extract_audio_from_video, video_dir=config.run_time_cache_dir, audio_dir=config.run_time_cache_dir)  # !!! get audio name
    ])
    data_loading_pipeline = Pipeline([
        partial(get_transformed_image, image_dir=config.image_dir),
        partial(load_video_frames, frame_dir=config.frame_dir, num_frames=config.num_frames_to_load),
        partial(get_audio_mels, audio_dir=config.audio_dir)
    ])

    ctx.update({"data_preprocess_pipeline": data_preprocess_pipeline, "data_loading_pipeline": data_loading_pipeline})
    return ctx

def prepare_model_input(
        ctx
    ):
    config = ctx["config"]
    data_preprocess_pipeline = ctx["data_preprocess_pipeline"]
    data_loading_pipeline = ctx["data_loading_pipeline"]
    tokenizer = ctx["tokenizer"]
    instruction = ctx["instruction"]
    input = ctx["input"]
    video_path = ctx["video_path"]
    image_path = ctx["image_path"]
    audio_path = ctx["audio_path"]

    # setup raw input item
    image_name = os.path.basename(image_path) if image_path else None
    video_name = os.path.basename(video_path) if video_path else None
    audio_name = os.path.basename(audio_path) if audio_path else None

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
    
    # preprocess data item
    model_input_e = data_loading_pipeline(data_preprocess_pipeline(formatted_input_e))
    batch = [model_input_e]
    data_item = collate_multimodal_batches(batch, tokenizer)

    # postprocess data item for inference
    data_item.pop("labels")  #!!! remove these two keys for inference mode.
    data_item.pop("attention_mask")
    data_item['inference'] = True  #!!! if not set this, the model output will be logits rather than ids.
    eos_token_id = tokenizer.eos_token_id
    pad_token_id = tokenizer.pad_token_id
    input_ids_list = data_item["input_ids"].tolist()[0]  #!!! get flattened 1D list
    input_ids_list = [x for x in input_ids_list if x != eos_token_id and x != pad_token_id]
    data_item["input_ids"] = torch.tensor(input_ids_list).unsqueeze(0)

    ctx.update({"data_item": data_item})
    return ctx


def generate(ctx):
    data_item = ctx["data_item"]
    model = ctx["model"]
    tokenizer = ctx["tokenizer"]

    model.eval()
    with torch.no_grad():
        generate_ids = model(data_item)
    generated_texts = tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

    ctx.update({"generated_texts": generated_texts})
    return ctx


def prepare_pretrained_models_for_macaw(ctx):
    clip_path = ctx["config"].clip_model_name_or_path
    whisper_path = ctx["config"].whisper_model_name_or_path
    llama7b_path = ctx["config"].llama7b_model_name_or_path

    # save whisper, clip, and llama models for future use.
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16")
    whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base")
    llama7b_model = LlamaModel.from_pretrained("decapoda-research/llama-7b-hf")
    ensure_dir(clip_path)
    ensure_dir(whisper_path)
    ensure_dir(llama7b_path)
    clip_model.save_pretrained(clip_path)
    whisper_model.save_pretrained(whisper_path)
    llama7b_model.save_pretrained(llama7b_path)

    return ctx


def get_dataloader(ctx):
    config = ctx["config"]
    tokenizer = ctx["tokenizer"]
    pipeline = ctx["data_loading_pipeline"]

    if config.mode == "inference":
        config.batch_size = 1  #!!!!!!
    dataloader = multimodal_loader(config, tokenizer, pipeline)
    print("config: ", config)

    ctx.update({"dataloader": dataloader, "config": config})  #!!! return config?

    if config.mode == "train":
        train_loader = dataloader  #!!!!!!
        val_loader = dataloader  #!!!!!!
        ctx.update({"train_loader": train_loader, "val_loader": val_loader})
    return ctx


def inference(ctx):
    dataloader = ctx["dataloader"]
    model = ctx["model"]
    tokenizer = ctx["tokenizer"]
    max_samples_for_inference = 3 #!!!!!! changeg to config param later.

    num_samples = 0
    model.eval()
    with torch.no_grad():
        for data_item in dataloader:
            if num_samples >= max_samples_for_inference:
                break
            # postprocess data item for inference
            data_item.pop("labels")  #!!! remove these two keys for inference mode.
            data_item.pop("attention_mask")
            data_item['inference'] = True  #!!! if not set this, the model output will be logits rather than ids.
            eos_token_id = tokenizer.eos_token_id
            pad_token_id = tokenizer.pad_token_id
            input_ids_list = data_item["input_ids"].tolist()[0]  #!!! get flattened 1D list
            input_ids_list = [x for x in input_ids_list if x != eos_token_id and x != pad_token_id]
            data_item["input_ids"] = torch.tensor(input_ids_list).unsqueeze(0)
            #!!! we need to also remove the Response part of the item. revise later.

            generate_ids = model(data_item)
            generated_texts = tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            input_texts = tokenizer.batch_decode(data_item["input_ids"], skip_special_tokens=True, clean_up_tokenization_spaces=False)
            print("input_texts: ", input_texts)
            print("generated_texts: ", generated_texts)
            print("=====================================")
            num_samples += 1
        #!!!! NOTE: ctx is not updated yet. We may record the inference results in ctx here. revise later.
    return ctx

def get_logger(ctx):
    config = ctx["config"]

    # setup the WandbLogger
    if config.use_wandb:
        wandb_logger = WandbLogger(project=config.wandb_project, log_model=True)
    print("wandb logger done")

    ctx.update({"logger": wandb_logger})
    return ctx

def get_trainer(ctx):
    config = ctx["config"]
    model = ctx["model"]
    tokenizer = ctx["tokenizer"]

    litmodel = LightningTrainer(model, tokenizer, config)
    print("==================== Step 4: setup lightning model done")

    # set up the ModelCheckpoint
    checkpoint_callback = ModelCheckpoint(
        dirpath=config.output_dir,
        filename='ckpt-{epoch:02d}-{val_loss:.2f}.pt',
        every_n_train_steps=config.save_checkpoint_every_n_train_steps,
        save_top_k=-1 if config.always_save_checkpoint else 1, #!!! set always_save_checkpoint to be False if storage is limited
        verbose=True,
        monitor='val_loss',
        mode='min',
        save_last=True  # Save the latest model, regardless of its performance. The name is last.ckpt
    )

    model_callback = LoggingCallback(
        config.log_every_n_steps,
        config.accumulate_grad_batches
    )
    print("==================== Step 5: setup checkpoint callback done")

    # set up the Trainer
    trainer = pl.Trainer(
        # logger=wandb_logger,
        logger=None,
        callbacks=[checkpoint_callback, model_callback],
        max_steps=config.max_steps,
        accelerator='ddp' if config.ddp_backend else 'auto',
        # precision=16 if config.mixed_precision else 32,
        precision=32,
        deterministic=True,
        gradient_clip_val=config.max_grad_norm,
        accumulate_grad_batches=config.accumulate_grad_batches,
        val_check_interval=config.val_check_interval, #!!! this may make the training slow as we eval frequently. disable it to eval only after each epoch
        limit_val_batches=config.limit_val_batches, #!!! Not using full validation set. Disable it if evaluate after each epoch
        log_every_n_steps=config.log_every_n_steps
    )

    ctx.update({"trainer": trainer, "model": litmodel})
    return ctx

def train(ctx):
    trainer = ctx["trainer"]
    trainer.fit(ctx["model"], ctx["train_loader"], ctx["val_loader"])
    return ctx
