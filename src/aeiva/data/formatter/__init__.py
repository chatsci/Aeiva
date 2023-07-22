import os

from .alpaca import AlpacaDataFormatter
from .avsd import AvsdDataFormatter
from .macaw import MacawCocoDataFormatter, MacawAvsdDataFormatter
from .vqa import VqaDataFormatter


os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"  # NOTE: This is just a workarouond. Ensure a single OpenMP runtime is linked is the best solution.
