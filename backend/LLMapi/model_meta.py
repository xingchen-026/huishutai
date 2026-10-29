"""模型分类、调用参数规格生成与严格校验（业务层纯函数，无 IO）。"""

from __future__ import annotations

from typing import Any

CATEGORIES = ("chat", "embedding", "rerank", "image", "audio", "other")

CATEGORY_LABELS = {
    "chat": "对话",
    "embedding": "向量嵌入",
    "rerank": "重排序",
    "image": "图像生成",
    "audio": "语音",
    "other": "其它",
}

# 由系统控制的参数，用户不允许传入
PROTECTED_PARAMS = ("model", "messages", "input", "stream")

_EMBEDDING_KEYS = ("embed", "embedding", "bge", "gte", "m3e", "text-embedding")
_RERANK_KEYS = ("rerank",)
_IMAGE_KEYS = ("dall", "image", "imagen", "flux", "stable-diffusion", "sd3", "kolors", "seedream")
_AUDIO_KEYS = ("whisper", "tts", "speech", "audio", "voice", "asr", "paraformer")

_TYPE_CHECKS = {
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "string_list": lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
    "object": lambda v: isinstance(v, dict),
    "list": lambda v: isinstance(v, list),
}


def classify_model(protocol: str, model_id: str, raw: dict | None = None) -> str:
    """按供应商元信息/模型 ID 归类到 CATEGORIES 之一。"""
    model_id = (model_id or "").lower()
    raw = raw or {}

    if protocol == "gemini":
        methods = [str(m).lower() for m in (raw.get("supportedGenerationMethods") or [])]
        if "embedcontent" in methods:
            return "embedding"
        if "generatecontent" in methods:
            return "chat"

    for keys, category in (
        (_EMBEDDING_KEYS, "embedding"),
        (_RERANK_KEYS, "rerank"),
        (_IMAGE_KEYS, "image"),
        (_AUDIO_KEYS, "audio"),
    ):
        if any(key in model_id for key in keys):
            return category
    return "chat"


def _max_output_tokens(model_id: str) -> int:
    """各模型最大输出 token 的最佳努力估算（用于参数上界，减少无效调用）。"""
    model_id = (model_id or "").lower()
    if "reasoner" in model_id or model_id.startswith(("o1", "o3", "o4")):
        return 100000
    if "deepseek-chat" in model_id:
        return 8192
    if "deepseek" in model_id:
        return 65536
    if "claude" in model_id:
        return 64000
    if "gemini" in model_id:
        return 65536
    if "qwen" in model_id:
        return 16384
    if "kimi" in model_id or "moonshot" in model_id:
        return 8192
    if "gpt-4o" in model_id:
        return 16384
    if "gpt-4.1" in model_id:
        return 32768
    return 32768


def _param(
    name: str,
    type_name: str,
    *,
    default: Any = None,
    required: bool = False,
    minimum: Any = None,
    maximum: Any = None,
    enum: list | None = None,
    description: str = "",
) -> dict:
    item: dict[str, Any] = {
        "name": name,
        "type": type_name,
        "required": required,
        "description": description,
    }
    if default is not None:
        item["default"] = default
    if minimum is not None:
        item["minimum"] = minimum
    if maximum is not None:
        item["maximum"] = maximum
    if enum is not None:
        item["enum"] = enum
    return item


