# File: cognition/brain/llm_brain.py

import asyncio
import json
from uuid import uuid4
from typing import Any, List, Dict, AsyncGenerator, Optional
import logging
from aeiva.cognition.brain.base_brain import Brain
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

logger = logging.getLogger(__name__)

class LLMBrain(Brain):
    """
    Concrete implementation of the Brain, using an LLM to process stimuli
    and generate cognitive states.

    This brain uses the LLMClient to communicate with a language model to
    process input stimuli and produce outputs.
    """

    def __init__(self, config: Dict):
        """
        Initialize the LLMBrain with the provided LLM configuration.

        Args:
            config (LLMGatewayConfig): Configuration settings for the LLMBrain.
        """
        super().__init__(config)
        self.config_dict = config
        self.config = None
        self.llm_client = None

    def init_state(self) -> Any:
        """
        Initialize the internal state of the Brain.

        The state can track the ongoing conversation or task context.

        Returns:
            dict: Initial empty state.
        """
        return {
            "conversation": [],
            "cognitive_state": None,
            "pending_tool_call": None,
        }

    def setup(self) -> None:
        """
        Set up the Brain's components.

        For the LLMBrain, this might involve validating the LLM configuration
        and ensuring that all necessary resources are in place.
        """
        llm_conf_dict = self.config_dict.get('llm_gateway_config', {})
        llm_api_key = llm_conf_dict.get('llm_api_key')
        self.config = LLMGatewayConfig(
            llm_api_key=llm_api_key,
            llm_model_name=llm_conf_dict.get('llm_model_name', 'gpt-4o'),
            llm_temperature=llm_conf_dict.get('llm_temperature', 0.7),
            llm_max_output_tokens=llm_conf_dict.get('llm_max_output_tokens', 10000),
            llm_timeout=llm_conf_dict.get('llm_timeout', 120),
            llm_use_async=llm_conf_dict.get('llm_use_async', False),
            llm_stream=llm_conf_dict.get('llm_stream', False),
            llm_api_mode=llm_conf_dict.get("llm_api_mode", "auto"),
            llm_tool_choice=llm_conf_dict.get("llm_tool_choice"),
            llm_additional_params=llm_conf_dict.get("llm_additional_params") or {},
            llm_custom_provider=llm_conf_dict.get("llm_custom_provider"),
        )
        self.llm_client = LLMClient(self.config)

        system_prompt = self._build_system_prompt(llm_conf_dict)
        if system_prompt is not None:  # TODO: only add system prompt for llms that support it.
            self.state["conversation"].append({"role": "system", "content": system_prompt})
        
        logger.info("LLMBrain setup complete.")

    async def think(
            self,
            stimuli: Any,
            tools: List[Dict[str, Any]] = None,
            stream: bool = False,
            use_async: bool = False,
            tool_choice: Any = None,
            ) -> AsyncGenerator[str, None]:
        """
        Asynchronously process input stimuli to update the cognitive state.

        Args:
            stimuli (Any): The input stimuli to process.
            stream (bool): Whether to use streaming mode. Default is False.

        Returns:
            str: The full response in both streaming and non-streaming modes.
        """
        try:
            # Assume stimuli is a list of messages (conversation context)
            if not isinstance(stimuli, list):
                raise ValueError("Stimuli must be a list of messages.")
            
            self.state["conversation"].extend(stimuli)  # keep local history
            messages = self._build_messages_for_llm(stimuli)

            # Approval retry path: if we have a pending tool call and user confirms, run it directly.
            pending = self.state.get("pending_tool_call")
            user_text = self._latest_user_text(stimuli)
            decision = self._detect_approval_decision(user_text) if pending else None
            if pending and decision == "approve":
                response = await self._execute_pending_tool_call(pending, tools, stream, use_async)
                yield response
                return
            if pending and decision == "deny":
                self.state["pending_tool_call"] = None
                yield "Understood. I won't proceed with that action."
                return

            response_parts: List[str] = []
            use_async = use_async or stream  # streaming requires async

            if use_async:
                if stream:
                    extra = {"tool_choice": tool_choice} if tool_choice is not None else {}
                    async for delta in self.llm_client.astream(
                        messages,
                        tools=tools,
                        stream=stream,
                        **extra,
                    ):
                        response_parts.append(delta)
                        yield delta
                else:
                    extra = {"tool_choice": tool_choice} if tool_choice is not None else {}
                    result = await self.llm_client.arun(
                        messages,
                        tools=tools,
                        stream=False,
                        **extra,
                    )
                    response_parts.append(result.text)
                    yield result.text
            else:
                extra = {"tool_choice": tool_choice} if tool_choice is not None else {}
                result = await asyncio.to_thread(
                    self.llm_client.run,
                    messages,
                    tools,
                    stream=False,
                    **extra,
                )
                response_parts.append(result.text)
                yield result.text

            self.state["cognitive_state"] = "".join(response_parts)
            self._refresh_pending_tool_call()

        except Exception as e:
            if use_async and not stream:
                try:
                    result = await asyncio.to_thread(
                        self.llm_client.run,
                        self.state["conversation"],
                        tools=tools,
                        stream=False,
                    )
                    self.state["cognitive_state"] = result.text
                    yield result.text
                    return
                except Exception:
                    pass
            self.handle_error(e)
            raise

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during cognitive processing.

        Args:
            error (Exception): The exception that was raised.
        """
        super().handle_error(error)
        # Custom error handling logic for LLM-related issues
        logger.error("LLMBrain encountered an error: %s", error)

    def _build_messages_for_llm(self, stimuli: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build minimal message list for LLM calls."""
        return self.state["conversation"]

    def _build_system_prompt(self, llm_conf_dict: Dict[str, Any]) -> Optional[str]:
        """Return the base system prompt without action JSON instructions."""
        return llm_conf_dict.get('llm_system_prompt')

    def _latest_user_text(self, stimuli: List[Dict[str, Any]]) -> str:
        if not isinstance(stimuli, list):
            return ""
        for msg in reversed(stimuli):
            if not isinstance(msg, dict):
                continue
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                return content.strip().lower()
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                joined = " ".join(parts).strip().lower()
                if joined:
                    return joined
        return ""

    def _detect_approval_decision(self, user_text: str) -> Optional[str]:
        if not user_text:
            return None
        approve = {"yes", "y", "ok", "okay", "proceed", "go ahead", "do it", "sure", "确认", "可以", "好的", "oui"}
        deny = {"no", "n", "stop", "cancel", "don't", "do not", "不要", "否", "non"}
        if user_text in approve or any(user_text.startswith(a) for a in approve):
            return "approve"
        if user_text in deny or any(user_text.startswith(d) for d in deny):
            return "deny"
        return None

    async def _execute_pending_tool_call(
        self,
        pending: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]],
        stream: bool,
        use_async: bool,
    ) -> str:
        tool_name = pending.get("name")
        args = pending.get("args") or {}
        call_id = pending.get("id") or ""
        if not tool_name:
            self.state["pending_tool_call"] = None
            return "Unable to proceed: pending tool information is missing."
        if not call_id:
            call_id = f"call_{uuid4().hex}"

        # Add assistant tool call message
        tool_call_msg = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args),
                    },
                }
            ],
        }
        self.state["conversation"].append(tool_call_msg)

        # Execute tool
        args_for_tool = dict(args)
        args_for_tool["__approved"] = True
        try:
            result = await self.llm_client.call_tool(tool_name, args_for_tool)
        except Exception as exc:
            result = {"success": False, "error": str(exc)}
        self.state["conversation"].append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result),
        })
        self.state["pending_tool_call"] = None

        # Ask LLM to respond to tool result
        response_parts: List[str] = []
        if stream:
            async for delta in self.llm_client.astream(self.state["conversation"], tools=tools, stream=True):
                response_parts.append(delta)
            return "".join(response_parts)

        result_obj = await self.llm_client.arun(self.state["conversation"], tools=tools, stream=False)
        return result_obj.text

    def _refresh_pending_tool_call(self) -> None:
        self.state["pending_tool_call"] = None
        history = self.state.get("conversation") or []
        if not isinstance(history, list):
            return

        # Find the most recent tool result.
        last_tool_msg = None
        for msg in reversed(history):
            if isinstance(msg, dict) and msg.get("role") == "tool":
                last_tool_msg = msg
                break
        if not last_tool_msg:
            return

        try:
            content = last_tool_msg.get("content") or ""
            data = json.loads(content) if isinstance(content, str) else content
        except Exception:
            return

        if not isinstance(data, dict) or data.get("error") != "approval_required":
            return

        call_id = last_tool_msg.get("tool_call_id") or ""
        if not call_id:
            return
        # Find matching tool call for args
        tool_name = last_tool_msg.get("name")
        args = None
        for msg in reversed(history):
            if not isinstance(msg, dict):
                continue
            if msg.get("role") != "assistant":
                continue
            tool_calls = msg.get("tool_calls") or []
            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                if tc.get("id") != call_id:
                    continue
                func = tc.get("function") or {}
                tool_name = func.get("name") or tool_name
                raw_args = func.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}
                break
            if args is not None:
                break

        if tool_name and args is not None:
            self.state["pending_tool_call"] = {
                "id": call_id,
                "name": tool_name,
                "args": args,
            }
