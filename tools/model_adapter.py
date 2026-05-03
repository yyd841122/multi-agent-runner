"""
多模型 API 适配器 MVP

统一模型调用接口，支持为不同 Agent 配置不同模型。
当前实现 mock provider，预留 zhipu / deepseek / kimi / qwen provider。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ModelRequest:
    """模型调用请求。"""
    agent: str
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.2


@dataclass
class ModelResponse:
    """模型调用响应。"""
    provider: str
    model: str
    agent: str
    success: bool
    content: str
    raw: Any | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def load_model_config(config_path: str | Path = "config.yaml") -> dict:
    """读取模型配置。"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_agent_model_config(config: dict, agent: str) -> dict:
    """根据 agent 名称获取模型配置。

    查找 config.models.<agent>，如果不存在则使用 default_provider。
    返回 dict，包含 provider 和 model 字段。
    """
    models_cfg = config.get("models", {})
    providers_cfg = config.get("providers", {})

    agent_cfg = models_cfg.get(agent, None)
    if agent_cfg is None:
        # 使用 default_provider
        default_provider = models_cfg.get("default_provider", "mock")
        provider_cfg = providers_cfg.get(default_provider, {})
        return {
            "provider": default_provider,
            "model": provider_cfg.get("default_model", f"mock-{agent}"),
        }

    provider_name = agent_cfg.get("provider", models_cfg.get("default_provider", "mock"))
    provider_cfg = providers_cfg.get(provider_name, {})

    return {
        "provider": provider_name,
        "model": agent_cfg.get("model", provider_cfg.get("default_model", f"mock-{agent}")),
    }


# ---------------------------------------------------------------------------
# Provider 实现
# ---------------------------------------------------------------------------

def call_mock_provider(
    request: ModelRequest,
    provider_config: dict,
    model_config: dict,
) -> ModelResponse:
    """本地 mock provider，用于不接真实 API 时验证流程。"""
    prompt_preview = request.prompt[:200] + "..." if len(request.prompt) > 200 else request.prompt

    content = (
        f"[MOCK MODEL RESPONSE]\n"
        f"\n"
        f"agent: {request.agent}\n"
        f"provider: mock\n"
        f"model: {model_config.get('model', 'mock')}\n"
        f"temperature: {request.temperature}\n"
        f"\n"
        f"收到的 prompt 摘要：\n"
        f"{prompt_preview}\n"
        f"\n"
        f"system_prompt: {request.system_prompt or '(无)'}\n"
        f"\n"
        f"这是 mock 响应，不会调用真实 API。\n"
        f"要启用真实 API，请修改 config.yaml 中的 provider 配置。\n"
    )

    return ModelResponse(
        provider="mock",
        model=model_config.get("model", "mock"),
        agent=request.agent,
        success=True,
        content=content,
    )


def call_zhipu_provider(
    request: ModelRequest,
    provider_config: dict,
    model_config: dict,
) -> ModelResponse:
    """智谱 (GLM) provider — 预留，T016 不实现真实调用。"""
    raise NotImplementedError("zhipu provider 尚未在 T016 实现真实调用。")


def call_deepseek_provider(
    request: ModelRequest,
    provider_config: dict,
    model_config: dict,
) -> ModelResponse:
    """DeepSeek provider — 预留，T016 不实现真实调用。"""
    raise NotImplementedError("deepseek provider 尚未在 T016 实现真实调用。")


def call_kimi_provider(
    request: ModelRequest,
    provider_config: dict,
    model_config: dict,
) -> ModelResponse:
    """Kimi (Moonshot) provider — 预留，T016 不实现真实调用。"""
    raise NotImplementedError("kimi provider 尚未在 T016 实现真实调用。")


def call_qwen_provider(
    request: ModelRequest,
    provider_config: dict,
    model_config: dict,
) -> ModelResponse:
    """Qwen (通义千问) provider — 预留，T016 不实现真实调用。"""
    raise NotImplementedError("qwen provider 尚未在 T016 实现真实调用。")


# ---------------------------------------------------------------------------
# Provider 路由
# ---------------------------------------------------------------------------

PROVIDER_MAP = {
    "mock": call_mock_provider,
    "zhipu": call_zhipu_provider,
    "deepseek": call_deepseek_provider,
    "kimi": call_kimi_provider,
    "qwen": call_qwen_provider,
}


# ---------------------------------------------------------------------------
# 统一调用入口
# ---------------------------------------------------------------------------

def call_model(
    request: ModelRequest,
    config_path: str | Path = "config.yaml",
) -> ModelResponse:
    """统一模型调用入口。

    根据 config.yaml 中 agent 对应的 provider 配置，路由到对应 provider 函数。
    """
    try:
        config = load_model_config(config_path)
    except FileNotFoundError as e:
        return ModelResponse(
            provider="unknown",
            model="unknown",
            agent=request.agent,
            success=False,
            content="",
            error=str(e),
        )

    model_config = get_agent_model_config(config, request.agent)
    provider_name = model_config["provider"]

    providers_cfg = config.get("providers", {})
    provider_config = providers_cfg.get(provider_name, {})

    # 检查 provider 是否存在
    provider_fn = PROVIDER_MAP.get(provider_name)
    if provider_fn is None:
        return ModelResponse(
            provider=provider_name,
            model=model_config.get("model", "unknown"),
            agent=request.agent,
            success=False,
            content="",
            error=f"未知 provider: {provider_name}",
        )

    # 检查 provider 是否启用
    if not provider_config.get("enabled", False) and provider_name != "mock":
        return ModelResponse(
            provider=provider_name,
            model=model_config.get("model", "unknown"),
            agent=request.agent,
            success=False,
            content="",
            error=f"provider '{provider_name}' 未启用，请在 config.yaml 中设置 enabled: true",
        )

    # 调用 provider
    try:
        return provider_fn(request, provider_config, model_config)
    except NotImplementedError as e:
        return ModelResponse(
            provider=provider_name,
            model=model_config.get("model", "unknown"),
            agent=request.agent,
            success=False,
            content="",
            error=str(e),
        )
    except Exception as e:
        return ModelResponse(
            provider=provider_name,
            model=model_config.get("model", "unknown"),
            agent=request.agent,
            success=False,
            content="",
            error=f"provider 调用失败: {type(e).__name__}: {e}",
        )


# ---------------------------------------------------------------------------
# 本地测试
# ---------------------------------------------------------------------------

def model_test(agent: str = "reviewer", prompt: str = "请测试模型适配器。") -> ModelResponse:
    """本地测试模型适配器。"""
    request = ModelRequest(agent=agent, prompt=prompt)
    return call_model(request)


if __name__ == "__main__":
    import sys
    agent = sys.argv[1] if len(sys.argv) > 1 else "reviewer"
    prompt = sys.argv[2] if len(sys.argv) > 2 else "请测试模型适配器。"
    result = model_test(agent, prompt)
    print(f"provider: {result.provider}")
    print(f"model: {result.model}")
    print(f"agent: {result.agent}")
    print(f"success: {result.success}")
    print(f"error: {result.error}")
    print(f"content:\n{result.content}")
