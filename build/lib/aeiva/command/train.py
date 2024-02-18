import os

os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"  # NOTE: This is just a workarouond. Ensure a single OpenMP runtime is linked is the best solution.

from aeiva.runner.runner import Runner
from aeiva.operator.task_ops import *


if __name__ == "__main__":
    # setup config
    ctx = {}
    ctx["config_path"] = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"

    # setup runner
    runner = Runner()
    op1 = runner.add_operator('load_config', load_config)
    op2 = runner.add_operator('init_model', init_model)
    op3 = runner.add_operator('setup_data_processor', setup_data_processor)
    op4 = runner.add_operator('setup_data_loader', setup_data_loader)
    op5 = runner.add_operator('setup_logger', setup_logger)
    op6 = runner.add_operator('setup_trainer', setup_trainer)
    op7 = runner.add_operator('train', train)
    runner.stack_operators([op1, op2, op3, op4, op5, op6, op7])

    # run
    runner(ctx)
 