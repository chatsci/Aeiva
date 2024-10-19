#!/usr/bin/env python
# coding=utf-8
""" 
This module defines a chatbot demo using LLM providers with Gradio.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2024-04-27

Copyright (C) 2024 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""

import os
import json
import numpy as np
import soundfile as sf
import PIL
import gradio as gr
from datetime import datetime
from dotenv import load_dotenv

from aeiva.cognition.brain.llm.llm_client_old import LLMClient
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.cognition.brain.llm.llm_gateway_exceptions import LLMGatewayError
from aeiva.util.file_utils import is_image_file, is_video_file, is_audio_file
from aeiva.logger.logger import get_logger


# ****** Part I - Setup the LLM instance ******
logger = get_logger(__name__, level="INFO")

# Fetch sensitive data from environment variables
load_dotenv()  # This loads variables from a .env file into the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_default_api_key_here")  # Replace with your API key or set it as an environment variable

# Initialize LLMGatewayConfig directly
llm_gateway_config = LLMGatewayConfig(
    llm_model_name="gpt-4",  # Specify your desired model
    llm_api_key=OPENAI_API_KEY,
    llm_base_url="https://api.openai.com/v1",  # Update if using a different provider
    llm_api_version="v1",
    llm_embedding_model="text-embedding-ada-002",  # Update if needed
    llm_timeout=60,
    llm_max_input_tokens=2048,
    llm_max_output_tokens=512,
    llm_temperature=0.7,
    llm_top_p=0.9,
    llm_num_retries=3,
    llm_retry_backoff_factor=2,
    llm_retry_on_status=(429, 500, 502, 503, 504),
    llm_use_async=False,  # Set to False for synchronous operations
    llm_stream=False,     # Set to True if you want streaming responses
    llm_logging_level="INFO",
    # llm_enable_file_logging=True,
    # llm_log_file_path="logs/llm.log",
    # llm_enable_metrics=True,
    # llm_metrics_path="metrics/usage_metrics.json",
    llm_additional_params={
        # Add any additional parameters here
        # Example:
        # "logit_bias": {"50256": -100}
    },
)

# Initialize the LLM Instance
llm = LLMClient(llm_gateway_config)

# Initialize conversation history
history = []

# ****** Part II - Define the react functions for Gradio components ******

def add_text(history, text):
    """
    Handles adding user text input to the conversation history.

    Args:
        history (list): Current conversation history.
        text (str): User input text.

    Returns:
        tuple: Updated history and cleared text input.
    """
    history = history + [(text, None)]
    return history, gr.update(value="", interactive=True)

# Uncomment and implement if using file uploads
# def add_file(history, file):
#     """
#     Handles file uploads (images, videos, audio) and processes them.

#     Args:
#         history (list): Current conversation history.
#         file (file): Uploaded file.

#     Returns:
#         list: Updated conversation history.
#     """
#     if file is None:
#         return history

#     filename = file.name
#     if is_image_file(filename):
#         # Process image to generate caption
#         caption = generate_image_caption(file)
#         history = history + [((f"[Image]: {caption}",), None)]
#         logger.info(f"Processed image: {filename} with caption: {caption}")
#     elif is_video_file(filename):
#         # Process video to generate description
#         description = generate_video_description(file)
#         history = history + [((f"[Video]: {description}",), None)]
#         logger.info(f"Processed video: {filename} with description: {description}")
#     elif is_audio_file(filename):
#         # Process audio to generate transcription
#         transcription = transcribe_audio(file)
#         history = history + [((f"[Audio]: {transcription}",), None)]
#         logger.info(f"Processed audio: {filename} with transcription: {transcription}")
#     else:
#         history = history + [((f"[Unsupported File]: {filename}",), None)]
#         logger.warning(f"Unsupported file type: {filename}")

#     return history

def bot(history):
    """
    Generates a response from the LLM based on the conversation history.

    Args:
        history (list): Current conversation history.

    Returns:
        list: Updated conversation history with the bot's response.
    """
    try:
        # Construct the prompt from history
        prompt = construct_prompt(history)
        logger.info(f"Generating response for prompt: {prompt}")

        # Generate response using LLM
        response = llm(prompt)

        # Append the response to history
        history[-1][1] = response
        logger.info(f"Generated response: {response}")

        return history
    except LLMGatewayError as e:
        logger.error(f"LLM Generation Error: {e}")
        history[-1][1] = "Sorry, I encountered an error while generating a response."
        return history
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        history[-1][1] = "An unexpected error occurred."
        return history

