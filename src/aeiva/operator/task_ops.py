import pytorch_lightning as pl
from pytorch_lightning.loggers import WandbLogger

from aeiva.config import OmniConfig
from aeiva.common.types import TaskContext
from aeiva.common.decorators import OPERATORS, import_submodules


import_submodules('aeiva.operator.custom_ops')


def setup_logger(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]

    # setup the WandbLogger
    if config.use_wandb:
        logger = WandbLogger(project=config.wandb_project, log_model=True)
        print("setup wandb logger done")
    # elif config.use_tensorboard:
    #     logger = pl.loggers.TensorBoardLogger(config.log_dir)
    #     print("setup tensorboard logger done")
    else:
        logger = None
    
    ctx.update({"logger": logger})
    return ctx


def load_config(ctx: TaskContext) -> TaskContext:
    config_path = ctx["config_path"]

    OmniConfig.create_omni_config()
    config = OmniConfig.from_json_or_yaml(config_path)
    parser = config.get_argparse_parser()
    args = parser.parse_args()
    config.update_from_args(args)

    ctx.update({"config": config})
    return ctx


def prepare_resource(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    resource_ready = ctx["resource_ready"]
    if resource_ready:
        return ctx
    
    model_specific_resource_preparer = OPERATORS['resource_preparer'].get(config.model_name)
    if not model_specific_resource_preparer:
        raise ValueError(f"No resource_preparer function registered for model {config.model_name}")
    ctx = model_specific_resource_preparer(ctx)
    return ctx


def load_model(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_loader = OPERATORS['model_loader'].get(config.model_name)
    if not model_specific_loader:
        raise ValueError(f"No model loader function registered for model {config.model_name}")
    ctx = model_specific_loader(ctx)
    return ctx


def init_model(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_initializer = OPERATORS['model_initializer'].get(config.model_name)
    if not model_specific_initializer:
        raise ValueError(f"No model initializer function registered for model {config.model_name}")
    ctx = model_specific_initializer(ctx)
    return ctx


def setup_data_loader(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_data_loader = OPERATORS['data_loader'].get(config.model_name)
    if not model_specific_data_loader:
        raise ValueError(f"No dataloader function registered for model {config.model_name}")
    ctx = model_specific_data_loader(ctx)
    return ctx


def setup_data_processor(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_data_processor = OPERATORS['data_processor'].get(config.model_name)
    if not model_specific_data_processor:
        raise ValueError(f"No data_processor function registered for model {config.model_name}")
    ctx = model_specific_data_processor(ctx)
    return ctx


def process_dataitem(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_dataitem_processor = OPERATORS['dataitem_processor'].get(config.model_name)
    if not model_specific_dataitem_processor:
        raise ValueError(f"No data_item_processor function registered for model {config.model_name}")
    ctx = model_specific_dataitem_processor(ctx)
    return ctx


def setup_trainer(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_trainer = OPERATORS['trainer'].get(config.model_name)
    if not model_specific_trainer:
        raise ValueError(f"No trainer function registered for model {config.model_name}")
    ctx = model_specific_trainer(ctx)
    return ctx


def train(ctx: TaskContext) -> TaskContext:
    trainer = ctx["trainer"]
    trainer.fit(ctx["model"], ctx["train_loader"], ctx["val_loader"])
    return ctx


def eval(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_evaluator = OPERATORS['evaluator'].get(config.model_name)
    if not model_specific_evaluator:
        raise ValueError(f"No evaluator function registered for model {config.model_name}")
    ctx = model_specific_evaluator(ctx)
    return ctx


def infer(ctx: TaskContext) -> TaskContext:
    config = ctx["config"]
    model_specific_inferer = OPERATORS['inferer'].get(config.model_name)
    if not model_specific_inferer:
        raise ValueError(f"No model inferer function registered for model {config.model_name}")
    ctx = model_specific_inferer(ctx)
    return ctx
