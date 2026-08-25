import json
import secrets
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Generic, TypeVar

from ..observability import log
from ..settings import get_settings
from .guard import check_privacy_gate
from .pricing import compute_cost_usd
from .prompts import PROMPT_VERSION_JD_EXTRACTION_V1, SYSTEM_PROMPT_JD_EXTRACTION_V1
from .schemas import JobRequirementExtractionOutput, get_jd_extraction_json_schema

T = TypeVar("T")


class LLMError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LLMRefusedError(LLMError):
    def __init__(self, message: str = "The model refused to process the request.") -> None:
        super().__init__("llm_refused", message)


class LLMTruncatedError(LLMError):
    def __init__(self, message: str = "The model response was truncated.") -> None:
        super().__init__("llm_truncated", message)


class LLMSchemaViolationError(LLMError):
    def __init__(self, message: str = "The model response did not conform to schema.") -> None:
        super().__init__("schema_violation", message)


class LLMUnavailableError(LLMError):
    def __init__(self, message: str = "LLM provider is currently unavailable.") -> None:
        super().__init__("llm_unavailable", message)


class LLMRateLimitedError(LLMError):
    def __init__(self, message: str = "LLM provider rate limit exceeded.") -> None:
        super().__init__("llm_rate_limited", message)


@dataclass(frozen=True)
class LLMCallResult(Generic[T]):
    data: T
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: Decimal
    latency_ms: int
    model: str
    stop_reason: str
    attempt: int
    prompt_version_name: str


def assemble_job_user_message(normalized_text: str, nonce: str) -> str:
    """Assemble user message wrapping untrusted JD text in a nonce-delimited block."""
    return (
        f'<untrusted_job_description nonce="{nonce}">\n'
        f"{normalized_text}\n"
        f"</untrusted_job_description>\n\n"
        f"Extract all requirements from the job description above according to instructions."
    )


class LLMClient:
    """Interface for LLM extraction and matching operations."""

    def extract_job_requirements(
        self,
        normalized_text: str,
        *,
        is_fixture: bool = False,
        prompt_template: str = SYSTEM_PROMPT_JD_EXTRACTION_V1,
        prompt_version_name: str = PROMPT_VERSION_JD_EXTRACTION_V1,
    ) -> LLMCallResult[JobRequirementExtractionOutput]:
        raise NotImplementedError


