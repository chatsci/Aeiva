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

    # setup current input dataitem
    ctx["instruction"] = "Is the woman already in the room?"
    ctx["input"] = ""  # input can be empty 
    ctx["output"] = ""  # in running mode, output is always empty.
    ctx["image_path"] = ""  # None or image name
    ctx["video_path"] = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/videos/7UPGT.mp4"
    ctx["audio_path"] = ""

    # setup runner
    runner = Runner()
    op1 = runner.add_operator('load_config', load_config)
    op2 = runner.add_operator('load_model', load_model)
    op3 = runner.add_operator('setup_data_processor', setup_data_processor)
    op4 = runner.add_operator('process_dataitem', process_dataitem)
    op5 = runner.add_operator('infer', infer)
    runner.stack_operators([op1, op2, op3, op4, op5])

    # run
    runner(ctx)
    print("generated_texts: ", ctx["generated_texts"])