def construct_prompt(history):
    """
    Constructs a prompt for the LLM based on the conversation history.

    Args:
        history (list): Current conversation history.

    Returns:
        str: Constructed prompt.
    """
    prompt = ""
    for user, bot_resp in history:
        prompt += f"User: {user}\n"
        if bot_resp:
            prompt += f"Bot: {bot_resp}\n"
    prompt += "Bot:"
    return prompt

def after_stop_recording_video(recorded_video):
    """
    Handles the event after stopping video recording.

    Args:
        recorded_video (str): Path to the recorded video.

    Returns:
        None
    """
    if recorded_video:
        logger.info(f"Recorded video: {recorded_video}")
    return

def after_stop_recording_audio(recorded_audio):
    """
    Handles the event after stopping audio recording.

    Args:
        recorded_audio (tuple): Tuple containing sample rate and audio data.

    Returns:
        None
    """
    if recorded_audio:
        sample_rate, audio_data = recorded_audio
        # Normalize audio_data to float32 in the range -1.0 to 1.0
        audio_data_normalized = audio_data.astype(np.float32) / np.abs(audio_data).max()

        # Save as a 16-bit PCM WAV file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_path = f"outputs/audio_output_{timestamp}.wav"  # Ensure this directory exists
        sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
        logger.info(f"Recorded audio saved at: {audio_path}")
    return

def after_clear_audio():
    """
    Handles the event after clearing audio input.

    Returns:
        None
    """
    logger.info("Audio input cleared.")
    return

def after_clear_video():
    """
    Handles the event after clearing video input.

    Returns:
        None
    """
    logger.info("Video input cleared.")
    return

def after_upload_image(image: PIL.Image.Image) -> None:
    """
    Handles the event after uploading an image.

    Args:
        image (PIL.Image.Image): Uploaded image.

    Returns:
        None
    """
    if image:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        image_path = f"outputs/uploaded_image_{timestamp}.jpg"  # Ensure this directory exists
        image.save(image_path)
        logger.info(f"Uploaded image saved at: {image_path}")
    return

def after_upload_video(uploaded_video: str) -> None:
    """
    Handles the event after uploading a video.

    Args:
        uploaded_video (str): Path to the uploaded video.

    Returns:
        None
    """
    if uploaded_video:
        logger.info(f"Uploaded video: {uploaded_video}")
    return

def after_upload_audio(uploaded_audio: tuple) -> None:
    """
    Handles the event after uploading an audio file.

    Args:
        uploaded_audio (tuple): Tuple containing sample rate and audio data.

    Returns:
        None
    """
    if uploaded_audio:
        sample_rate, audio_data = uploaded_audio
        # Normalize audio_data to float32 in the range -1.0 to 1.0
        audio_data_normalized = audio_data.astype(np.float32) / np.abs(audio_data).max()
        # Save as a 16-bit PCM WAV file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_path = f"outputs/uploaded_audio_{timestamp}.wav"  # Ensure this directory exists
        sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
        logger.info(f"Uploaded audio saved at: {audio_path}")
    return

def clear_history():
    """
    Clears the conversation history.

    Returns:
        list: Empty conversation history.
    """
    logger.info("Conversation history cleared.")
    return []

def regenerate_response(history):
    """
    Regenerates the last bot response.

    Args:
        history (list): Current conversation history.

    Returns:
        list: Updated conversation history with the regenerated response.
    """
    if not history:
        return history

    try:
        # Remove the last bot response
        if history[-1][1]:
            history[-1] = (history[-1][0], None)
            logger.info("Regenerating the last response.")
        
        # Re-generate the response
        prompt = construct_prompt(history)
        response = llm(prompt)
        history[-1] = (history[-1][0], response)
        logger.info(f"Regenerated response: {response}")
        return history
    except LLMGatewayError as e:
        logger.error(f"LLM Regeneration Error: {e}")
        history[-1][1] = "Sorry, I encountered an error while regenerating the response."
        return history
    except Exception as e:
        logger.error(f"Unexpected Error during regeneration: {e}")
        history[-1][1] = "An unexpected error occurred while regenerating the response."
        return history

def remove_last_turn(history):
    """
    Removes the last turn (user and bot messages) from the conversation history.

    Args:
        history (list): Current conversation history.

    Returns:
        list: Updated conversation history with the last turn removed.
    """
    if history:
        removed = history.pop()
        logger.info(f"Removed last turn: {removed}")
    return history

# ****** Part III - Setup the Gradio interface ******