class AnthropicLLMClient(LLMClient):
    """Production LLM client calling Anthropic Claude API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.timeout = settings.llm_timeout_seconds
        self.model = settings.llm_model
        self.fallback_model = settings.llm_fallback_model

    def extract_job_requirements(
        self,
        normalized_text: str,
        *,
        is_fixture: bool = False,
        prompt_template: str = SYSTEM_PROMPT_JD_EXTRACTION_V1,
        prompt_version_name: str = PROMPT_VERSION_JD_EXTRACTION_V1,
    ) -> LLMCallResult[JobRequirementExtractionOutput]:
        # 1. Enforce privacy launch gate
        check_privacy_gate(is_fixture=is_fixture)

        if not self.api_key:
            raise LLMUnavailableError("LLM API key is not configured.")

        settings = get_settings()
        max_output_tokens = settings.llm_max_output_tokens_extraction
        schema = get_jd_extraction_json_schema()

        nonce = secrets.token_hex(8)
        user_content = assemble_job_user_message(normalized_text, nonce)

        # We allow at most 1 retry, plus at most 1 fallback attempt
        current_model = self.model
        attempt = 1
        last_error: Exception | None = None

        while attempt <= 3:
            start_time = time.perf_counter()
            log("llm_call_started", purpose="jd_extraction", model=current_model, attempt=attempt)
            try:
                result_data, input_tokens, output_tokens, cache_read, cache_write, stop_reason = (
                    self._call_anthropic_structured(
                        model=current_model,
                        system_prompt=prompt_template,
                        user_content=user_content,
                        schema=schema,
                        max_tokens=max_output_tokens,
                    )
                )
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                cost = compute_cost_usd(
                    current_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read,
                    cache_write_tokens=cache_write,
                )

                if stop_reason == "refusal":
                    # Refusal is not retried
                    log("llm_call_refused", model=current_model, latency_ms=latency_ms)
                    raise LLMRefusedError()

                if stop_reason == "max_tokens":
                    # One retry with doubled max_tokens
                    if attempt == 1:
                        max_output_tokens *= 2
                        attempt += 1
                        continue
                    raise LLMTruncatedError()

                # Validate Pydantic schema
                try:
                    output = JobRequirementExtractionOutput.model_validate(result_data)
                except Exception as exc:
                    raise LLMSchemaViolationError(str(exc)) from exc

                log(
                    "llm_call_completed",
                    purpose="jd_extraction",
                    model=current_model,
                    tokens=input_tokens + output_tokens,
                    cost=float(cost),
                    latency_ms=latency_ms,
                )

                return LLMCallResult(
                    data=output,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read,
                    cache_write_tokens=cache_write,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    model=current_model,
                    stop_reason=stop_reason,
                    attempt=attempt,
                    prompt_version_name=prompt_version_name,
                )

            except LLMRefusedError:
                raise
            except (
                LLMTruncatedError,
                LLMSchemaViolationError,
                LLMUnavailableError,
                LLMRateLimitedError,
                Exception,
            ) as exc:
                last_error = exc
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                log(
                    "llm_call_attempt_failed",
                    model=current_model,
                    attempt=attempt,
                    error=str(exc),
                    latency_ms=latency_ms,
                )
                if attempt == 1:
                    # Retry once on current model
                    attempt += 1
                    continue
                if attempt == 2 and current_model != self.fallback_model:
                    # Fallback once to Opus
                    current_model = self.fallback_model
                    attempt += 1
                    continue
                break

        if isinstance(last_error, LLMError):
            raise last_error
        raise LLMSchemaViolationError(f"Extraction failed after attempts: {last_error}")

    def _call_anthropic_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[dict[str, Any], int, int, int, int, str]:
        """Make HTTP request to Anthropic Messages API with tool-use structured outputs."""
        import httpx

        headers = {
            "x-api-key": str(self.api_key),
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "content-type": "application/json",
        }

        endpoint = (self.base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [{"role": "user", "content": user_content}],
            "tools": [
                {
                    "name": "record_extracted_requirements",
                    "description": "Record structured job requirements extracted from text.",
                    "input_schema": schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "record_extracted_requirements"},
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise LLMUnavailableError(f"Network error calling Anthropic: {exc}") from exc

        if response.status_code == 429:
            raise LLMRateLimitedError("Anthropic rate limit reached.")
        if response.status_code >= 500:
            raise LLMUnavailableError(f"Anthropic server error: {response.status_code}")
        if response.status_code != 200:
            raise LLMUnavailableError(f"Anthropic error {response.status_code}: {response.text}")

        res_json = response.json()
        stop_reason = res_json.get("stop_reason", "end_turn")
        usage = res_json.get("usage", {})
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        cache_read = int(usage.get("cache_read_input_tokens", 0))
        cache_write = int(usage.get("cache_creation_input_tokens", 0))

        if stop_reason == "refusal":
            return {}, input_tokens, output_tokens, cache_read, cache_write, "refusal"

        # Find tool use content block
        content_blocks = res_json.get("content", [])
        tool_input: dict[str, Any] = {}
        for block in content_blocks:
            if (
                block.get("type") == "tool_use"
                and block.get("name") == "record_extracted_requirements"
            ):
                tool_input = block.get("input", {})
                break

        if not tool_input:
            # Check if JSON was returned in plain text
            for block in content_blocks:
                if block.get("type") == "text":
                    try:
                        tool_input = json.loads(block.get("text", "{}"))
                        break
                    except Exception:
                        pass

        return tool_input, input_tokens, output_tokens, cache_read, cache_write, stop_reason


class MockLLMClient(LLMClient):
    """Deterministic Mock LLM Client for testing without external network calls."""

    def __init__(
        self,
        output: JobRequirementExtractionOutput | None = None,
        *,
        stop_reason: str = "end_turn",
        input_tokens: int = 1500,
        output_tokens: int = 400,
        cache_read_tokens: int = 200,
        cache_write_tokens: int = 0,
        should_refuse: bool = False,
        should_truncate: bool = False,
        should_fail_schema: bool = False,
        should_error: bool = False,
    ) -> None:
        self.output = output or JobRequirementExtractionOutput()
        self.stop_reason = stop_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_tokens = cache_read_tokens
        self.cache_write_tokens = cache_write_tokens
        self.should_refuse = should_refuse
        self.should_truncate = should_truncate
        self.should_fail_schema = should_fail_schema
        self.should_error = should_error
        self.calls: list[dict[str, Any]] = []

    def extract_job_requirements(
        self,
        normalized_text: str,
        *,
        is_fixture: bool = False,
        prompt_template: str = SYSTEM_PROMPT_JD_EXTRACTION_V1,
        prompt_version_name: str = PROMPT_VERSION_JD_EXTRACTION_V1,
    ) -> LLMCallResult[JobRequirementExtractionOutput]:
        # Enforce privacy gate even in mock client
        check_privacy_gate(is_fixture=is_fixture)

        self.calls.append(
            {
                "normalized_text": normalized_text,
                "is_fixture": is_fixture,
                "prompt_template": prompt_template,
                "prompt_version_name": prompt_version_name,
            }
        )

        if self.should_refuse:
            raise LLMRefusedError()
        if self.should_truncate:
            raise LLMTruncatedError()
        if self.should_fail_schema:
            raise LLMSchemaViolationError("Simulated schema violation")
        if self.should_error:
            raise LLMUnavailableError("Simulated provider error")

        cost = compute_cost_usd(
            "claude-sonnet-5",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_read_tokens=self.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens,
        )

        return LLMCallResult(
            data=self.output,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_read_tokens=self.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens,
            cost_usd=cost,
            latency_ms=120,
            model="claude-sonnet-5",
            stop_reason=self.stop_reason,
            attempt=1,
            prompt_version_name=prompt_version_name,
        )
