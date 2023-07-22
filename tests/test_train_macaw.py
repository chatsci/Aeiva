from functools import partial
from transformers import LlamaTokenizer
import aeiva.data.formatter  # For registering data formatters and processors.
from aeiva.util.token_utils import get_tokenizer
from transformers import CLIPConfig, WhisperConfig, LlamaTokenizer
from transformers import AutoConfig
from aeiva.model.macaw_model import MM_LLMs, MM_LLMs_Config
# test how to train model using pytorch lightning
from aeiva.trainer.pl_trainer import LightningTrainer, LoggingCallback
from torch.utils.data import DataLoader
from pytorch_lightning import Trainer
from aeiva.data.operator.loader import MultiModalDataset, collate_multimodal_batches
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger
import pytorch_lightning as pl
from functools import partial
from aeiva.data.util.dataitem_utils import get_transformed_image, load_video_frames, get_audio_mels
from aeiva.config import OmniConfig


# tokenizer_name_or_path = 'yahma/llama-7b-hf'  #!!! currently different with the author. Maybe we can just load from the downloaded tokenizer.
# TOKENIZER = get_tokenizer(tokenizer_name_or_path, add_special_tokens=True, special_tokens_dict=TOKENIZER_SPECIAL_TOKENS)

# TOKENIZER =  get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)


if __name__ == "__main__":
    # get model config
    clip_config = CLIPConfig.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    whisper_config = WhisperConfig.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/whisper_model/')
    llm_config = AutoConfig.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/llama7b_model/')
    print("config load done")

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
    print("model config: ", model_config)
    print("==================== Step 1: loading model config done")

    # load model separately 
    tokenizer = get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)
    model = MM_LLMs(config=model_config)
    print("model init done")

    model.image_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    model.video_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/clip_model/')
    model.audio_encoder.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/whisper_model/')
    model.llm.from_pretrained('/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/llama7b_model/')
    print("model config: ", model.llm.config)
    # model.llm.config.use_return_dict = True #!!!!!!!!!  # seems it is None and read only. I cannot revise it....
    model.llm.resize_token_embeddings(len(tokenizer))
    print("model loaded successfully")
    print("==================== Step 2: loading model done")


    # setup omniconfig
    config_path = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"
    OmniConfig.create_omni_config()
    config = OmniConfig.from_yaml(config_path)
    print("omniconfig: ", config)

    # setup the WandbLogger
    if config.use_wandb:
        wandb_logger = WandbLogger(project=config.wandb_project, log_model=True)
    print("wandb logger done")

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
    train_dataset = dataset  #!!!
    val_dataset = dataset  #!!!

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, collate_fn=partial(collate_multimodal_batches, tokenizer=tokenizer))
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, collate_fn=partial(collate_multimodal_batches, tokenizer=tokenizer))
    print("==================== Step 3: setup dataloader done")

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
    print("==================== Step 6: setup trainer done")

    trainer.fit(litmodel, train_loader, val_loader)
    print("==================== Step 7: training done")
