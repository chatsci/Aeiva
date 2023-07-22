import whisper
import PIL
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize
# from datasets import Dataset
from aeiva.util.json_utils import load_json
from aeiva.util.video_utils import get_frame_indices
from functools import partial

try:
    from torchvision.transforms import InterpolationMode
    BICUBIC = InterpolationMode.BICUBIC
except ImportError:
    BICUBIC = Image.BICUBIC


TOTAL_FRAMES = 120  # The total number of frames in the video file.
NUM_INDICES = 6  # The number of frame indices to generate.


MEANS = (0.48145466, 0.4578275, 0.40821073)  # mean for R, G, B image channels
STDS = (0.26862954, 0.26130258, 0.27577711)  # standard deviations for R, G, B image channels
N_PX = 224  # image width and height

def preprocess_image(image: PIL.Image, n_pixel=N_PX):
    preprocess = Compose([
        Resize(n_pixel, interpolation=BICUBIC),  # Resize the image
        CenterCrop(n_pixel),                     # Crop the center of the image
        lambda img: img.convert("RGB"),          # Convert the image to RGB
        ToTensor(),                              # Convert the image to a PyTorch tensor
        Normalize(MEANS, STDS)                   # Normalize the image
    ])
    processed_image = preprocess(image)
    return processed_image


class MultiModalDataset(Dataset):
    def __init__(self, data_dirs: dict, tokenizer):
        self.processed_dataset = self._load_datasets(data_dirs['data_dir'])
        self.image_dir = data_dirs['image_dir']
        self.audio_dir = data_dirs['audio_dir']
        # self.video_dir = data_dirs['video_dir']
        self.frame_dir = data_dirs['frame_dir']
        self.tokenizer = tokenizer
        self.train_frame_indices = get_frame_indices(TOTAL_FRAMES, NUM_INDICES)

    def _load_datasets(self, data_dir):
        """ Load the dataset for training and evaluation.
        It will be input into the Trainer class of Huggingface. See run_clm_llms.py
        """
        # load formatted dataset (the dataset we get after prepare.py)
        processed_dataset = load_json(data_dir)  #!!!
        return processed_dataset

    def __len__(self):
        return len(self.processed_dataset["data"])
    
    def _get_frame_path(self, frame_dir, video_name, frame_idx):
        return '{}{}.mp4_{}.jpg'.format(frame_dir, video_name, str(frame_idx))
    
    def _get_video_frames(self, frame_dir, video_name, frame_indices):
        all_video_frames = []
        for vfi in frame_indices:
            if video_name == None:
                frame = torch.zeros(1, 3, 224, 224)
            else:
                frame = preprocess_image(
                    Image.open(self._get_frame_path(frame_dir, video_name, vfi))
                )
                frame = frame.unsqueeze(0)
            all_video_frames.append(frame)
        all_video_frames = torch.cat(all_video_frames, dim=0).unsqueeze(0)
        return all_video_frames

    def _get_audio_path(self, audio_dir, audio_name):
        return '{}{}.mp4.wav'.format(audio_dir, audio_name) # audio name is the same as video name

    def _get_audio_mels(self, audio_dir, audio_name):
        all_audio_mels = []
        if audio_name == None:
            mel = torch.zeros(1, 80, 3000)
        else:
            # load audio and pad/trim it to fit 30 seconds
            audio = whisper.load_audio(self._get_audio_path(audio_dir, audio_name))
            audio = whisper.pad_or_trim(audio)
            # make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio)
            mel = mel.unsqueeze(0)
            # audio_features = model.embed_audio(mel.unsqueeze(0)).squeeze()
        return mel

    def _get_image_path(self, image_dir, image_name):
        return '{}{}'.format(image_dir, image_name)
    
    def _get_image_features(self, image_dir, image_name):
        if image_name == None:
            image_features = torch.zeros(1, 3, 224, 224)
        else:
            image_features = preprocess_image(Image.open(self._get_image_path(image_dir, image_name)))
            image_features = image_features.unsqueeze(0)
        return image_features

    def __getitem__(self, idx):
        print("idx: ", idx)
        data_item = self.processed_dataset["data"][idx]
        data_item["video_frames_features"] = self._get_video_frames(self.frame_dir, data_item["video"], self.train_frame_indices)
        data_item["audio_mel_features"] = self._get_audio_mels(self.audio_dir, data_item["audio"])
        data_item["image_features"] = self._get_image_features(self.image_dir, data_item["image"])
        return data_item


