import torch
from functools import partial

from torch.utils.data import Dataset, DataLoader

from aeiva.util.json_utils import load_json
from aeiva.common.pipeline import Pipeline


class MultiModalDataset(Dataset):
    def __init__(self, config, tokenizer, pipeline: list[callable]):
        self.config = config
        self.tokenizer = tokenizer
        self.processed_dataset = load_json(config.dataset_path)
        if isinstance(pipeline, list):
            self.pipeline = Pipeline(pipeline)  #!!!! revise later.
        else:
            self.pipeline = pipeline

    def __len__(self):
        return len(self.processed_dataset["data"])

    def __getitem__(self, idx):
        print("idx: ", idx)
        data_item = self.processed_dataset["data"][idx]
        data_item = self.pipeline(data_item.copy())  #!!! Do I need copy?
        return data_item


def collate_multimodal_batches(batch, tokenizer):
    fields = ['video_frames', 'audio_mels', 'transformed_image']
    token_fields = ['text_token_ids', 'attention_mask']
    tags = ['<image>', '</image>', '<audio>', '</audio>', '<video>', '</video>']
    field_map = {
        'video_frames': 'videos',
        'audio_mels': 'audios',
        'transformed_image': 'images',
        'text_token_ids': 'input_ids',
        'attention_mask': 'attention_mask',
        '<image>': 'image_starts',
        '</image>': 'image_ends',
        '<audio>': 'audio_starts',
        '</audio>': 'audio_ends',
        '<video>': 'video_starts',
        '</video>': 'video_ends'
    }
    
    batch_data = {}
    for field in fields:
        batch_data[field_map[field]] = torch.cat([item[field] for item in batch], dim=0).float() #!!! use half() when using GPU.
    

    for field in token_fields:
        batch_data[field_map[field]] = torch.tensor([item[field] for item in batch], dtype=torch.int)
        
    for tag in tags:
        batch_data[field_map[tag]] = torch.tensor([tokenizer.convert_tokens_to_ids(tag)] * len(batch), dtype=torch.int)

    # Add labels if they exist
    if 'labels' in batch[0]:
        batch_data['labels'] = torch.tensor([item['labels'] for item in batch], dtype=torch.int)
    else:
        batch_data['labels'] = None

    return batch_data


def multimodal_loader(config, tokenizer, pipeline: list[callable]):
    dataset = MultiModalDataset(config, tokenizer, pipeline)
    dataloader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True, collate_fn=partial(collate_multimodal_batches, tokenizer=tokenizer))
    return dataloader
