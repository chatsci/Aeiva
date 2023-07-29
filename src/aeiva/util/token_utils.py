
import os
from transformers import AutoTokenizer
from aeiva.common.constants import DEFAULT_PAD_TOKEN


def pad_or_truncate_tokens(tokens, max_length, pad_token_id):
    """ This function aims to pad or truncate tokens to max_length.

    Args:
        tokens (list): the list of tokens.
        max_length (int): the max length of tokens.
        pad_token_id (int): the id of pad token.

    Returns:
        tokens (list): the list of tokens after padding or truncating.
    """
    if len(tokens) > max_length:
        tokens = tokens[:max_length]
    elif len(tokens) < max_length:
        tokens = tokens + [pad_token_id] * (max_length - len(tokens))
    return tokens


def get_tokenizer(tokenizer_name_or_path, tokenizer_cls=None, add_special_tokens=False, special_tokens_dict=None):
    # prepare llama tokenizer
    # NOTE: The authors of macaw used https://huggingface.co/decapoda-research/llama-7b-hf. However, this version tokenizer has
    # some bugs (see: https://github.com/huggingface/transformers/issues/22222).
    # So we use the tokenizer from https://huggingface.co/yahma/llama-7b-hf.
    # Also, in many llama tokenizer versions, their bos, eos id seems to be 0, making models hard to learn 
    # when to stop. Therefore, it is more recommended to use 'yahma/llama-7b-hf' or 'yahma/llama-13b-hf'.
    # Credit to Yu Song for the bug of LLaMA tokenizer.
    if os.path.isdir(tokenizer_name_or_path) and tokenizer_cls is not None:
        return tokenizer_cls.from_pretrained(tokenizer_name_or_path)

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name_or_path)  #!!!
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({'pad_token': DEFAULT_PAD_TOKEN})  #!!! NOTE: currently, the pad_token_id is 32000. It is not the same with the macaw implementation. I don't know why.
    tokenizer.padding_side = "right"
    if add_special_tokens:
        tokenizer.add_special_tokens(special_tokens_dict)
    # tokenizer.save_pretrained('./llama_tokenizer')  #!!!!!! change the dir to a constant
    return tokenizer


def load_tokenizer(cls, tokenizer_dir):
    return cls.from_pretrained(tokenizer_dir)
