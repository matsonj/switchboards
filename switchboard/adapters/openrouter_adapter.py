"""OpenRouter adapter for AI model calls."""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import yaml
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OpenRouterAdapter:
    """Adapter for calling AI models through OpenRouter."""

    def __init__(self, model_mappings_file: Optional[str] = None):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/matsonj/eval-connections",
                "X-Title": "Switchboard Game Simulator"
            }
        )

        # Load model mappings from YAML file
        self.model_mappings = self._load_model_mappings(model_mappings_file)

    def _load_model_mappings(
        self, mappings_file: Optional[str] = None
    ) -> Dict[str, str]:
        """Load model mappings from YAML configuration file."""
        if mappings_file is None:
            # Default to inputs/model_mappings.yml
            file_path = Path("inputs/model_mappings.yml")
        else:
            file_path = Path(mappings_file)

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            mappings = data.get("models", {})
            logger.info(f"Loaded {len(mappings)} model mappings from {file_path}")
            return mappings
        except FileNotFoundError:
            logger.warning(f"Model mappings file not found: {file_path}")
            # Fallback to basic mappings
            return {
                "gpt4": "openai/gpt-4",
                "claude": "anthropic/claude-3.5-sonnet",
                "gemini": "google/gemini-2.5-pro",
            }
        except Exception as e:
            logger.error(f"Error loading model mappings: {e}")
            # Fallback to basic mappings
            return {
                "gpt4": "openai/gpt-4",
                "claude": "anthropic/claude-3.5-sonnet",
                "gemini": "google/gemini-2.5-pro",
            }

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def call_model(self, model_name: str, prompt: str) -> str:
        """Call AI model with retry logic."""
        try:
            # Map model name to OpenRouter model ID
            model_id = self.model_mappings.get(model_name, model_name)

            if model_name not in self.model_mappings:
                logger.warning(
                    f"Model '{model_name}' not found in mappings, using as-is: {model_id}"
                )

            logger.debug(
                f"Calling model {model_id} (from {model_name}) with prompt length: {len(prompt)}"
            )

            # Check if this is a reasoning model that doesn't support certain parameters
            is_reasoning_model = self._is_reasoning_model(model_id)

            # Create request parameters based on model type
            is_gemini_reasoning = model_id.startswith('google/gemini-2.5')
            
            if is_reasoning_model:
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                )
            elif is_gemini_reasoning:
                # Gemini reasoning models: no max_tokens limit, temperature 0.0
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
            else:
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.0,
                )

            content = response.choices[0].message.content

            # Log token usage if available
            if hasattr(response, "usage") and response.usage:
                logger.info(
                    f"Model call completed. Tokens: {response.usage.total_tokens}"
                )

            return content or ""

        except Exception as e:
            logger.error(
                f"Error calling model {model_name} (mapped to {model_id}): {e}"
            )
            raise

    def _is_reasoning_model(self, model_id: str) -> bool:
        """Check if model is a reasoning model that doesn't support standard parameters."""
        reasoning_patterns = [
            "o1",
            "o3",
            "o4",
            "gpt-5",
            "grok-4",
            "grok-3-mini",
            "gpt-oss-120b",
            "gpt-oss-20b",
            "qwen3",
        ]
        return any(pattern in model_id for pattern in reasoning_patterns)

    def get_available_models(self) -> list:
        """Get list of available model names."""
        return list(self.model_mappings.keys())
