# toolkit/git_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class GitToolkit(Toolkit):
    """
    A toolkit for interacting with Git repositories.
    """

    def __init__(self, config=None):
        super().__init__(
            name="GitToolkit",
            tool_names=[
                "git_apply_patch",
                "git_clone",
                "git_custom",
                "git_patch",
                "git_repo_tree"
            ],
            config=config
        )