def build_param_spec(protocol: str, category: str, model_id: str) -> list[dict]:
    """生成某个模型的调用参数白名单（入库保存，调用时据此校验）。"""
    if category == "embedding":
        if protocol == "gemini":
            return [
                _param(
                    "task_type",
                    "enum",
                    enum=[
                        "RETRIEVAL_QUERY",
                        "RETRIEVAL_DOCUMENT",
                        "SEMANTIC_SIMILARITY",
                        "CLASSIFICATION",
                        "CLUSTERING",
                    ],
                    description="Gemini 嵌入任务类型",
                ),
            ]
        return [
            _param(
                "dimensions",
                "integer",
                minimum=1,
                maximum=8192,
                description="输出向量维度（部分模型支持）",
            ),
            _param(
                "encoding_format",
                "enum",
                default="float",
                enum=["float", "base64"],
                description="向量编码格式",
            ),
            _param("user", "string", description="调用方标识"),
        ]

    if category != "chat":
        return []

    limit = _max_output_tokens(model_id)

    if protocol == "anthropic":
        return [
            _param(
                "temperature",
                "number",
                default=1.0,
                minimum=0.0,
                maximum=1.0,
                description="采样温度",
            ),
            _param("top_p", "number", default=1.0, minimum=0.0, maximum=1.0, description="核采样"),
            _param("top_k", "integer", minimum=1, maximum=500, description="Top-K 采样"),
            _param(
                "max_tokens",
                "integer",
                default=1024,
                required=True,
                minimum=1,
                maximum=limit,
                description="最大输出 token 数（Anthropic 必填）",
            ),
            _param("stop", "string_list", description="停止词列表"),
        ]

    if protocol == "gemini":
        return [
            _param(
                "temperature",
                "number",
                default=1.0,
                minimum=0.0,
                maximum=2.0,
                description="采样温度",
            ),
            _param("top_p", "number", default=1.0, minimum=0.0, maximum=1.0, description="核采样"),
            _param("top_k", "integer", minimum=1, maximum=200, description="Top-K 采样"),
            _param(
                "max_tokens",
                "integer",
                default=2048,
                minimum=1,
                maximum=limit,
                description="最大输出 token 数",
            ),
            _param("stop", "string_list", description="停止词列表"),
        ]

    # openai 兼容协议
    return [
        _param(
            "temperature", "number", default=1.0, minimum=0.0, maximum=2.0, description="采样温度"
        ),
        _param("top_p", "number", default=1.0, minimum=0.0, maximum=1.0, description="核采样"),
        _param(
            "max_tokens",
            "integer",
            minimum=1,
            maximum=limit,
            description="最大输出 token 数（不传用供应商默认）",
        ),
        _param("presence_penalty", "number", default=0.0, minimum=-2.0, maximum=2.0),
        _param("frequency_penalty", "number", default=0.0, minimum=-2.0, maximum=2.0),
        _param("stop", "string_list", description="停止词列表"),
        _param("seed", "integer", minimum=0, maximum=2147483647),
        _param(
            "n",
            "integer",
            default=1,
            minimum=1,
            maximum=16,
            description="生成条数（网关只返回第一条）",
        ),
        _param("user", "string", description="调用方标识"),
    ]


def validate_messages(messages: Any) -> tuple[list[dict], list[str]]:
    if not isinstance(messages, list) or not messages:
        return [], ["messages 必须是非空数组"]
    errors: list[str] = []
    cleaned: list[dict] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            errors.append(f"messages[{index}] 必须是对象")
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in ("system", "user", "assistant"):
            errors.append(f"messages[{index}].role 只能是 system/user/assistant")
            continue
        if not isinstance(content, str) and not isinstance(content, list):
            errors.append(f"messages[{index}].content 必须是字符串或数组")
            continue
        cleaned.append({"role": role, "content": content})
    if not any(item["role"] == "user" for item in cleaned):
        errors.append("messages 至少需要一条 user 消息")
    return cleaned, errors


def validate_embedding_input(value: Any) -> tuple[list[str], list[str]]:
    if isinstance(value, str):
        return ([value], []) if value.strip() else ([], ["input 不能为空"])
    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item.strip() for item in value)
    ):
        return value, []
    return [], ["input 必须是字符串，或非空字符串数组"]


def validate_params(
    param_spec: list[dict] | None,
    user_params: Any,
    *,
    protected: tuple[str, ...] = PROTECTED_PARAMS,
) -> tuple[dict, list[str]]:
    """按模型参数规格严格校验；返回 (合并默认值后的参数, 错误列表)。"""
    if user_params is None:
        user_params = {}
    if not isinstance(user_params, dict):
        return {}, ["params 必须是 JSON 对象"]

    spec_list = param_spec or []
    spec_map = {item["name"]: item for item in spec_list}
    errors: list[str] = []

    for key in user_params:
        if key in protected:
            errors.append(f"参数 {key} 由系统控制，不允许传入")

    merged: dict[str, Any] = {}
    for item in spec_list:
        if "default" in item and item["name"] not in user_params:
            merged[item["name"]] = item["default"]

    for name, value in user_params.items():
        if name in protected:
            continue
        item = spec_map.get(name)
        if item is None:
            errors.append(f"不支持的参数：{name}")
            continue

        type_name = item.get("type", "string")
        if type_name == "string_list" and isinstance(value, str):
            value = [value]
        checker = _TYPE_CHECKS.get(type_name)
        if checker is not None and not checker(value):
            errors.append(f"参数 {name} 类型应为 {type_name}")
            continue

        if type_name in ("number", "integer"):
            minimum = item.get("minimum")
            maximum = item.get("maximum")
            if minimum is not None and value < minimum:
                errors.append(f"参数 {name} 不能小于 {minimum}")
                continue
            if maximum is not None and value > maximum:
                errors.append(f"参数 {name} 不能大于 {maximum}")
                continue

        enum = item.get("enum")
        if enum is not None and value not in enum:
            errors.append(f"参数 {name} 只能是 {enum} 之一")
            continue

        merged[name] = value

    for item in spec_list:
        if item.get("required") and item["name"] not in merged:
            errors.append(f"缺少必填参数：{item['name']}")

    return merged, errors
