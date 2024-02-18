#!/usr/bin/env python
# coding=utf-8
""" 
This module defines a multimodal chatbot demo with gradio.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-13

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
import os
import numpy as np
from datetime import datetime

import soundfile as sf
import PIL
import gradio as gr

from aeiva.util.file_utils import is_image_file, is_video_file, is_audio_file
from aeiva.runner.runner import Runner
from aeiva.operator.task_ops import *


os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"  # NOTE: This is just a workarouond. Ensure a single OpenMP runtime is linked is the best solution.


# ****** Par I - Setup the model runner for chatbot ******
# setup config
ctx = {}
ctx["config_path"] = "/Users/bangliu/Documents/ChatSCI/Aeiva/configs/train_macaw.yaml"

# setup current input dataitem
ctx["instruction"] = ""  # will be set during the dialogue
ctx["input"] = ""  # input can be empty 
ctx["output"] = ""  # in inference mode, output is always empty.
ctx["image_path"] = ""  # accept from gradio
ctx["video_path"] = ""  # accept from gradio
ctx["audio_path"] = ""  # accept from gradio

# setup runner
runner = Runner()
op1 = runner.add_operator('load_config', load_config)
op2 = runner.add_operator('load_model', load_model)
op3 = runner.add_operator('setup_data_processor', setup_data_processor)
runner.stack_operators([op1, op2, op3])
ctx = runner(ctx)  # setup model and data processor for inference
print("Done with setup model and data processor for inference.")

runner.clear()
op4 = runner.add_operator('process_dataitem', process_dataitem)
op5 = runner.add_operator('infer', infer)
runner.stack_operators([op4, op5])  # setup runner for inference
print("Done with setup runner for inference.")


# ****** Part II - Define the react functions for gradio components ******
def add_text(history, text):
    global ctx
    history = history + [(text, None)]
    instruction = history[-1][0]  #!!! maybe use the full history?
    ctx["instruction"] = instruction  #!!! maybe define a dialogue history prompt?
    return history, gr.update(value="", interactive=False)


def add_file(history, file):
    global ctx
    history = history + [((file.name,), None)]
    if is_image_file(file.name):
        ctx["image_path"] = file.name
    elif is_video_file(file.name):
        ctx["video_path"] = file.name
    elif is_audio_file(file.name):
        ctx["audio_path"] = file.name
    else:
        raise Exception("Unsupported file type.")
    return history


def after_stop_recording_video(recorded_video):
    global ctx
    ctx["video_path"] = recorded_video
    print("recorded video: ", recorded_video)


def after_stop_recording_audio(recorded_audio):
    global ctx
    sample_rate, audio_data = recorded_audio
    # Normalize audio_data to float32 in the range -1.0 to 1.0
    audio_data_normalized = audio_data.astype(np.float32) / np.abs(audio_data).max()

    # Save as a 16-bit PCM WAV file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    audio_path = ctx["config"].run_time_cache_dir + f'output_{timestamp}.wav'
    sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
    print("recorded audio: ", audio_path)
    ctx["audio_path"] = audio_path


def after_clear_audio():
    global ctx
    ctx["audio_path"] = ""


def after_clear_video():
    global ctx
    ctx["video_path"] = ""


def after_upload_image(image: PIL.Image) -> None:
    global ctx
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    image_path = ctx["config"].run_time_cache_dir + f'uploaded_image_{timestamp}.jpg'
    image.save(image_path)
    print("uploaded image: ", image_path)
    ctx["image_path"] = image_path


def after_upload_video(uploaded_video: str) -> None:
    global ctx
    print("uploaded video: ", uploaded_video)
    ctx["video_path"] = uploaded_video


def after_upload_audio(uploaded_audio: tuple) -> None:
    global ctx
    sample_rate, audio_data = uploaded_audio
    # Normalize audio_data to float32 in the range -1.0 to 1.0
    audio_data_normalized = audio_data.astype(np.float32) / np.abs(audio_data).max()
    # Save as a 16-bit PCM WAV file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    audio_path = ctx["config"].run_time_cache_dir + f'output_{timestamp}.wav'
    sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
    print("uploaded audio: ", audio_path)
    ctx["audio_path"] = audio_path


def bot(history):
    global ctx
    #response = "**That's cool!**"
    ctx = runner(ctx)
    response = ctx["generated_texts"]

    history[-1][1] = response
    return history


# ****** Part III - Setup the gradio interface ******
if __name__ == "__main__":
    # setup gradio
    title_markdown = ("""
    <h1 align="center">
        <a href="https://github.com/chatsci/Aeiva">
            <img src="https://upload.wikimedia.org/wikipedia/en/b/bd/Doraemon_character.png",
            alt="Aeiva" border="0" style="margin: 0 auto; height: 200px;" />
        </a>
    </h1>

    <h2 align="center">
        AEIVA: An Evolving Intelligent Virtual Assistant
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

    # usage_markdown = ("""
    # <h2 align="center">
    #     Use Aeiva to chat with you!
    # </h2>
    # """)

    # theme='shivi/calm_seafoam'
    with gr.Blocks(title="Aeiva Chatbot", css=""".gradio {max-height: 100px;}""") as demo:

        gr.Markdown(title_markdown)

        with gr.Row():
            with gr.Column(scale=0.5):
                # gr.Markdown(usage_markdown)
                with gr.Tab(label="Parameter Setting"):
                    gr.Markdown("# Parameters")
                    top_p = gr.Slider(minimum=-0, maximum=1.0, value=0.95, step=0.05, interactive=True, label="Top-p",)
                    temperature = gr.Slider(minimum=0.1, maximum=2.0, value=1, step=0.1, interactive=True, label="Temperature",)
                    max_length_tokens = gr.Slider(minimum=0,maximum=512, value=512, step=8, interactive=True, label="Max Generation Tokens",)
                    max_context_length_tokens = gr.Slider(minimum=0, maximum=4096, value=2048, step=128, interactive=True, label="Max History Tokens",)
                with gr.Row():
                    imagebox = gr.Image(type="pil")
                    videobox = gr.Video()
                    audiobox = gr.Audio()
                with gr.Row():
                    camera = gr.Video(source="webcam", streaming=False, include_audio=True, format='mp4')
                    microphone = gr.Audio(source="microphone", streaming=False, interactive=True, format='wav')

            with gr.Column(scale=0.5):
                with gr.Row():
                    chatbot = gr.Chatbot([], elem_id="chatbot", height=730)
                with gr.Row():
                    with gr.Column(scale=0.8):
                        txt = gr.Textbox(
                            show_label=False,
                            placeholder="Enter text and press enter, or upload an image",
                        ).style(container=False)
                    with gr.Column(scale=0.2, min_width=0):
                        btn = gr.UploadButton("📁", file_types=["image", "video", "audio"])
                with gr.Row(visible=True) as button_row:
                    upvote_btn = gr.Button(value="👍  Upvote", interactive=True)
                    downvote_btn = gr.Button(value="👎  Downvote", interactive=True)
                    flag_btn = gr.Button(value="⚠️  Flag", interactive=True)
                    regenerate_btn = gr.Button(value="🔄  Regenerate", interactive=True)
                    clear_btn = gr.Button(value="🗑️  Clear history", interactive=True)
                    emptyBtn = gr.Button(value="🧹 New Conversation",interactive=True)
                    delLastBtn = gr.Button("🗑️ Remove Last Turn")

        txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
            bot, chatbot, chatbot
        )
        txt_msg.then(lambda: gr.update(interactive=True), None, [txt], queue=False)
        # file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False).then(
        #     bot, chatbot, chatbot
        # )
        file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False)

        imagebox.upload(after_upload_image, imagebox, None, queue=False)
        imagebox.clear(after_clear_video, None, None, queue=False)
        videobox.upload(after_upload_video, videobox, None, queue=False)
        videobox.clear(after_clear_video, None, None, queue=False)
        audiobox.upload(after_upload_audio, audiobox, None, queue=False)
        audiobox.clear(after_clear_audio, None, None, queue=False)

        camera.stop_recording(after_stop_recording_video, camera, None, queue=False)
        camera.clear(after_clear_video, None, None, queue=False)
        microphone.stop_recording(after_stop_recording_audio, microphone, None, queue=False)
        microphone.clear(after_clear_audio, None, None, queue=False)

    demo.launch(share=False)
