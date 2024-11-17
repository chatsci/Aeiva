#!/usr/bin/env python
# coding=utf-8
"""
Multimodal Chatbot using LLM with function call capabilities and tool integration via APIs.
Updated to include image, audio, and video inputs based on the old UI design and compatible with Gradio 5.1.
"""

import os
import gradio as gr
import json
from dotenv import load_dotenv
import numpy as np
from datetime import datetime
import soundfile as sf
import PIL

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.logger.logger import get_logger

# Setup logger
logger = get_logger(__name__, level="INFO")

# Load environment variables (API keys, etc.)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_default_api_key_here")

# Initialize LLM client with function call capability
llm_gateway_config = LLMGatewayConfig(
    llm_model_name="gpt-4o-mini",  # Use the model that supports litellm's function calling and streaming
    llm_api_key=OPENAI_API_KEY,
    llm_base_url="https://api.openai.com/v1",
    llm_max_input_tokens=2048,
    llm_max_output_tokens=512,
    llm_use_async=True,    # Enable asynchronous mode
    llm_stream=True,       # Enable streaming
)
llm = LLMClient(llm_gateway_config)

# Load tool schema from JSON files
def load_tool_schema(api_name):
    current_path = os.path.dirname(os.path.abspath(__file__))
    # Adjust the project root as necessary
    project_root = os.path.abspath(os.path.join(current_path, "../../.."))
    path = os.path.join(
        project_root,
        f"src/aeiva/tool/api/{api_name}/{api_name}.json",
    )
    with open(path, "r") as file:
        return json.load(file)

# Ensure the uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Global context to store paths of uploaded files
context = {
    "image_path": "",
    "audio_path": "",
    "video_path": "",
}

# Gradio chatbot handler
async def bot(user_input, history):
    """
    Handles chatbot logic and dynamically invokes functions via LLM function calls.

    Args:
        user_input (str): The user's input.
        history (list): Conversation history as list of dicts.

    Yields:
        tuple: Updated history and an empty string to clear the input box.
    """
    try:
        # Append user's message to history
        history.append({"role": "user", "content": user_input})
        # Append an empty assistant response
        history.append({"role": "assistant", "content": ""})
        yield history, ''

        # Construct the messages for LLM
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
        logger.info(f"Messages: {messages}")

        # Load tools
        tools = [
            load_tool_schema("test_operation"),
            # Add more tools as needed
        ]

        # Get the response stream from LLM
        stream = llm(messages, tools=tools)
        assistant_message = ''
        async for chunk in stream:
            assistant_message += chunk
            history[-1]["content"] = assistant_message
            yield history, ''
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        history[-1]["content"] = "An unexpected error occurred."
        yield history, ''

# Handlers for multimodal inputs
def handle_image_upload(image: PIL.Image):
    if image is not None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        image_path = f"uploads/uploaded_image_{timestamp}.jpg"
        image.save(image_path)
        context["image_path"] = image_path
        return "User uploaded an image."
    return ""

def handle_video_upload(video):
    if video is not None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        video_path = f"uploads/uploaded_video_{timestamp}.mp4"
        with open(video_path, "wb") as f:
            f.write(video.read())
        context["video_path"] = video_path
        return "User uploaded a video."
    return ""

def handle_audio_upload(audio):
    if audio is not None:
        sample_rate, audio_data = audio
        # Normalize audio_data to float32 in the range -1.0 to 1.0
        audio_data_normalized = audio_data.astype(np.float32) / np.abs(audio_data).max()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_path = f"uploads/uploaded_audio_{timestamp}.wav"
        sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
        context["audio_path"] = audio_path
        return "User uploaded an audio file."
    return ""

def handle_upload(file):
    """
    Handles file uploads and delegates to specific handlers based on file type.

    Args:
        file: Uploaded file object.

    Returns:
        str: Message indicating the upload status.
    """
    if file is None:
        return ""
    if file.type.startswith("image"):
        return handle_image_upload(file)
    elif file.type.startswith("video"):
        return handle_video_upload(file)
    elif file.type.startswith("audio"):
        return handle_audio_upload(file)
    else:
        return "Unsupported file type uploaded."

def clear_media():
    context["image_path"] = ""
    context["audio_path"] = ""
    context["video_path"] = ""
    return ""

# Define custom CSS
# custom_css = """
# <style>
# /* Style for the UploadButton */
# .upload-button {
#     width: 40px !important; /* Further reduced width */
#     height: 40px !important; /* Match the Textbox height */
#     padding: 5px;
#     font-size: 16px;
#     border-radius: 5px;
# }

# /* Optional: Adjust the Textbox height to match the button */
# .input-textbox textarea {
#     height: 40px !important; /* Ensure the Textbox height matches the button */
#     resize: none; /* Prevent resizing */
#     font-size: 16px;
# }
# </style>
# """

