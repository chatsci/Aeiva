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
import gradio as gr
import cv2
import sounddevice as sd
import soundfile as sf



def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.update(value="", interactive=False)


def add_file(history, file):
    history = history + [((file.name,), None)]
    return history


def after_stop_recording(recorded_video):
    print("video name: ", recorded_video)


def bot(history):
    response = "**That's cool!**"
    history[-1][1] = response
    return history

title_markdown = ("""
<h1 align="center">
    <a href="https://github.com/chatsci/Aeiva">
        <img src="https://upload.wikimedia.org/wikipedia/en/b/bd/Doraemon_character.png",
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
                chatbot = gr.Chatbot([], elem_id="chatbot", height=700)
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
    file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False).then(
        bot, chatbot, chatbot
    )

    camera.stop_recording(after_stop_recording, camera, None, queue=False)
    microphone.stop_recording(after_stop_recording, microphone, None, queue=False)

demo.launch()