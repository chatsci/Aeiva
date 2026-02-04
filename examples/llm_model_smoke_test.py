import asyncio
import time
import yaml

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.action.action_envelope import parse_action_envelope
from aeiva.cognition.brain.llm_brain import LLMBrain

CONFIG_PATH = "configs/agent_config.yaml"
MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5",
    "gpt-5.1",
    "gpt-5.2",
    "gpt-5.1-codex",
]

PLAIN_PROMPT = "Say hello in one short sentence."
ACTION_PROMPT = "What is on my Desktop? Use tools if needed."


def _load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _filter_llm_config(cfg: dict) -> dict:
    valid = set(LLMGatewayConfig.__dataclass_fields__.keys())
    return {k: v for k, v in cfg.items() if k in valid}


def _run_plain(model: str, base_llm_cfg: dict) -> dict:
    llm_cfg = dict(base_llm_cfg)
    llm_cfg["llm_model_name"] = model
    llm_cfg["llm_stream"] = False
    llm_cfg["llm_use_async"] = False
    client = LLMClient(LLMGatewayConfig(**llm_cfg))

    t0 = time.time()
    response = client.generate([
        {"role": "user", "content": PLAIN_PROMPT}
    ])
    t1 = time.time()
    return {
        "ok": True,
        "latency_s": round(t1 - t0, 2),
        "response": response,
    }


async def _run_action(model: str, base_config: dict) -> dict:
    config = dict(base_config)
    llm_cfg = dict(config.get("llm_gateway_config") or {})
    llm_cfg["llm_model_name"] = model
    llm_cfg["llm_stream"] = False
    llm_cfg["llm_use_async"] = False
    config["llm_gateway_config"] = llm_cfg

    brain = LLMBrain(config)
    brain.setup()

    result_text = ""
    async for chunk in brain.think([
        {"role": "user", "content": ACTION_PROMPT}
    ], stream=False, use_async=False):
        if isinstance(chunk, str):
            result_text += chunk

    envelope, parse_errors = parse_action_envelope(result_text)
    return {
        "ok": True,
        "parse_errors": parse_errors,
        "envelope_type": envelope.get("type"),
        "message_len": len(envelope.get("message") or ""),
    }


async def main():
    base = _load_config(CONFIG_PATH)
    base_llm_cfg = _filter_llm_config(base.get("llm_gateway_config") or {})

    results = []

    for model in MODELS:
        entry = {"model": model, "plain": None, "action": None}
        try:
            entry["plain"] = _run_plain(model, base_llm_cfg)
        except Exception as e:
            entry["plain"] = {"ok": False, "error": str(e)}

        try:
            entry["action"] = await _run_action(model, base)
        except Exception as e:
            entry["action"] = {"ok": False, "error": str(e)}

        results.append(entry)

    print("\n=== LLM Smoke Test Results ===")
    for entry in results:
        print(f"\nModel: {entry['model']}")
        plain = entry["plain"]
        action = entry["action"]
        if plain and plain.get("ok"):
            resp = plain.get("response", "").strip().replace("\n", " ")
            print(f"  Plain: OK ({plain.get('latency_s')}s) -> {resp[:120]}")
        else:
            print(f"  Plain: ERROR -> {plain.get('error') if plain else 'unknown'}")
        if action and action.get("ok"):
            print(
                "  Action: OK "
                f"type={action.get('envelope_type')} "
                f"parse_errors={action.get('parse_errors')} "
                f"message_len={action.get('message_len')}"
            )
        else:
            print(f"  Action: ERROR -> {action.get('error') if action else 'unknown'}")


if __name__ == "__main__":
    asyncio.run(main())
