from __future__ import annotations

"""Compatibility shim for MetaUI evaluation CLI.

The canonical CLI implementation now lives in `aeiva.command.aeiva_metaui_eval`.
This module re-exports symbols to keep existing imports stable.
"""

from aeiva.command import aeiva_metaui_eval as _impl


# Preserve legacy import path while ensuring monkeypatches affect the
# canonical implementation module.
if __name__ == "__main__":
    _impl.run()
else:
    import sys

    sys.modules[__name__] = _impl
