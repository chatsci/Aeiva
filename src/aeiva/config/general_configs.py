#!/usr/bin/env python
# coding=utf-8
"""
This module contains some general config classes that can be used in deep learning projects.

E.g., data config, model config, trainer config, etc.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

from transformers.utils.versions import require_version
from transformers import MODEL_FOR_CAUSAL_LM_MAPPING

from aeiva.config.base_config import BaseConfig


MODEL_CONFIG_CLASSES = list(MODEL_FOR_CAUSAL_LM_MAPPING.keys())
MODEL_TYPES = tuple(conf.model_type for conf in MODEL_CONFIG_CLASSES)


class ExplicitEnum(str, Enum):
    """
    Enum with more explicit error message for missing values.
    """
    @classmethod
    def _missing_(cls, value):
        raise ValueError(
            f"{value} is not a valid {cls.__name__}, please select one of {list(cls._value2member_map_.keys())}"
        )


class IntervalStrategy(ExplicitEnum):
    NO = "no"
    STEPS = "steps"
    EPOCH = "epoch"


class EvaluationStrategy(ExplicitEnum):
    NO = "no"
    STEPS = "steps"
    EPOCH = "epoch"


class SchedulerType(ExplicitEnum):
    LINEAR = "linear"
    COSINE = "cosine"
    COSINE_WITH_RESTARTS = "cosine_with_restarts"
    POLYNOMIAL = "polynomial"
    CONSTANT = "constant"
    CONSTANT_WITH_WARMUP = "constant_with_warmup"
    INVERSE_SQRT = "inverse_sqrt"
    REDUCE_ON_PLATEAU = "reduce_lr_on_plateau"


class OptimizerNames(ExplicitEnum):
    """
    Stores the acceptable string identifiers for optimizers.
    """
    ADAMW_HF = "adamw_hf"
    ADAMW_TORCH = "adamw_torch"
    ADAMW_TORCH_FUSED = "adamw_torch_fused"
    ADAMW_TORCH_XLA = "adamw_torch_xla"
    ADAMW_APEX_FUSED = "adamw_apex_fused"
    ADAFACTOR = "adafactor"
    ADAMW_ANYPRECISION = "adamw_anyprecision"
    SGD = "sgd"
    ADAGRAD = "adagrad"
    ADAMW_BNB = "adamw_bnb_8bit"
    ADAMW_8BIT = "adamw_8bit"  # just an alias for adamw_bnb_8bit
    LION_8BIT = "lion_8bit"
    LION = "lion_32bit"
    PAGED_ADAMW = "paged_adamw_32bit"
    PAGED_ADAMW_8BIT = "paged_adamw_8bit"
    PAGED_LION = "paged_lion_32bit"
    PAGED_LION_8BIT = "paged_lion_8bit"


@dataclass
class DataConfig(BaseConfig):
    """This class contains the data configuration."""
    dataset_path: Optional[str] = field(
        default=None, metadata={"help": "The path of the dataset to use."}
    )
    dataset_name: Optional[str] = field(
        default="customized", metadata={"help": "Should be \"customized\""}
    )
    is_custom_dataset: Optional[bool] = field(
        default=False, metadata={"help": "whether to use custom data"}
    )
    customized_cache_dir: Optional[str] = field(
        default=".cache/llm-ft/datasets",
        metadata={"help": "Where do you want to store the customized dataset caches"},
    )
    dataset_config_name: Optional[str] = field(
        default=None, metadata={"help": "The configuration name of the dataset to use (via the datasets library)."}
    )
    train_file: Optional[str] = field(default=None, metadata={"help": "The input training data file (a text file)."})
    validation_file: Optional[str] = field(
        default=None,
        metadata={"help": "An optional input evaluation data file to evaluate the perplexity on (a text file)."},
    )
    max_train_samples: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "For debugging purposes or quicker training, truncate the number of training examples to this "
                "value if set."
            )
        },
    )
    max_eval_samples: Optional[int] = field(
        default=1e10,
        metadata={
            "help": (
                "For debugging purposes or quicker training, truncate the number of evaluation examples to this "
                "value if set."
            )
        },
    )
    streaming: Optional[bool] = field(default=False, metadata={"help": "Enable streaming mode"})
    block_size: Optional[int] = field(
        default=512,
        metadata={
            "help": (
                "Optional input sequence length after tokenization. "
                "The training dataset will be truncated in block of this size for training. "
                "Default to the model max input length for single sentence inputs (take into account special tokens)."
            )
        },
    )
    overwrite_cache: Optional[bool] = field(
        default=False,
        metadata={"help": "Overwrite the cached training and evaluation sets"}
    )
    validation_split_percentage: Optional[int] = field(
        default=5,
        metadata={
            "help": "The percentage of the train set used as validation set in case there's no validation split"
        },
    )
    preprocessing_num_workers: Optional[int] = field(
        default=None,
        metadata={"help": "The number of processes to use for the preprocessing."},
    )
    group_texts_batch_size: Optional[int] = field(
        default=1000,
        metadata={
            "help": (
                "Number of samples that will be grouped together to go though"
                " `group_texts` operation. See `--disable_group_texts` for"
                " detailed explanation of this operation."
            )
        }
    )
    disable_group_texts: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether we group original samples together to generate sample"
                " sequences of length `block_size`. By default, we group every"
                " 1000 tokenized sequences together, divide them into "
                " [{total_num_tokens} / {block_size}] sequences, each with"
                " `block_size` tokens (the remaining tokens are ommited."
                " If this flag is set to True, we only group 1 tokenized"
                " sequence, i.e. cutting long sequence into chunks."
            )
        },
    )
    keep_linebreaks: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether to keep line breaks when using TXT files or not."}
    )
    test_file: Optional[str] = field(
        default=None,
        metadata={"help": "Evaluation File Path"},
    )

    def __post_init__(self):
        if self.streaming:
            require_version("datasets>=2.0.0", "The streaming feature requires `datasets>=2.0.0`")

        if self.dataset_name is None and self.train_file is None and self.validation_file is None:
            raise ValueError("Need either a dataset name or a training/validation file.")
        else:
            if self.train_file is not None:
                extension = self.train_file.split(".")[-1]
                assert extension in ["csv", "json", "txt"], "`train_file` should be a csv, a json or a txt file."
            if self.validation_file is not None:
                extension = self.validation_file.split(".")[-1]
                assert extension in ["csv", "json", "txt"], "`validation_file` should be a csv, a json or a txt file."


@dataclass
class ModelConfig(BaseConfig):
    """Model configuration class."""
    model_name_or_path: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "The model checkpoint for weights initialization. Don't set if you want to train a model from scratch."
            )
        },
    )
    lora_model_path: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "The incremental model diff introduced by LoRA finetuning."
                " Along with the original non-finetuned model forms the whole"
                " finetuned model."
            )
        }
    )
    model_type: Optional[str] = field(
        default=None,
        metadata={"help": "If training from scratch, pass a model type from the list: " + ", ".join(MODEL_TYPES)},
    )
    arch_type: Optional[str] = field(
        default="decoder_only",
        metadata={"help": "The architecture type of the model. Currently supported decoder_only or encoder_decoder"}
    )
    config_overrides: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "Override some existing default config settings when a model is trained from scratch. Example: "
                "n_embd=10,resid_pdrop=0.2,scale_attn_weights=false,summary_type=cls_index"
            )
        },
    )
    arch_type: Optional[str] = field(
        default="decoder_only",
        metadata={
            "help": (
                "Model architecture type, e.g. \"decoder_only\","
                " \"encoder_decoder\""
            ),
            "choices": ["decoder_only", "encoder_decoder", "text_regression", "vision_encoder_decoder"],
        },
    )
    config_name: Optional[str] = field(
        default=None,
        metadata={"help": "Pretrained config name or path if not the same as model_name"}
    )
    tokenizer_name: Optional[str] = field(
        default=None,
        metadata={"help": "Pretrained tokenizer name or path if not the same as model_name"}
    )
    cache_dir: Optional[str] = field(
        default=None,
        metadata={"help": "Where do you want to store the pretrained models downloaded from huggingface.co"},
    )
    use_fast_tokenizer: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether to use one of the fast tokenizer (backed by the tokenizers library) or not."},
    )
    model_revision: Optional[str] = field(
        default="main",
        metadata={"help": "The specific model version to use (can be a branch name, tag name or commit id)."},
    )
    use_auth_token: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Will use the token generated when running `huggingface-cli login` (necessary to use this script "
                "with private models)."
            )
        },
    )
    torch_dtype: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "Override the default `torch.dtype` and load the model under this dtype. If `auto` is passed, the "
                "dtype will be automatically derived from the model's weights."
            ),
            "choices": ["auto", "bfloat16", "float16", "float32"],
        },
    )
    use_lora: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to lora."},
    )
    lora_r: Optional[int] = field(
        default=8,
        metadata={"help": "the rank of the lora parameters. The smaller lora_r is , the fewer parameters lora has."},
    )
    lora_alpha: Optional[int] = field(
        default=32,
        metadata={"help": "Merging ratio between the fine-tuned model and the original. This is controlled by a parameter called alpha in the paper."},
    )
    lora_target_modules: Optional[list[str]] = field(
        default=None,
        metadata={"help": "Pretrained config name or path if not the same as model_name",
                              }
    )
    lora_dropout: Optional[float] = field(
        default=0.1,
        metadata={"help": "The dropout rate in lora.linear."},
    )
    save_aggregated_lora: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to save aggregated lora."},
        )
    use_ram_optimized_load: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether use disk mapping when memory is not enough."}
    )
    use_flash_attention: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "whether use flash attention layer to reduce GPU memory with"
                " higher time cost."
            )
        }
    )
    use_int8: Optional[bool] = field(
        default=False,
        metadata={"help": "whether to load int8 quantization for inference"}
    )
    custom_model: Optional[bool] = field(
        default=False,
        metadata={"help": "flag for the model from huggingface or not"}
    )
    # below is added for macaw model
    n_frames: Optional[int] = field(
        default=6,
        metadata={
            "help": "The number of frames for encoding a video."
        },
    )
    attention_heads: Optional[int] = field(
        default=220,
        metadata={
            "help": "The number of attention heads used in multi-head-attention."
        },
    )
    image_conv_kernel: Optional[int] = field(
        default=48,
        metadata={
            "help": "The size of the convolutional kernel for the image stream."
        },
    )
    image_conv_stride: Optional[int] = field(
        default=36,
        metadata={
            "help": "The stride of the convolutional kernel for the image stream."
        },
    )
    video_conv_kernel: Optional[int] = field(
        default=36,
        metadata={
            "help": "The size of the convolutional kernel for the video stream."
        },
    )
    video_conv_stride: Optional[int] = field(
        default=30,
        metadata={
            "help": "The stride of the convolutional kernel for the video stream."
        },
    )
    audio_conv_kernel: Optional[int] = field(
        default=240,
        metadata={
            "help": "The size of the convolutional kernel for the audio stream."
        },
    )
    audio_conv_stride: Optional[int] = field(
        default=220,
        metadata={
            "help": "The stride of the convolutional kernel for the audio stream."
        },
    )
    freeze_multi_modal_encoder: bool = field(
        default=False,
        metadata={
            "help": (
                "Whether to freeze the parameters of multi-modal encoders during training.)."
            )
        },
    )

    def __post_init__(self):
        if self.config_overrides is not None and (self.config_name is not None or self.model_name_or_path is not None):
            raise ValueError(
                "--config_overrides can't be used in combination with --config_name or --model_name_or_path"
            )


@dataclass
class TrainerConfig(BaseConfig):
    framework: Optional[str] = field(
        default="pt",
        metadata={"help": "The framework to use."}
    )
    output_dir: Optional[str] = field(
        default=".",
        metadata={"help": "The output directory where the model predictions and checkpoints will be written."},
    )
    overwrite_output_dir: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Overwrite the content of the output directory. "
                "Use this to continue training if output_dir points to a checkpoint directory."
            )
        },
    )
    do_train: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to run training."}
    )
    do_eval: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to run eval on the dev set."}
    )
    do_predict: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to run predictions on the test set."}
    )
    evaluation_strategy: Optional[Union[IntervalStrategy, str]] = field(
        default="no",
        metadata={"help": "The evaluation strategy to use."},
    )
    prediction_loss_only: Optional[bool] = field(
        default=False,
        metadata={"help": "When performing evaluation and predictions, only returns the loss."}
    )
    per_device_train_batch_size: Optional[int] = field(
        default=8,
        metadata={"help": "Batch size per GPU/TPU core/CPU for training."}
    )
    per_device_eval_batch_size: Optional[int] = field(
        default=8,
        metadata={"help": "Batch size per GPU/TPU core/CPU for evaluation."}
    )

    per_gpu_train_batch_size: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "Deprecated, the use of `--per_device_train_batch_size` is preferred. "
                "Batch size per GPU/TPU core/CPU for training."
            )
        },
    )
    per_gpu_eval_batch_size: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "Deprecated, the use of `--per_device_eval_batch_size` is preferred. "
                "Batch size per GPU/TPU core/CPU for evaluation."
            )
        },
    )

    gradient_accumulation_steps: Optional[int] = field(
        default=1,
        metadata={"help": "Number of updates steps to accumulate before performing a backward/update pass."},
    )
    eval_accumulation_steps: Optional[int] = field(
        default=None,
        metadata={"help": "Number of predictions steps to accumulate before moving the tensors to the CPU."},
    )

    eval_delay: Optional[float] = field(
        default=0,
        metadata={
            "help": (
                "Number of epochs or steps to wait for before the first evaluation can be performed, depending on the"
                " evaluation_strategy."
            )
        },
    )

    learning_rate: Optional[float] = field(
        default=5e-5,
        metadata={"help": "The initial learning rate for AdamW."}
    )
    weight_decay: Optional[float] = field(
        default=0.0,
        metadata={"help": "Weight decay for AdamW if we apply some."}
    )
    adam_beta1: Optional[float] = field(
        default=0.9,
        metadata={"help": "Beta1 for AdamW optimizer"}
    )
    adam_beta2: Optional[float] = field(
        default=0.999,
        metadata={"help": "Beta2 for AdamW optimizer"}
    )
    adam_epsilon: Optional[float] = field(
        default=1e-8,
        metadata={"help": "Epsilon for AdamW optimizer."}
    )
    max_grad_norm: Optional[float] = field(
        default=1.0,
        metadata={"help": "Max gradient norm."}
    )
    num_train_epochs: Optional[float] = field(
        default=3.0,
        metadata={"help": "Total number of training epochs to perform."}
    )
    max_steps: Optional[int] = field(
        default=-1,
        metadata={"help": "If > 0: set total number of training steps to perform. Override num_train_epochs."},
    )
    lr_scheduler_type: Optional[Union[SchedulerType, str]] = field(
        default="linear",
        metadata={"help": "The scheduler type to use."},
    )
    warmup_ratio: Optional[float] = field(
        default=0.0,
        metadata={"help": "Linear warmup over warmup_ratio fraction of total steps."}
    )
    warmup_steps: Optional[int] = field(
        default=0,
        metadata={"help": "Linear warmup over warmup_steps."}
    )
    log_on_each_node: Optional[bool] = field(
        default=True,
        metadata={
            "help": (
                "When doing a multinode distributed training, whether to log once per node or just once on the main"
                " node."
            )
        },
    )
    logging_dir: Optional[str] = field(
        default=None,
        metadata={"help": "Tensorboard log dir."}
    )
    logging_strategy: Optional[Union[IntervalStrategy, str]] = field(
        default="steps",
        metadata={"help": "The logging strategy to use."},
    )
    logging_first_step: Optional[bool] = field(
        default=False,
        metadata={"help": "Log the first global_step"}
    )
    logging_steps: Optional[float] = field(
        default=500,
        metadata={
            "help": (
                "Log every X updates steps. Should be an integer or a float in range `[0,1)`."
                "If smaller than 1, will be interpreted as ratio of total training steps."
            )
        },
    )
    logging_nan_inf_filter: Optional[bool] = field(
        default=True,
        metadata={"help": "Filter nan and inf losses for logging."}
    )
    save_strategy: Optional[Union[IntervalStrategy, str]] = field(
        default="steps",
        metadata={"help": "The checkpoint save strategy to use."},
    )
    save_steps: Optional[float] = field(
        default=500,
        metadata={
            "help": (
                "Save checkpoint every X updates steps. Should be an integer or a float in range `[0,1)`."
                "If smaller than 1, will be interpreted as ratio of total training steps."
            )
        },
    )
    save_total_limit: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "If a value is passed, will limit the total amount of checkpoints. Deletes the older checkpoints in"
                " `output_dir`. When `load_best_model_at_end` is enabled, the 'best' checkpoint according to"
                " `metric_for_best_model` will always be retained in addition to the most recent ones. For example,"
                " for `save_total_limit=5` and `load_best_model_at_end=True`, the four last checkpoints will always be"
                " retained alongside the best model. When `save_total_limit=1` and `load_best_model_at_end=True`,"
                " it is possible that two checkpoints are saved: the last one and the best one (if they are different)."
                " Default is unlimited checkpoints"
            )
        },
    )
    save_safetensors: Optional[bool] = field(
        default=False,
        metadata={
            "help": "Use safetensors saving and loading for state dicts instead of default torch.load and torch.save."
        },
    )
    save_on_each_node: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "When doing multi-node distributed training, whether to save models and checkpoints on each node, or"
                " only on the main one"
            )
        },
    )
    no_cuda: Optional[bool] = field(
        default=False,
        metadata={"help": "Do not use CUDA even when it is available"}
    )
    seed: Optional[int] = field(
        default=42,
        metadata={"help": "Random seed that will be set at the beginning of training."}
    )
    data_seed: Optional[int] = field(
        default=None,
        metadata={"help": "Random seed to be used with data samplers."}
    )
    jit_mode_eval: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether or not to use PyTorch jit trace for inference"}
    )
    use_ipex: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Use Intel extension for PyTorch when it is available, installation:"
                " 'https://github.com/intel/intel-extension-for-pytorch'"
            )
        },
    )
    bf16: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether to use bf16 (mixed) precision instead of 32-bit. Requires Ampere or higher NVIDIA"
                " architecture or using CPU (no_cuda). This is an experimental API and it may change."
            )
        },
    )
    fp16: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to use fp16 (mixed) precision instead of 32-bit"},
    )
    fp16_opt_level: Optional[str] = field(
        default="O1",
        metadata={
            "help": (
                "For fp16: Apex AMP optimization level selected in ['O0', 'O1', 'O2', and 'O3']. "
                "See details at https://nvidia.github.io/apex/amp.html"
            )
        },
    )
    half_precision_backend: Optional[str] = field(
        default="auto",
        metadata={
            "help": "The backend to be used for half precision.",
            "choices": ["auto", "cuda_amp", "apex", "cpu_amp"],
        },
    )
    bf16_full_eval: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether to use full bfloat16 evaluation instead of 32-bit. This is an experimental API and it may"
                " change."
            )
        },
    )
    fp16_full_eval: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to use full float16 evaluation instead of 32-bit"},
    )
    tf32: Optional[bool] = field(
        default=None,
        metadata={
            "help": (
                "Whether to enable tf32 mode, available in Ampere and newer GPU architectures. This is an experimental"
                " API and it may change."
            )
        },
    )
    local_rank: Optional[int] = field(
        default=-1,
        metadata={"help": "For distributed training: local_rank"}
    )
    ddp_backend: Optional[str] = field(
        default=None,
        metadata={
            "help": "The backend to be used for distributed training",
            "choices": ["nccl", "gloo", "mpi", "ccl"],
        },
    )
    tpu_num_cores: Optional[int] = field(
        default=None,
        metadata={"help": "TPU: Number of TPU cores (automatically passed by launcher script)"}
    )
    tpu_metrics_debug: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Deprecated, the use of `--debug tpu_metrics_debug` is preferred. TPU: Whether to print debug metrics"
            )
        },
    )
    debug: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether or not to enable debug mode. Current options"
            )
        }
    )
    dataloader_drop_last: Optional[bool] = field(
        default=False,
        metadata={"help": "Drop the last incomplete batch if it is not divisible by the batch size."}
    )
    eval_steps: Optional[float] = field(
        default=None,
        metadata={
            "help": (
                "Run an evaluation every X steps. Should be an integer or a float in range `[0,1)`."
                "If smaller than 1, will be interpreted as ratio of total training steps."
            )
        },
    )
    dataloader_num_workers: Optional[int] = field(
        default=0,
        metadata={
            "help": (
                "Number of subprocesses to use for data loading (PyTorch only). 0 means that the data will be loaded"
                " in the main process."
            )
        },
    )
    past_index: Optional[int] = field(
        default=-1,
        metadata={"help": "If >=0, uses the corresponding part of the output as the past state for next step."},
    )
    run_name: Optional[str] = field(
        default=None,
        metadata={"help": "An optional descriptor for the run. Notably used for wandb logging."}
    )
    disable_tqdm: Optional[bool] = field(
        default=None,
        metadata={"help": "Whether or not to disable the tqdm progress bars."}
    )

    remove_unused_columns: Optional[bool] = field(
        default=True,
        metadata={"help": "Remove columns not required by the model when using an nlp.Dataset."}
    )
    label_names: Optional[list[str]] = field(
        default=None,
        metadata={"help": "The list of keys in your dictionary of inputs that correspond to the labels."}
    )
    load_best_model_at_end: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether or not to load the best model found during training at the end of training. When this option"
                " is enabled, the best checkpoint will always be saved. See `save_total_limit` for more."
            )
        },
    )
    metric_for_best_model: Optional[str] = field(
        default=None,
        metadata={"help": "The metric to use to compare two different models."}
    )
    greater_is_better: Optional[bool] = field(
        default=None,
        metadata={"help": "Whether the `metric_for_best_model` should be maximized or not."}
    )
    ignore_data_skip: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "When resuming training, whether or not to skip the first epochs and batches to get to the same"
                " training data."
            )
        },
    )
    sharded_ddp: Optional[str] = field(
        default="",
        metadata={
            "help": (
                "Whether or not to use sharded DDP training (in distributed training only). The base option should be"
                " `simple`, `zero_dp_2` or `zero_dp_3` and you can add CPU-offload to `zero_dp_2` or `zero_dp_3` like"
                " this: zero_dp_2 offload` or `zero_dp_3 offload`. You can add auto-wrap to `zero_dp_2` or `zero_dp_3`"
                " with the same syntax: zero_dp_2 auto_wrap` or `zero_dp_3 auto_wrap`."
            ),
        },
    )
    fsdp: Optional[str] = field(
        default="",
        metadata={
            "help": (
                "Whether or not to use PyTorch Fully Sharded Data Parallel (FSDP) training (in distributed training"
                " only). The base option should be `full_shard`, `shard_grad_op` or `no_shard` and you can add"
                " CPU-offload to `full_shard` or `shard_grad_op` like this: full_shard offload` or `shard_grad_op"
                " offload`. You can add auto-wrap to `full_shard` or `shard_grad_op` with the same syntax: full_shard"
                " auto_wrap` or `shard_grad_op auto_wrap`."
            ),
        },
    )
    fsdp_min_num_params: Optional[int] = field(
        default=0,
        metadata={
            "help": (
                "This parameter is deprecated. FSDP's minimum number of parameters for Default Auto Wrapping. (useful"
                " only when `fsdp` field is passed)."
            )
        },
    )
    fsdp_config: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "Config to be used with FSDP (Pytorch Fully Sharded  Data Parallel). The  value is either a"
                "fsdp json config file (e.g., `fsdp_config.json`) or an already loaded  json file as `dict`."
            )
        },
    )
    fsdp_transformer_layer_cls_to_wrap: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "This parameter is deprecated. Transformer layer class name (case-sensitive) to wrap, e.g,"
                " `BertLayer`, `GPTJBlock`, `T5Block` .... (useful only when `fsdp` flag is passed)."
            )
        },
    )
    deepspeed: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "Enable deepspeed and pass the path to deepspeed json config file (e.g. ds_config.json) or an already"
                " loaded json file as a dict"
            )
        },
    )
    label_smoothing_factor: Optional[float] = field(
        default=0.0,
        metadata={"help": "The label smoothing epsilon to apply (zero means no label smoothing)."}
    )

    default_optim = "adamw_hf"
    optim: Optional[Union[OptimizerNames, str]] = field(
        default=default_optim,
        metadata={"help": "The optimizer to use."},
    )
    optim_args: Optional[str] = field(
        default=None,
        metadata={"help": "Optional arguments to supply to optimizer."}
    )
    adafactor: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether or not to replace AdamW by Adafactor."}
    )
    group_by_length: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether or not to group samples of roughly the same length together when batching."},
    )
    length_column_name: Optional[str] = field(
        default="length",
        metadata={"help": "Column name with precomputed lengths to use when grouping by length."},
    )
    report_to: Optional[list[str]] = field(
        default=None,
        metadata={"help": "The list of integrations to report the results and logs to."}
    )
    ddp_find_unused_parameters: Optional[bool] = field(
        default=None,
        metadata={
            "help": (
                "When using distributed training, the value of the flag `find_unused_parameters` passed to "
                "`DistributedDataParallel`."
            )
        },
    )
    ddp_bucket_cap_mb: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "When using distributed training, the value of the flag `bucket_cap_mb` passed to "
                "`DistributedDataParallel`."
            )
        },
    )
    ddp_broadcast_buffers: Optional[bool] = field(
        default=None,
        metadata={
            "help": (
                "When using distributed training, the value of the flag `broadcast_buffers` passed to "
                "`DistributedDataParallel`."
            )
        },
    )
    dataloader_pin_memory: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether or not to pin memory for DataLoader."}
    )
    skip_memory_metrics: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether or not to skip adding of memory profiler reports to metrics."}
    )
    use_legacy_prediction_loop: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether or not to use the legacy prediction_loop in the Trainer."}
    )
    push_to_hub: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether or not to upload the trained model to the model hub after training."}
    )
    resume_from_checkpoint: Optional[str] = field(
        default=None,
        metadata={"help": "The path to a folder with a valid checkpoint for your model."},
    )
    gradient_checkpointing: Optional[bool] = field(
        default=False,
        metadata={
            "help": "If True, use gradient checkpointing to save memory at the expense of slower backward pass."
        },
    )
    include_inputs_for_metrics: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether or not the inputs will be passed to the `compute_metrics` function."}
    )
    auto_find_batch_size: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether to automatically decrease the batch size in half and rerun the training loop again each time"
                " a CUDA Out-of-Memory was reached"
            )
        },
    )
    full_determinism: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether to call enable_full_determinism instead of set_seed for reproducibility in distributed"
                " training. Important: this will negatively impact the performance, so only use it for debugging."
            )
        },
    )
    torchdynamo: Optional[str] = field(
        default=None,
        metadata={
            "help": "This argument is deprecated, use `--torch_compile_backend` instead.",
        },
    )
    ray_scope: Optional[str] = field(
        default="last",
        metadata={
            "help": (
                'The scope to use when doing hyperparameter search with Ray. By default, `"last"` will be used. Ray'
                " will then use the last checkpoint of all trials, compare those, and select the best one. However,"
                " other options are also available. See the Ray documentation"
                " (https://docs.ray.io/en/latest/tune/api_docs/analysis.html"
                "#ray.tune.ExperimentAnalysis.get_best_trial)"
                " for more options."
            )
        },
    )
    ddp_timeout: Optional[int] = field(
        default=1800,
        metadata={
            "help": "Overrides the default timeout for distributed training (value should be given in seconds)."
        },
    )
    torch_compile: Optional[bool] = field(
        default=False,
        metadata={"help": "If set to `True`, the model will be wrapped in `torch.compile`."}
    )
    torch_compile_backend: Optional[str] = field(
        default=None,
        metadata={
            "help": "Which backend to use with `torch.compile`, passing one will trigger a model compilation.",
        },
    )
    torch_compile_mode: Optional[str] = field(
        default=None,
        metadata={
            "help": "Which mode to use with `torch.compile`, passing one will trigger a model compilation.",
        },
    )
    xpu_backend: Optional[str] = field(
        default=None,
        metadata={
            "help": "The backend to be used for distributed training on Intel XPU.",
            "choices": ["mpi", "ccl", "gloo"],
        },
    )

    # below added by Bang
    log_every_n_steps: Optional[int] = field(
        default=100,
        metadata={"help": "Log every n steps"}
    )
    use_wandb: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "When this flag is True, wandb will be enabled"
            )
        },
    )
    wandb_project: Optional[str] = field(
        default="",
        metadata={
            "help": (
                "The name of the wandb project"
            )
        },
    )
    wandb_run_name: Optional[str] = field(
        default="",
        metadata={
            "help": (
                "The name of the wandb run"
            )
        },
    )
    init_from: Optional[str] = field(
        default="scratch",
        metadata={
            "help": (
                "The path of the model to be loaded"
            )
        },
    )
    always_save_checkpoint: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether to always save checkpoint after each eval"
            )
        },
    )
    min_lr: Optional[float] = field(
        default=1e-6,
        metadata={
            "help": (
                "The minimum learning rate"
            )
        },
    )
    lr_decay_steps: Optional[int] = field(
        default=10000,
        metadata={
            "help": (
                "The number of steps to decay learning rate"
            )
        },
    )
    lr_decay: Optional[bool] = field(
        default=False,
        metadata={
            "help": (
                "Whether to decay learning rate"
            )
        },
    )
    accumulate_grad_batches: Optional[int] = field(
        default=1,
        metadata={
            "help": (
                "The number of gradient accumulation steps used to simulate larger batch sizes"
            )
        },
    )
    limit_val_batches: Optional[int] = field(
        default=1,
        metadata={
            "help": (
                "How much of validation dataset to fast estimate val loss during training"
            )
        },
    )
    val_check_interval: Optional[int] = field(
        default=2000,
        metadata={
            "help": (
                "Evaluate the loss on train/validation set for every val_check_interval train steps"
            )
        },
    )
    save_checkpoint_every_n_train_steps: Optional[int] = field(
        default=10000,
        metadata={
            "help": (
                "Save checkpoint every n train steps"
            )
        },
    )
    use_return_dict: Optional[bool] = field(
        default=True,
        metadata={
            "help": (
                "Whether to use return dict"
            )
        },
    )

    def __post_init__(self):
        pass


@dataclass
class FinetunerConfig(BaseConfig):
    eval_dataset_path: Optional[str] = field(
        default=None,
        metadata={"help": "The path of the eval dataset to use."}
    )


@dataclass
class EvaluatorConfig(BaseConfig):

    random_shuffle: Optional[bool] = field(
        default=False, 
        metadata={
            "help": ""
        }
    )
    random_seed: Optional[int] = field(
        default=1,
        metadata={
            "help": (
                "used to set random seed"
            )
        },
    )
    evaluator_output_dir: Optional[str] = field(
        default="./output_dir",
        metadata={"help": "Output path for the inferenced results"},
    )
    mixed_precision: Optional[str] = field(
        default="bf16",
        metadata={
            "help": (
                "mixed precision mode, whether to use bf16 or fp16"
            ),
            "choices": ["bf16","fp16"],
        },
    )
    answer_type: Optional[str] = field(
        default="text",
        metadata={
            "help": (
                'Question type for answer extraction from the decoder output.'
                ' Supported types: \n'
                '   1) "multiple_choice", e.g. A, B, C, D, ...\n'
                '   2) "binary_choice", e.g. yes, no, maybe\n'
                '   3) "math", e.g. 1.0, -3.52\n'
                '   4) "text", e.g. "I think that it is okay"\n'
                '   5) Special treatment for several datasets\n'
                '     - "gsm8k"\n'
                '     - "svamp"\n'
                '     - "asdiv"\n'
                '     - "addsub"\n'
                '     - "singleeq"\n'
                '     - "multiarith"\n'
                '     - "aqua"\n'
                '     - "csqa"\n'
                '     - "strategyqa"\n'
                '     - "pubmedqa"\n'
                '     - "medmcqa"\n'
                '     - "usmle"\n'
            )
        },
    )
    prompt_structure: Optional[str] = field(
        default="{input}",
        metadata={
            "help": (
                'Prompt structure to facilitate prompt engineering during'
                ' inference. The model will receive'
                ' `prompt_structure.format(input=input)` as its input.'
            )
        },
    )
    evaluate_block_size: Optional[int] = field(
        default=512,
        metadata={
            "help": (
                "the model will have at least block_size tokens for context when calculating the conditional likelihood of any one token"
                " (provided there are block_size preceding tokens available to condition on)"
            )
        },
    )
    metric: Optional[str] = field(
        default="accuracy",
        metadata={
            "help": "the metric the model will be evaluated on",
            "choices": ["ppl", "perplexity", "acc", "accuracy", "nll", "neg_log_likelihood"],
        },
    )
    inference_batch_size_per_device: Optional[int] = field(
        default=1,
        metadata={
            "help": (
                "every device will infer {inference_batch_size_per_device}"
                " samples in parallel. The inferred results will be concatenaed"
                " with inputs and attach a reward."
            ),
        },
    )
    use_accelerator_for_evaluator: Optional[bool] = field(
        default=False,
        metadata={"help": "Whether to use Huggingface Accelerator instead of Deepspeed"},
    )  
    temperature: Optional[float] = field(
        default=0,
        metadata={"help": "Temperature during inference."},
    )
    repetition_penalty: Optional[float] = field(
        default=1,
        metadata={"help": "Repetition_penalty during inference."},
    )    
    max_new_tokens: Optional[int] = field(
        default=100,
        metadata={"help": "Maximum length during inference."},
    )
    
@dataclass
class InferencerConfig(BaseConfig):
    device: Optional[str] = field(
        default="gpu",
        metadata={
            "help": "device of chatbot",
            "choices": ["gpu", "cpu"],
        },
    )
    do_sample: Optional[bool] = field(
        default=False,
        metadata={
            "help": "whether turn on true random sampling during inference."
        },
    )


@dataclass
class BenchmarkingConfig(BaseConfig):
    lm_evaluation_metric: Optional[str] = field(
        default="accuracy",
        metadata={
            "help": "the metric the model will be evaluated on",
            "choices": ["acc", "acc_norm", "bleu", "chrf", "em", "f1", "ppl", \
                "ter", "r@1", "r@2", "mrr", "mc1", "mc2", "word_perplexity", \
                    "byte_perplexity", "bits_per_byte"],
        },
    )