if __name__ == "__main__":
    # Ensure output directories exist
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("metrics", exist_ok=True)

    # Define Gradio Blocks
    with gr.Blocks(title="Aeiva Chatbot with LLM Providers") as demo:
        gr.Markdown("""
        <h1 align="center">
            <img src="https://upload.wikimedia.org/wikipedia/en/b/bd/Doraemon_character.png",
            alt="Aeiva" border="0" style="height: 100px;" />
        </h1>
        <h2 align="center">AEIVA: An Evolving Intelligent Virtual Assistant</h2>
        <h5 align="center">If you like our project, please give us a star ⭐ on Github for the latest updates.</h5>
        <div align="center">
            <a href='https://github.com/chatsci/Aeiva'><img src='https://img.shields.io/badge/Github-Code-blue'></a>
            <a href="https://arxiv.org/abs/2304.14178"><img src="https://img.shields.io/badge/Arxiv-2304.14178-red"></a>
            <a href='https://github.com/chatsci/Aeiva/stargazers'><img src='https://img.shields.io/github/stars/chatsci/Aeiva.svg?style=social'></a>
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=1):  # Changed from scale=0.5 to scale=1
                with gr.Tab(label="Parameter Setting"):
                    gr.Markdown("# Parameters")
                    top_p = gr.Slider(
                        minimum=0.0, maximum=1.0, value=0.95, step=0.05, interactive=True, label="Top-p"
                    )
                    temperature = gr.Slider(
                        minimum=0.1, maximum=2.0, value=1.0, step=0.1, interactive=True, label="Temperature"
                    )
                    max_length_tokens = gr.Slider(
                        minimum=50, maximum=2048, value=512, step=50, interactive=True, label="Max Generation Tokens"
                    )
                    max_context_length_tokens = gr.Slider(
                        minimum=100, maximum=4096, value=2048, step=100, interactive=True, label="Max History Tokens"
                    )

                with gr.Row():
                    imagebox = gr.Image(type="pil", label="Upload Image")
                    videobox = gr.Video(label="Upload Video")
                    audiobox = gr.Audio(label="Upload Audio")

                with gr.Row():
                    # Replace gr.Camera with gr.Video(source="webcam", ...)
                    camera = gr.Video(label="Record Video")
                    microphone = gr.Audio(interactive=True, label="Record Audio")

            with gr.Column(scale=1):  # Changed from scale=0.5 to scale=1
                with gr.Row():
                    chatbot = gr.Chatbot([], elem_id="chatbot", height=730)

                with gr.Row():
                    with gr.Column(scale=4):  # Adjusted to integer scale
                        txt = gr.Textbox(
                            show_label=False,
                            placeholder="Enter text and press enter, or upload a file.",
                        )
                    
                    with gr.Column(scale=1, min_width=0):  # Adjusted to integer scale
                        btn = gr.UploadButton("📁 Upload", file_types=["image", "video", "audio"])

                with gr.Row(visible=True):
                    upvote_btn = gr.Button(value="👍 Upvote", interactive=True)
                    downvote_btn = gr.Button(value="👎 Downvote", interactive=True)
                    flag_btn = gr.Button(value="⚠️ Flag", interactive=True)
                    regenerate_btn = gr.Button(value="🔄 Regenerate", interactive=True)
                    clear_btn = gr.Button(value="🗑️ Clear History", interactive=True)
                    new_conv_btn = gr.Button(value="🧹 New Conversation", interactive=True)
                    del_last_btn = gr.Button(value="🗑️ Remove Last Turn", interactive=True)

        # Define Event Handlers
        txt.submit(add_text, [chatbot, txt], [chatbot, txt]).then(
            bot, chatbot, chatbot
        )
        
        # If using file uploads, uncomment and ensure `add_file` is implemented
        # btn.upload(add_file, [chatbot, btn], [chatbot]).then(
        #     bot, chatbot, chatbot
        # )
        
        imagebox.upload(after_upload_image, imagebox, None, queue=False)
        imagebox.clear(after_clear_video, None, None, queue=False)
        
        videobox.upload(after_upload_video, videobox, None, queue=False)
        videobox.clear(after_clear_video, None, None, queue=False)
        
        audiobox.upload(after_upload_audio, audiobox, None, queue=False)
        audiobox.clear(after_clear_audio, None, None, queue=False)
        
        # Replace `camera.upload` with `camera.change` for Gradio v4.x
        camera.change(after_stop_recording_video, camera, None, queue=False)
        camera.clear(after_clear_video, None, None, queue=False)
        
        # Replace `microphone.upload` with `microphone.change`
        microphone.change(after_stop_recording_audio, microphone, None, queue=False)
        microphone.clear(after_clear_audio, None, None, queue=False)
        
        regenerate_btn.click(regenerate_response, [chatbot], [chatbot])
        clear_btn.click(clear_history, None, [chatbot])
        new_conv_btn.click(clear_history, None, [chatbot])
        del_last_btn.click(remove_last_turn, [chatbot], [chatbot])

        # Launch the Gradio interface
        demo.launch(share=False)