def my_collate_fn(batch, tokenizer):
    # Separate the tensors in the batch
    videos = [item['video_frames_features'] for item in batch]
    audios = [item['audio_mel_features'] for item in batch]
    images = [item['image_features'] for item in batch]
    input_ids = [item['text_token_ids'] for item in batch]
    input_ids = torch.tensor(input_ids, dtype=torch.int)
    attention_masks = [item['attention_mask'] for item in batch]
    attention_masks = torch.tensor(attention_masks, dtype=torch.int)
    contain_labels = False
    if 'labels' in batch[0]:
        contain_labels = True
    labels = [item['labels'] for item in batch if contain_labels]
    labels = torch.tensor(labels, dtype=torch.int)

    # The rest of the batch is created as specified
    bs = len(batch)  # Batch size
    # Assuming `tokenizer` is defined in your scope
    image_starts = torch.tensor([tokenizer.convert_tokens_to_ids('<image>')] * bs, dtype=torch.int)
    image_ends = torch.tensor([tokenizer.convert_tokens_to_ids('</image>')] * bs, dtype=torch.int)
    audio_starts = torch.tensor([tokenizer.convert_tokens_to_ids('<audio>')] * bs, dtype=torch.int)
    audio_ends = torch.tensor([tokenizer.convert_tokens_to_ids('</audio>')] * bs, dtype=torch.int)
    video_starts = torch.tensor([tokenizer.convert_tokens_to_ids('<video>')] * bs, dtype=torch.int)
    video_ends = torch.tensor([tokenizer.convert_tokens_to_ids('</video>')] * bs, dtype=torch.int)

    batch = {
        'videos': torch.cat(videos, dim=0).float(),  # shape: (batch_size, num_frames, 3, 224, 224) #!!! use half() when using GPU.
        'audios': torch.cat(audios, dim=0).float(),  # shape: (batch_size, 80, 3000) #!!! use half() when using GPU.
        'images': torch.cat(images, dim=0).float(),  # shape: (batch_size, 3, 224, 224) #!!! use half() when using GPU.
        'input_ids': input_ids,                     # list of lists
        'attention_mask': attention_masks,          # list of lists
        'labels': labels if contain_labels else None,       # list of lists, shape (batch_size, num_labels)
        'image_starts': image_starts,               # shape: (batch_size,)
        'image_ends': image_ends,                   # shape: (batch_size,)
        'audio_starts': audio_starts,               # shape: (batch_size,)
        'audio_ends': audio_ends,                   # shape: (batch_size,)
        'video_starts': video_starts,               # shape: (batch_size,)
        'video_ends': video_ends                    # shape: (batch_size,)
    }

    return batch


if __name__ == '__main__':
    from transformers import LlamaTokenizer
    import aeiva.data.formatter  # For registering data formatters and processors.
    from aeiva.data.base import BaseDataFormatter
    from aeiva.util.token_utils import get_tokenizer
    # load the dataset
    data_dirs = {
        'image_dir': '/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/coco/train2014/',
        'audio_dir': '/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/audios/',
        'frame_dir': '/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/frames/',
        'data_dir': '/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/merge/avsd_alpaca_vqa.json'
    }
    TOKENIZER =  get_tokenizer("/Users/bangliu/Desktop/ChatSCI/Aeiva/pretrained_models/macaw/", tokenizer_cls=LlamaTokenizer)
    dataset = MultiModalDataset(data_dirs, TOKENIZER)
    dataloader = DataLoader(
        dataset,
        batch_size=4,
        collate_fn=partial(my_collate_fn, tokenizer=TOKENIZER),
    )
    data_item = next(iter(dataloader))
    for key, val in data_item.items():
        print(key)
        if type(val) is not list:
            print(val.shape)
    # print(data_item)
