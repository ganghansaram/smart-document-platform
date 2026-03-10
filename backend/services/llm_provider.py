"""
LLM 프로바이더 추상화 레이어

지원 프로바이더:
- ollama: Ollama API (현재 기본)
- openai_compat: OpenAI-compatible API (vLLM, NIM, TGI, 사내 MLOps)
"""
import json
import logging
from typing import AsyncIterator, Optional

import httpx

import config

logger = logging.getLogger(__name__)


class LLMProvider:
    """LLM 프로바이더 인터페이스"""

    async def generate(self, prompt: str, system: Optional[str] = None, **opts) -> str:
        """동기식 응답 생성 (전체 텍스트 반환)"""
        raise NotImplementedError

    async def generate_stream(self, prompt: str, system: Optional[str] = None, **opts) -> AsyncIterator[str]:
        """스트리밍 응답 생성 (토큰 단위 yield)"""
        raise NotImplementedError
        yield  # noqa: make it a generator

    async def health_check(self) -> bool:
        """프로바이더 연결 상태 확인"""
        return False

    @property
    def model_name(self) -> str:
        """현재 사용 중인 모델 이름"""
        return "unknown"


class OllamaProvider(LLMProvider):
    """Ollama API 프로바이더 (기존 호환)"""

    def __init__(self, url: str, model: str):
        self.url = url.rstrip("/")
        self.model = model

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(self, prompt: str, system: Optional[str] = None, **opts) -> str:
        temperature = opts.get("temperature", 0)
        timeout = opts.get("timeout", 120)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.url}/api/generate",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def generate_stream(self, prompt: str, system: Optional[str] = None, **opts) -> AsyncIterator[str]:
        temperature = opts.get("temperature", 0)
        timeout = opts.get("timeout", 300)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.url}/api/generate",
                json=payload,
                timeout=timeout,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.url}/api/tags", timeout=5)
                return resp.status_code == 200
        except Exception:
            return False


class OpenAICompatProvider(LLMProvider):
    """OpenAI-compatible API 프로바이더 (vLLM, NIM, TGI, 사내 MLOps)"""

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    @property
    def model_name(self) -> str:
        return self.model

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(self, prompt: str, system: Optional[str] = None, **opts) -> str:
        temperature = opts.get("temperature", 0)
        timeout = opts.get("timeout", 120)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(self, prompt: str, system: Optional[str] = None, **opts) -> AsyncIterator[str]:
        temperature = opts.get("temperature", 0)
        timeout = opts.get("timeout", 300)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=timeout,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._headers(),
                    timeout=5,
                )
                return resp.status_code == 200
        except Exception:
            return False


# ── 프로바이더 팩토리 ──

_provider_instance: Optional[LLMProvider] = None


def get_provider() -> LLMProvider:
    """현재 설정에 맞는 LLM 프로바이더 인스턴스 반환 (싱글턴)"""
    global _provider_instance

    provider_type = getattr(config, "LLM_PROVIDER", "ollama")

    # 설정 변경 감지 → 인스턴스 재생성
    if _provider_instance is not None:
        if provider_type == "ollama" and isinstance(_provider_instance, OllamaProvider):
            if _provider_instance.url == config.OLLAMA_URL and _provider_instance.model == config.OLLAMA_MODEL:
                return _provider_instance
        elif provider_type == "openai_compat" and isinstance(_provider_instance, OpenAICompatProvider):
            endpoint = getattr(config, "LLM_ENDPOINT", "")
            model_id = getattr(config, "LLM_MODEL_ID", "")
            if _provider_instance.base_url == endpoint and _provider_instance.model == model_id:
                return _provider_instance

    # 새 인스턴스 생성
    if provider_type == "openai_compat":
        endpoint = getattr(config, "LLM_ENDPOINT", "")
        api_key = getattr(config, "LLM_API_KEY", "")
        model_id = getattr(config, "LLM_MODEL_ID", "")
        if not endpoint or not model_id:
            logger.warning("OpenAI-compat 설정 불완전 → Ollama 폴백")
            _provider_instance = OllamaProvider(config.OLLAMA_URL, config.OLLAMA_MODEL)
        else:
            _provider_instance = OpenAICompatProvider(endpoint, model_id, api_key)
            logger.info("LLM 프로바이더: OpenAI-compat (%s, %s)", endpoint, model_id)
    else:
        _provider_instance = OllamaProvider(config.OLLAMA_URL, config.OLLAMA_MODEL)
        logger.info("LLM 프로바이더: Ollama (%s, %s)", config.OLLAMA_URL, config.OLLAMA_MODEL)

    return _provider_instance


def reset_provider():
    """프로바이더 인스턴스 초기화 (설정 변경 시 호출)"""
    global _provider_instance
    _provider_instance = None
