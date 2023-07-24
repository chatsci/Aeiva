#!/usr/bin/env python
# coding=utf-8
""" 
This module contains the base class for all agent classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.

Reference: 
https://gradio.app/creating-a-chatbot/
https://github.com/X-PLUG/mPLUG-Owl/blob/main/serve/web_server.py

todo: develop and connect to the aeiva agent.
"""
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

import gradio as gr

from shutil import copyfile


#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
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
MODEL = MM_LLMs.from_pretrained(
    '/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/',
    config = model_config,
    # load_in_8bit=True,
    # torch_dtype=torch.float16,
    # device_map=device_map,
)
TOKENIZER =  get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)
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
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# set up some global variables for the chatbot
DIALOGUE_HISTORY = []
MM_FILES = {
    "image": None,
    "audio": None,
    "video": None
}
MODEL_INPUT = {
    'instruction': "",
    'input': "",
    'output': "",
    'image': None,
    'audio': None,
    'video': None
}

def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.update(value="", interactive=False)

def add_file(history, file):
    print(file.name)
    # To pass in a media file, we must pass like this: (filepath, Optional[alt_text]).
    history = history + [((file.name,), None)]

    # copy file to cache dir

    # update global dialog history for model

    # update global model input according to file type

    # update dialog history

    history = history + [(file.name, None)]
    return history

def bot(history):
    print("history: ", history)
    instruction = history[-1][0]  #!!!!
    print("instruction: ", instruction)
    formatted_input_e = {
        'instruction': instruction,
        'input': "",
        'output': "",
        'image': None,
        'audio': None,
        'video': None,
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

    MODEL.eval()
    with torch.no_grad():
        generate_ids = MODEL(data_item)
    print("generate_ids: ", generate_ids)
    input_texts = TOKENIZER.batch_decode(data_item["input_ids"], skip_special_tokens=True, clean_up_tokenization_spaces=False)
    generated_texts = TOKENIZER.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    response = generated_texts[0]  #!!!

    # response = "**That's cool!**"
    history[-1][1] = response
    return history

title_markdown = ("""
<h1 align="center">
    <a href="https://github.com/chatsci/Aeiva">
        <img src="https://github.com/chatsci/Aeiva/blob/main/assets/aeiva-logo-medusa.png",
        alt="Aeiva" border="0" style="margin: 0 auto; height: 200px;" />
    </a>
</h1>

<h2 align="center">
    Aeiva: A Multimodal and Embodied Agent that Learns from the Real and Virtual Worlds
</h2>

<h5 align="center">
    If you like our project, please give us a star ✨ on Github for latest update.
</h5>

<div align="center">
    <div style="display:flex; gap: 0.25rem;" align="center">
        <a href='https://github.com/chatsci/Aeiva'><img src='https://img.shields.io/badge/Github-Code-blue'></a>
        <a href="xxxxxx (arxiv paper link)"><img src="https://img.shields.io/badge/Arxiv-2304.14178-red"></a>
        <a href='https://github.com/chatsci/Aeiva/stargazers'><img src='https://img.shields.io/github/stars/X-PLUG/mPLUG-Owl.svg?style=social'></a>
    </div>
</div>
""")

with gr.Blocks(title="Aeiva Chatbot", css=None) as demo:

    gr.Markdown(title_markdown)

    with gr.Row():
        with gr.Column(scale=0.5):
            with gr.Row():
                imagebox = gr.Image(type="pil")
                videobox = gr.Video()
                audiobox = gr.Audio()
            with gr.Row():
                camera = gr.Video(source="webcam", streaming=True)
                microphone = gr.Audio(source="microphone", streaming=True)

        with gr.Column(scale=0.5):
            with gr.Row():
                chatbot = gr.Chatbot([], elem_id="chatbot").style(height=750)
            with gr.Row():
                with gr.Column(scale=0.8):
                    txt = gr.Textbox(
                        show_label=False,
                        placeholder="Enter text and press enter, or upload an image",
                    ).style(container=False)
                with gr.Column(scale=0.2, min_width=0):
                    btn = gr.UploadButton("📁", file_types=["image", "video", "audio"])

    txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
        bot, chatbot, chatbot
    )
    txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)
    file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False).then(
        bot, chatbot, chatbot
    )  # !!! we can remove .then part if we don't want to let the bot run when we upload a file.
    
    # imagebox.upload(add_image, imagebox, [chatbot], queue=False)
    # videobox.upload(lambda file: add_file2(chatbot, videobox, file, 'video'), [chatbot], queue=False)
    # audiobox.upload(process_audio, audiobox, [chatbot], queue=False)

demo.launch()