
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


load_dotenv()


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class DeepSeekClient:
    """DeepSeek API client with controlled requests."""

    def __init__(
        self,
        api_key=None,
        model=None,
        base_url="https://api.deepseek.com",
        timeout=60.0,
    ):
        self.api_key = api_key or os.getenv(
            "DEEPSEEK_API_KEY"
        )

        self.model = model or os.getenv(
            "DEEPSEEK_MODEL",
            "deepseek-chat",
        )

        if not self.api_key:
            raise ValueError(
                "DeepSeek API key is missing."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
        )

        self.usage = TokenUsage()

    def chat(
        self,
        messages,
        tools=None,
        tool_choice=None,
        max_output_tokens=None,
    ):
        if not isinstance(messages, list) or not messages:
            raise ValueError(
                "Messages must be a non-empty list."
            )

        request = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        request["extra_body"] = {"thinking": {"type": "disabled"}}

        if tools is not None:
            request["tools"] = tools

        if tool_choice is not None:
            request["tool_choice"] = tool_choice

        if max_output_tokens is not None:
            if (
                isinstance(max_output_tokens, bool)
                or not isinstance(max_output_tokens, int)
                or max_output_tokens < 1
            ):
                raise ValueError(
                    "max_output_tokens must be positive."
                )

            request["max_tokens"] = max_output_tokens

        try:
            response = (
                self.client.chat.completions.create(
                    **request
                )
            )
        except OpenAIError as error:
            raise RuntimeError(
                "DeepSeek API request failed. "
                f"Details: {error}"
            ) from error

        if response.usage is not None:
            prompt = (
                response.usage.prompt_tokens or 0
            )
            completion = (
                response.usage.completion_tokens or 0
            )

            self.usage.input_tokens += prompt
            self.usage.output_tokens += completion
            self.usage.total_tokens += (
                response.usage.total_tokens
                or prompt + completion
            )

        return response

    def get_usage(self):
        return {
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "total_tokens": self.usage.total_tokens,
        }
