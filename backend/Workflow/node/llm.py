"""大模型节点：通过项目统一模型网关调用 chat 模型。"""

from __future__ import annotations

from LLMapi import services as llm_services
from LLMapi.result import LLMStatus
from Workflow.node.base import NodeError, NodeResult, render_template

NODE_META = {
    "name": "大模型",
    "description": "调用「模型服务」中已启用的对话模型。",
    "category": "AI",
    "inputs": [{"id": "in", "label": "输入"}],
    "outputs": [{"id": "out", "label": "输出"}],
    "params": [
        {
            "key": "model_id",
            "label": "模型 ID",
            "type": "number",
            "required": True,
            "help": "在「模型服务」页面查看模型主键 ID。",
        },
        {
            "key": "system_prompt",
            "label": "系统提示词",
            "type": "textarea",
            "default": "你是一个简洁的助手。",
            "required": False,
        },
        {
            "key": "prompt",
            "label": "用户提示词",
            "type": "textarea",
            "default": "{{input}}",
            "required": False,
            "help": "支持 {{input}} 占位，替换为上游节点输出的 JSON。",
        },
        {
            "key": "temperature",
            "label": "temperature",
            "type": "number",
            "default": 0.7,
            "required": False,
        },
        {
            "key": "max_tokens",
            "label": "max_tokens",
            "type": "number",
            "default": 512,
            "required": False,
        },
    ],
}


def execute(config: dict, input_data: dict, context) -> NodeResult:
    try:
        model_id = int(config.get("model_id"))
    except (TypeError, ValueError) as exc:
        raise NodeError("请配置有效的模型 ID") from exc

    prompt = render_template(str(config.get("prompt") or "{{input}}"), input_data)
    messages = []
    system_prompt = str(config.get("system_prompt") or "").strip()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    params = {}
    if config.get("temperature") not in (None, ""):
        try:
            params["temperature"] = float(config["temperature"])
        except (TypeError, ValueError) as exc:
            raise NodeError("temperature 必须是数字") from exc
    if config.get("max_tokens") not in (None, ""):
        try:
            params["max_tokens"] = int(config["max_tokens"])
        except (TypeError, ValueError) as exc:
            raise NodeError("max_tokens 必须是整数") from exc

    model_owner = getattr(context.workflow, "owner", None) or context.user
    result = llm_services.chat_completion(
        model_owner,
        {"model_id": model_id, "messages": messages, "params": params},
    )
    if result.code != LLMStatus.SUCCESS:
        raise NodeError(f"模型调用失败：{result.message}")

    data = result.data or {}
    return NodeResult(
        output={
            "content": data.get("content", ""),
            "usage": data.get("usage", {}),
            "model": data.get("model", ""),
            "provider": data.get("provider", ""),
        },
        logs=[f"调用模型：{data.get('model', model_id)}"],
    )
