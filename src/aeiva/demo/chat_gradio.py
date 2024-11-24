# demo_agent.py

import os
import gradio as gr
import json
from dotenv import load_dotenv
import numpy as np
from datetime import datetime
import soundfile as sf
import PIL

import sys
import threading
import asyncio
import logging
import time
import queue  # Import thread-safe queue

from aeiva.logger.logger import get_logger
from aeiva.util.file_utils import from_json_or_yaml
from aeiva.agent.agent import Agent
from aeiva.event.event import Event

# Setup logger
logger = get_logger(__name__, level="INFO")

# Load environment variables (API keys, etc.)
load_dotenv()

# Initialize the Agent using the from_config class method
config_path = 'agent_config.yaml'  # Ensure this path is correct
config_dict = from_json_or_yaml(config_path)

try:
    agent = Agent(config_dict)
    agent.setup()
    logger.info("Agent initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Agent: {e}")
    agent = None

# Function to run the Agent's run method in a separate thread
def run_agent(agent_instance):
    try:
        asyncio.run(agent_instance.run())
    except Exception as e:
        logger.error(f"Error running Agent: {e}")

# Start the Agent in a separate daemon thread
if agent:
    agent_thread = threading.Thread(target=run_agent, args=(agent,), daemon=True)
    agent_thread.start()
    logger.info("Agent run thread started.")

# Initialize a thread-safe queue to receive responses from the Agent
response_queue = queue.Queue()

# Define a handler for 'response.gradio' events
def handle_response_gradio(event: Event):
    response = event.payload
    response_queue.put_nowait(response)  # Put response into the thread-safe queue
    logger.info(f"Received 'response.gradio' event: {response}")

# Register the handler with the Agent's EventBus
if agent:
    agent.event_bus.on('response.gradio')(handle_response_gradio)
    logger.info("Registered handler for 'response.gradio' events.")

# Define handlers for multimodal inputs

def handle_image_upload(image: PIL.Image.Image):
    if image is not None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        image_path = f"uploads/uploaded_image_{timestamp}.jpg"
        try:
            image.save(image_path)
            logger.info(f"Image uploaded and saved to {image_path}")
            return "User uploaded an image."
        except Exception as e:
            logger.error(f"Error saving uploaded image: {e}")
            return "Failed to upload image."
    return ""

def handle_video_upload(video):
    if video is not None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        video_path = f"uploads/uploaded_video_{timestamp}.mp4"
        try:
            with open(video_path, "wb") as f:
                f.write(video.read())
            logger.info(f"Video uploaded and saved to {video_path}")
            return "User uploaded a video."
        except Exception as e:
            logger.error(f"Error saving uploaded video: {e}")
            return "Failed to upload video."
    return ""

def handle_audio_upload(audio):
    if audio is not None:
        try:
            sample_rate, audio_data = audio
            # Normalize audio_data to float32 in the range -1.0 to 1.0
            audio_data_normalized = audio_data.astype(np.float32) / np.abs(audio_data).max()
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            audio_path = f"uploads/uploaded_audio_{timestamp}.wav"
            sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
            logger.info(f"Audio uploaded and saved to {audio_path}")
            return "User uploaded an audio file."
        except Exception as e:
            logger.error(f"Error saving uploaded audio: {e}")
            return "Failed to upload audio."
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
    """
    Clears the uploaded media paths.
    """
    # Implement any necessary logic to clear media paths or data
    logger.info("Cleared uploaded media paths.")
    return ""


async def bot(user_input, history):
    """
    Handles chatbot logic by emitting perception.gradio events to the Agent and retrieving responses.
    """
    if agent is None:
        logger.error("Agent is not initialized.")
        history.append({"role": "assistant", "content": "Agent is not initialized."})
        yield history, ''
        return

    try:
        # Append user's message to history
        history.append({"role": "user", "content": user_input})
        # Append an empty assistant response
        history.append({"role": "assistant", "content": ""})
        yield history, ''  # Display the user's message
        logger.info(f"User input appended to history: {user_input}")

        stream = config_dict["llm_gateway_config"]["llm_stream"]
        use_async = config_dict["llm_gateway_config"]["llm_use_async"]

        # Emit the 'perception.gradio' event with stream=True
        emit_future = asyncio.run_coroutine_threadsafe(
            agent.event_bus.emit('perception.gradio', payload=user_input),  # TODO: maybe simplify payload, Agent can directly read stream and use_async from config.
            agent.event_bus.loop
        )
        emit_future.result()  # Ensure the event is emitted
        logger.info(f"Emitted 'perception.gradio' event with payload: {user_input} | Stream: {stream}")

        assistant_message = ''
        if stream:
            while True:
                try:
                    # Non-blocking response retrieval from the thread-safe queue with timeout
                    response = await asyncio.wait_for(
                        asyncio.to_thread(response_queue.get, True, 30),
                        timeout=30
                    )
                    logger.info(f"Retrieved response from queue: {response}")
                    if response == "<END_OF_RESPONSE>":
                        logger.info("Received end of response signal.")
                        break
                    assistant_message += response
                    # Create a new history list to ensure Gradio detects the update
                    new_history = history.copy()
                    new_history[-1]["content"] = assistant_message
                    logger.info(f"Yielding updated history: {new_history}")
                    yield new_history, ''
                except asyncio.TimeoutError:
                    logger.warning("Timeout: No response received from Agent.")
                    # Create a new history list to ensure Gradio detects the update
                    new_history = history.copy()
                    new_history[-1]["content"] = "I'm sorry, I didn't receive a response in time."
                    yield new_history, ''
                    break
        else:
            try:
                # Non-blocking response retrieval from the thread-safe queue with timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(response_queue.get, True, 30),
                    timeout=30
                )
                logger.info(f"Retrieved response from queue: {response}")
                assistant_message += response
                # Create a new history list to ensure Gradio detects the update
                new_history = history.copy()
                new_history[-1]["content"] = assistant_message
                logger.info(f"Yielding updated history: {new_history}")
                yield new_history, ''
            except asyncio.TimeoutError:
                logger.warning("Timeout: No response received from Agent.")
                # Create a new history list to ensure Gradio detects the update
                new_history = history.copy()
                new_history[-1]["content"] = "I'm sorry, I didn't receive a response in time."
                yield new_history, ''

    except Exception as e:
        logger.error(f"Unexpected Error in bot function: {e}")
        # Create a new history list to ensure Gradio detects the update
        new_history = history.copy()
        new_history[-1]["content"] = "An unexpected error occurred."
        yield new_history, ''

if __name__ == "__main__":
    with gr.Blocks(title="Multimodal LLM Chatbot with Tools") as demo:

        # Header Section
        gr.Markdown("""
        <h1 align="center">
            <a href="https://github.com/chatsci/Aeiva">
                <img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png",
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
            with gr.Column(scale=1, min_width=700):
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
            with gr.Column(scale=1, min_width=700):
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

        # Text input submission with streaming
        txt.submit(
            bot,
            inputs=[txt, chatbot],
            outputs=[chatbot, txt],
            queue=True,    # Enable queue for better performance
            # stream=True    # Enable streaming
        )
        # Removed the .then callback to prevent layout shifts

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
    demo.launch(share=True)