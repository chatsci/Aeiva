
# Command

This module contains CLI entrypoints for AEIVA channels and services.

## Entrypoints

- `aeiva-gateway`: unified multi-channel gateway (recommended)
- `aeiva-chat-terminal`: terminal interaction mode
- `aeiva-chat-realtime`: FastRTC text/audio realtime mode
- `aeiva-chat-gradio`: legacy Gradio chat mode
- `aeiva-chat-slack`: Slack socket mode gateway
- `aeiva-chat-whatsapp`: WhatsApp Cloud API gateway
- `maid-chat`: Unity desktop assistant bridge
- `aeiva-server`: FastAPI text endpoint wrapper

## Shared Lifecycle Utilities

Common command behavior is centralized in `command_utils.py`:

- `setup_command_logger()`: standard logger setup with writable fallback.
- `prepare_runtime_config()`: env var resolution + runtime config normalization + validation.
- `build_runtime()` / `build_runtime_async()`: create Agent or MAS runtime with host router wiring.

## Startup Flow

```text
read config file
  -> prepare_runtime_config()
  -> build_runtime()
  -> start gateway/server loop
  -> graceful stop
```
