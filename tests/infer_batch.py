import os

os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"  # NOTE: This is just a workarouond. Ensure a single OpenMP runtime is linked is the best solution.

from aeiva.runner.runner import Runner
from task_operators import *


if __name__ == "__main__":
    ctx = {}
    ctx["config_path"] = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"

    runner = Runner()
    node1 = runner.add_operator('load_config', load_config)
    node2 = runner.add_operator('setup_model', setup_model)
    node3 = runner.add_operator('setup_pipeline', setup_pipeline)
    node4 = runner.add_operator('get_dataloader', get_dataloader)
    node5 = runner.add_operator('inference', inference)
    runner.stack_operators([node1, node2, node3, node4, node5])
    runner(ctx)
    # >>> python infer_batch.py --batch_size 1 (or --mode "inference")