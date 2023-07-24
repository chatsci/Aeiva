import torch
from torch.utils.data import Dataset, DataLoader
from aeiva.util.json_utils import load_json
from aeiva.util.pipeline import Pipeline


class MultiModalDataset(Dataset):
    def __init__(self, config, tokenizer, pipeline: list[callable]):
        self.config = config
        self.tokenizer = tokenizer
        self.processed_dataset = load_json(config.dataset_path)
        self.pipeline = Pipeline(pipeline)

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


# def collate_multimodal_batches(batch, tokenizer):
#     # Separate the tensors in the batch
#     videos = [item['video_frames'] for item in batch]
#     audios = [item['audio_mels'] for item in batch]
#     images = [item['transformed_image'] for item in batch]
#     input_ids = [item['text_token_ids'] for item in batch]
#     input_ids = torch.tensor(input_ids, dtype=torch.int)
#     attention_masks = [item['attention_mask'] for item in batch]
#     attention_masks = torch.tensor(attention_masks, dtype=torch.int)
#     contain_labels = False
#     if 'labels' in batch[0]:
#         contain_labels = True
#     labels = [item['labels'] for item in batch if contain_labels]
#     labels = torch.tensor(labels, dtype=torch.int)

#     # The rest of the batch is created as specified
#     bs = len(batch)  # Batch size
#     # Assuming `tokenizer` is defined in your scope
#     image_starts = torch.tensor([tokenizer.convert_tokens_to_ids('<image>')] * bs, dtype=torch.int)
#     image_ends = torch.tensor([tokenizer.convert_tokens_to_ids('</image>')] * bs, dtype=torch.int)
#     audio_starts = torch.tensor([tokenizer.convert_tokens_to_ids('<audio>')] * bs, dtype=torch.int)
#     audio_ends = torch.tensor([tokenizer.convert_tokens_to_ids('</audio>')] * bs, dtype=torch.int)
#     video_starts = torch.tensor([tokenizer.convert_tokens_to_ids('<video>')] * bs, dtype=torch.int)
#     video_ends = torch.tensor([tokenizer.convert_tokens_to_ids('</video>')] * bs, dtype=torch.int)

#     batch = {
#         'videos': torch.cat(videos, dim=0).float(),  # shape: (batch_size, num_frames, 3, 224, 224) #!!! use half() when using GPU.
#         'audios': torch.cat(audios, dim=0).float(),  # shape: (batch_size, 80, 3000) #!!! use half() when using GPU.
#         'images': torch.cat(images, dim=0).float(),  # shape: (batch_size, 3, 224, 224) #!!! use half() when using GPU.
#         'input_ids': input_ids,                     # list of lists
#         'attention_mask': attention_masks,          # list of lists
#         'labels': labels if contain_labels else None,       # list of lists, shape (batch_size, num_labels)
#         'image_starts': image_starts,               # shape: (batch_size,)
#         'image_ends': image_ends,                   # shape: (batch_size,)
#         'audio_starts': audio_starts,               # shape: (batch_size,)
#         'audio_ends': audio_ends,                   # shape: (batch_size,)
#         'video_starts': video_starts,               # shape: (batch_size,)
#         'video_ends': video_ends                    # shape: (batch_size,)
#     }

#     return batch
