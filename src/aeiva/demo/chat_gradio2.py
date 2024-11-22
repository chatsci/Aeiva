#!/usr/bin/env python
# coding=utf-8
"""
Enhanced Multimodal Chatbot with VS Code-like UI using Gradio 5.1.
Includes file browser, file viewer/editor, terminal log, and chatbot interface.
"""

import os
import gradio as gr
import json
from dotenv import load_dotenv
import numpy as np
from datetime import datetime
import soundfile as sf
import PIL
import logging

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.logger.logger import get_logger

# Import the custom Log component
from aeiva.demo.gradio_log_component import Log  # Ensure log.py is in the same directory

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
async def bot(user_input, history, top_p, temperature, max_length_tokens, max_context_length_tokens):
    """
    Handles chatbot logic and dynamically invokes functions via LLM function calls.

    Args:
        user_input (str): The user's input.
        history (list): Conversation history as list of dicts.
        top_p (float): Top-p sampling parameter.
        temperature (float): Temperature parameter.
        max_length_tokens (int): Maximum generation tokens.
        max_context_length_tokens (int): Maximum history tokens.

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
        stream = llm(messages, tools=tools, top_p=top_p, temperature=temperature,
                    max_length_tokens=max_length_tokens, max_context_length_tokens=max_context_length_tokens)
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
        logger.info(f"Image uploaded: {image_path}")
        return "User uploaded an image."
    return ""

def handle_video_upload(video):
    if video is not None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        video_path = f"uploads/uploaded_video_{timestamp}.mp4"
        with open(video_path, "wb") as f:
            f.write(video.read())
        context["video_path"] = video_path
        logger.info(f"Video uploaded: {video_path}")
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
        logger.info(f"Audio uploaded: {audio_path}")
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
        logger.warning(f"Unsupported file type uploaded: {file.type}")
        return "Unsupported file type uploaded."

def clear_media():
    context["image_path"] = ""
    context["audio_path"] = ""
    context["video_path"] = ""
    logger.info("Media cleared.")
    return ""

# File browser handler (simple implementation)
def list_files(folder_path="uploads"):
    """
    Lists files in the specified folder.

    Args:
        folder_path (str): Path to the folder.

    Returns:
        list: List of file names.
    """
    try:
        files = os.listdir(folder_path)
        # Optionally filter files based on extensions or other criteria
        logger.info(f"Listing files in {folder_path}: {files}")
        return files
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return []

# File viewer/editor handler
def view_file(file_name, file_type):
    """
    Returns the content of the file based on its type.

    Args:
        file_name (str): Name of the file.
        file_type (str): Type of the file (markdown, code, etc.).

    Returns:
        str: Content of the file or appropriate message.
    """
    file_path = os.path.join("uploads", file_name)
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return "File not found."

    try:
        if file_type in ["Markdown", "Code", "Text"]:
            with open(file_path, "r") as f:
                content = f.read()
            logger.info(f"File {file_type} viewed: {file_path}")
            return content
        elif file_type == "3D":
            # Placeholder for 3D viewer, can be integrated with a custom component
            logger.info(f"3D Viewer requested for: {file_path}")
            return f"3D Viewer for {file_name} is not implemented yet."
        else:
            logger.warning(f"Unsupported file type requested: {file_type}")
            return "Unsupported file type."
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return "Error reading file."

# Define custom CSS (optional)
custom_css = """
<style>
/* Add your custom CSS here */
.app {
    max-width: 100% !important;
}

#chatbot {
    height: 400px;
    overflow-y: auto;
}

.input-textbox textarea {
    height: 40px !important; /* Ensure the Textbox height matches the button */
    resize: none; /* Prevent resizing */
    font-size: 16px;
}
.upload-button {
    width: 40px !important; /* Further reduced width */
    height: 40px !important; /* Match the Textbox height */
    padding: 5px;
    font-size: 16px;
    border-radius: 5px;
}
</style>
"""

# Gradio interface
if __name__ == "__main__":
    with gr.Blocks(title="Enhanced Multimodal LLM Chatbot", theme='shivi/calm_seafoam') as demo:
        # Inject custom CSS
        gr.HTML(custom_css)

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

        # Main Layout: Three Columns (Left, Middle, Right)
        with gr.Row():
            # Left Column: File Browser (1/5 width)
            with gr.Column(scale=1, min_width=200):
                gr.Markdown("## File Browser")
                
                with gr.Group():
                    with gr.Row():
                        file_3 = gr.FileExplorer(
                            scale=1,
                            glob="**/components/**/*.py",
                            value=["themes/utils"],
                            file_count="single",
                            root_dir="/Users/bangliu/Documents/",
                            ignore_glob="**/__init__.py",
                            elem_id="file",
                        )

                        code = gr.Code(lines=30, scale=2, language="python")

            # Middle Column: File Viewer/Editor and Terminal (3/5 width)
            with gr.Column(scale=3, min_width=600):
                gr.Markdown("## File Viewer/Editor")
                file_tabs = gr.Tabs()

                with file_tabs:
                    with gr.TabItem("Markdown"):
                        markdown_view = gr.Markdown(value="Select a file to view.")
                    
                    with gr.TabItem("Code"):
                        code_view = gr.Code(language="python", value="Select a file to view.")
                    
                    with gr.TabItem("Text"):
                        text_view = gr.Textbox(value="Select a file to view.", lines=20)
                    
                    with gr.TabItem("3D"):
                        gr.HTML("<p>3D Viewer is not implemented yet.</p>")
                
                # Terminal Window (Bottom 1/4 height)
                gr.Markdown("## Terminal Output")
                terminal_log = Log(log_file="/tmp/gradio_log.txt", dark=True, height=240)

            # Right Column: Chatbot UI (1/5 width)
            with gr.Column(scale=1, min_width=300):
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

                # Chatbot Component
                chatbot = gr.Chatbot(
                    [],
                    type="messages",  # Specify type as 'messages'
                    elem_id="chatbot",
                    height=400
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
                    inputs=[txt, chatbot, top_p, temperature, max_length_tokens, max_context_length_tokens],
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

                # Action Buttons Functionality

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

                # Placeholder for Upvote, Downvote, Flag, Regenerate buttons
                # Implement these functionalities as needed

        # Reintroduce the Log component
        with gr.Row():
            gr.Markdown("## Terminal Output")
            terminal_log = Log(log_file="/tmp/gradio_log.txt", dark=True, height=240)

        # Optionally, define callbacks or interactions for the Log component if needed

    # Launch the app
    demo.launch(share=False)