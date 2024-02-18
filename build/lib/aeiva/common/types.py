from typing import TypedDict, Optional, Any
import torch
from aeiva.config import OmniConfig


class DataItem(TypedDict):
    r"""DataItem is a dictionary that contains all the information for a single data item.
    """
    instruction: str  # instruction text
    input: Optional[str]  # input text
    output: Optional[str]  # output text
    text: Optional[str]  # text field. How it is formed depends on the task.

    image: Optional[str]  # image name or path
    transformed_image: Optional[torch.Tensor]  # transformed image tensor

    audio: Optional[str]  # audio name or path
    audio_mels: Optional[torch.Tensor]  # audio melspectrogram tensor

    video: Optional[str]  # video name or path
    sampled_video_frame_indices: Optional[list[int]]  # sampled video frame indices
    video_frames: Optional[torch.Tensor]  # video frames tensor


class DataSet(TypedDict):
    r"""DataSet is a dictionary that contains data items and meta information.
    """
    data: list[DataItem]
    metadata: dict[str, Any]


class DataBatch(TypedDict):
    r"""DataBatch is a batch of data items created by a dataloader.
    """
    videos: Optional[torch.Tensor]  # videos representation
    audios: Optional[torch.Tensor]  # audios representation
    images: Optional[torch.Tensor]  # images representation
    input_ids: Optional[torch.Tensor]  # text token ids
    attention_mask: Optional[torch.Tensor]  # attention mask
    image_starts: Optional[torch.Tensor]  # image start token
    image_ends: Optional[torch.Tensor]  # image end token
    audio_starts: Optional[torch.Tensor]  # audio start token
    audio_ends: Optional[torch.Tensor]  # audio end token
    video_starts: Optional[torch.Tensor]  # video start token
    video_ends: Optional[torch.Tensor]  # video end token
    labels: Optional[torch.Tensor]  # labels


class TaskContext(TypedDict):
    r"""TaskContext is a dictionary that contains all the information for a task.
    """
    config_path: Optional[str]
    config: Optional[OmniConfig]
    dataloader: Optional[torch.utils.data.DataLoader]
    tokenizer: Optional[Any]
    model: Optional[Any]
    logger: Optional[Any]
    trainer: Optional[Any]
    current_model_input: Optional[DataItem]
    current_model_output: Optional[Any]


class ModelInput(TypedDict):
    r"""ModelInput is a dictionary that contains all the information for a model input.
    We use it to construct LEGO style models.
    """
    pass


class ModelOutput(TypedDict):
    r"""ModelOutput is a dictionary that contains all the information for a model output.
    We use it to construct LEGO style models.
    """
    pass