# Gradio interface
if __name__ == "__main__":
    with gr.Blocks(title="Multimodal LLM Chatbot with Tools") as demo:
        # Inject custom CSS
        # gr.HTML(custom_css)
        
        # Header Section
        gr.Markdown("""
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
            If you like our project, please give us a star ✨ on Github for the latest update.
        </h5>

        <div align="center">
            <div style="display:flex; gap: 0.25rem;" align="center">
                <a href='https://github.com/chatsci/Aeiva'><img src='https://img.shields.io/badge/Github-Code-blue'></a>
                <a href="https://arxiv.org/abs/2304.14178"><img src="https://img.shields.io/badge/Arxiv-2304.14178-red"></a>
                <a href='https://github.com/chatsci/Aeiva/stargazers'><img src='https://img.shields.io/github/stars/X-PLUG/mPLUG-Owl.svg?style=social'></a>
            </div>
        </div>
        """)

        # Main Layout: Two Columns
        with gr.Row():
            # Left Column: Parameter Settings and Multimodal Inputs
            with gr.Column(scale=1):
                # Parameter Settings Tab
                with gr.Tab(label="Parameter Setting"):
                    gr.Markdown("# Parameters")
                    top_p = gr.Slider(
                        minimum=0,
                        maximum=1.0,
                        value=0.95,
                        step=0.05,
                        interactive=True,
                        label="Top-p"
                    )
                    temperature = gr.Slider(
                        minimum=0.1,
                        maximum=2.0,
                        value=1.0,
                        step=0.1,
                        interactive=True,
                        label="Temperature"
                    )
                    max_length_tokens = gr.Slider(
                        minimum=0,
                        maximum=512,
                        value=512,
                        step=8,
                        interactive=True,
                        label="Max Generation Tokens"
                    )
                    max_context_length_tokens = gr.Slider(
                        minimum=0,
                        maximum=4096,
                        value=2048,
                        step=128,
                        interactive=True,
                        label="Max History Tokens"
                    )

                # Multimodal Inputs Section
                with gr.Row():
                    imagebox = gr.Image(type="pil", label="Upload Image")
                    videobox = gr.File(label="Upload Video", file_types=["video"])
                    audiobox = gr.Audio(label="Upload Audio", type="numpy")

                with gr.Row():
                    record_videobox = gr.Video(label="Record Video")
                    record_audiobox = gr.Audio(label="Record Audio")

                # Clear Media Button
                with gr.Row():
                    clear_media_btn = gr.Button("🧹 Clear Media", variant="secondary")

            # Right Column: Chat Interface and Action Buttons
            with gr.Column(scale=1):
                # Chatbot Component
                chatbot = gr.Chatbot(
                    [],
                    type="messages",  # Specify type as 'messages'
                    elem_id="chatbot",
                    height=730
                )

                # Input Textbox and Upload Button
                with gr.Row():
                    with gr.Column(scale=4, min_width=300):
                        txt = gr.Textbox(
                            show_label=False,
                            placeholder="Enter text and press enter, or upload an image/video/audio",
                            lines=1,
                            elem_classes=["input-textbox"]  # Assign a CSS class for styling
                        )
                    with gr.Column(scale=1, min_width=100):
                        btn = gr.UploadButton("📁", file_types=["image", "video", "audio"], elem_classes=["upload-button"])
                        # Changed the button label to an icon for a more compact look

                # Action Buttons Placed Below the Input Box
                with gr.Row():
                    upvote_btn = gr.Button("👍 Upvote", interactive=True)
                    downvote_btn = gr.Button("👎 Downvote", interactive=True)
                    flag_btn = gr.Button("⚠️ Flag", interactive=True)
                    regenerate_btn = gr.Button("🔄 Regenerate", interactive=True)
                    clear_history_btn = gr.Button("🗑️ Clear History", interactive=True)
                    new_conv_btn = gr.Button("🧹 New Conversation", interactive=True)
                    del_last_turn_btn = gr.Button("🗑️ Remove Last Turn", interactive=True)

        # Define interactions

        # Text input submission
        txt.submit(
            bot,
            inputs=[txt, chatbot],
            outputs=[chatbot, txt]
        ).then(
            lambda: gr.update(value=""),  # Clear textbox after submission
            None,
            [txt],
            queue=False
        )

        # File upload (image/video/audio)
        btn.upload(
            lambda file: handle_upload(file),
            inputs=btn,
            outputs=txt,  # Set message in textbox to trigger bot
            queue=True
        )

        # Image upload
        imagebox.upload(
            lambda img: handle_image_upload(img),
            inputs=imagebox,
            outputs=txt,  # Set message in textbox to trigger bot
            queue=True
        )

        # Video upload
        videobox.upload(
            lambda vid: handle_video_upload(vid),
            inputs=videobox,
            outputs=txt,  # Set message in textbox to trigger bot
            queue=True
        )

        # Audio upload
        audiobox.upload(
            lambda aud: handle_audio_upload(aud),
            inputs=audiobox,
            outputs=txt,  # Set message in textbox to trigger bot
            queue=True
        )

        # Record Video
        record_videobox.change(
            lambda vid: handle_video_upload(vid),
            inputs=record_videobox,
            outputs=txt,  # Set message in textbox to trigger bot
            queue=True
        )

        # Record Audio
        record_audiobox.change(
            lambda aud: handle_audio_upload(aud),
            inputs=record_audiobox,
            outputs=txt,  # Set message in textbox to trigger bot
            queue=True
        )

        # Clear Media Button
        clear_media_btn.click(
            clear_media,
            inputs=None,
            outputs=None,
            queue=False
        )

        # Action Buttons Functionality (To Be Implemented)
        # Clear History
        clear_history_btn.click(
            lambda: ([], ""),
            inputs=None,
            outputs=[chatbot, txt],
            queue=False
        )

        # New Conversation
        new_conv_btn.click(
            lambda: ([], ""),
            inputs=None,
            outputs=[chatbot, txt],
            queue=False
        )

        # Remove Last Turn (Removes the last user and assistant messages)
        del_last_turn_btn.click(
            lambda history: history[:-2] if len(history) >= 2 else history,
            inputs=chatbot,
            outputs=chatbot,
            queue=False
        )

        # Launch the app
        demo.launch(share=False)