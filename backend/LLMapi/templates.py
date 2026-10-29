"""内置供应商模板（不包含模型列表；模型一律在线拉取或用户手动登记）。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderTemplate:
    code: str
    name: str
    protocol: str  # openai / anthropic / gemini
    default_base_url: str
    docs_url: str
    requires_api_key: bool = True
    description: str = ""


_PROVIDER_TEMPLATES = (
    ProviderTemplate(
        "openai", "OpenAI", "openai",
        "https://api.openai.com/v1",
        "https://platform.openai.com/docs/api-reference",
        True, "OpenAI 官方接口（/models、/chat/completions、/embeddings）",
    ),
    ProviderTemplate(
        "deepseek", "DeepSeek", "openai",
        "https://api.deepseek.com/v1",
        "https://api-docs.deepseek.com/",
        True, "DeepSeek 官方接口，OpenAI 兼容",
    ),
    ProviderTemplate(
        "zhipu", "智谱 GLM", "openai",
        "https://open.bigmodel.cn/api/paas/v4",
        "https://open.bigmodel.cn/dev/api",
        True, "智谱 BigModel，OpenAI 兼容",
    ),
    ProviderTemplate(
        "moonshot", "Moonshot Kimi", "openai",
        "https://api.moonshot.cn/v1",
        "https://platform.moonshot.cn/docs",
        True, "Moonshot Kimi，OpenAI 兼容",
    ),
    ProviderTemplate(
        "dashscope", "阿里云百炼（Qwen）", "openai",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "https://help.aliyun.com/zh/model-studio/",
        True, "阿里云百炼 DashScope 兼容模式",
    ),
    ProviderTemplate(
        "siliconflow", "硅基流动 SiliconFlow", "openai",
        "https://api.siliconflow.cn/v1",
        "https://docs.siliconflow.cn/",
        True, "SiliconFlow，OpenAI 兼容（含 chat/embedding/rerank）",
    ),
    ProviderTemplate(
        "openrouter", "OpenRouter", "openai",
        "https://openrouter.ai/api/v1",
        "https://openrouter.ai/docs",
        True, "OpenRouter 聚合网关，OpenAI 兼容",
    ),
    ProviderTemplate(
        "ollama", "Ollama（本地）", "openai",
        "http://127.0.0.1:11434/v1",
        "https://github.com/ollama/ollama/blob/main/docs/openai.md",
        False, "本地 Ollama，OpenAI 兼容；不需要 API Key",
    ),
    ProviderTemplate(
        "anthropic", "Anthropic Claude", "anthropic",
        "https://api.anthropic.com",
        "https://docs.anthropic.com/en/api/",
        True, "Anthropic Messages API（/v1/models、/v1/messages）",
    ),
    ProviderTemplate(
        "gemini", "Google Gemini", "gemini",
        "https://generativelanguage.googleapis.com",
        "https://ai.google.dev/api",
        True, "Gemini Generative Language API（/v1beta/models 等）",
    ),
)

_TEMPLATE_MAP = {item.code: item for item in _PROVIDER_TEMPLATES}


def get_template(code: str) -> ProviderTemplate | None:
    return _TEMPLATE_MAP.get((code or "").strip())


def list_templates() -> list[dict]:
    return [
        {
            "code": item.code,
            "name": item.name,
            "protocol": item.protocol,
            "default_base_url": item.default_base_url,
            "docs_url": item.docs_url,
            "requires_api_key": item.requires_api_key,
            "description": item.description,
        }
        for item in _PROVIDER_TEMPLATES
    ]