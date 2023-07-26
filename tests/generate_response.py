import os

os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"  # NOTE: This is just a workarouond. Ensure a single OpenMP runtime is linked is the best solution.

from aeiva.runner.runner import Runner
from task_operators import *


if __name__ == "__main__":
    # load config
    ctx = {}
    ctx["config_path"] = "/Users/bangliu/Desktop/ChatSCI/Aeiva/configs/train_macaw.yaml"

    ctx["instruction"] = "Is the woman already in the room?"
    ctx["input"] = ""  # input can be empty 
    ctx["output"] = ""  # in running mode, output is always empty.
    ctx["image_path"] = ""  # None or image name
    ctx["video_path"] = "/Users/bangliu/Desktop/ChatSCI/Aeiva/datasets/avsd/videos/7UPGT.mp4"
    ctx["audio_path"] = ""

    runner = Runner()
    node1 = runner.add_operator('load_config', load_config)
    node2 = runner.add_operator('setup_model', setup_model)
    node3 = runner.add_operator('setup_pipeline', setup_pipeline)
    node4 = runner.add_operator('prepare_model_input', prepare_model_input)
    node5 = runner.add_operator('generate', generate)
    runner.stack_operators([node1, node2, node3, node4, node5])
    runner(ctx)
    print("generated_texts: ", ctx["generated_texts"])