from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger

from app.config.loader import ConfigLoader
from app.models.errors import AllProvidersFailedError
from app.models.request import ChatRequest
from app.models.response import ChatResponse
from app.monitoring.metrics import provider_requests

# ── Model Mapping ─────────────────────────────────────────────────────────────
# Aliasing virtual models to provider-native models
MODEL_MAPPING = {
    "gpt-4": {
        "groq": "mixtral-8x7b-32768",
        "gemini": "gemini-1.5-flash",
    },
    "gpt-3.5-turbo": {
        "groq": "llama-3.1-8b-instant",
        "gemini": "gemini-1.5-flash-8b",
    },
}


class Router:
    def __init__(
        self,
        providers: dict[str, Any],
        circuit_breakers: dict[str, Any],
        config_loader: ConfigLoader,
    ) -> None:
        self.providers = providers
        self.circuit_breakers = circuit_breakers
        self.config_loader = config_loader

    async def route(self, request: ChatRequest, request_id: str) -> ChatResponse:
        """
        Routes the ChatRequest through the fallback chain of providers.

        Checks each provider's circuit breaker first, maps the requested model,
        and executes the request. Automatically falls back to the next provider
        if a provider call fails.
        """
        chain = self.config_loader.get_chain()
        providers_tried = []
        fallback_triggered = False

        for idx, provider_name in enumerate(chain):
            provider = self.providers.get(provider_name)
            cb = self.circuit_breakers.get(provider_name)

            if not provider or not cb:
                logger.warning("router_invalid_provider_in_chain", provider=provider_name)
                continue

            # 1. Check Circuit Breaker
            if await cb.is_open():
                logger.warning("router_provider_skipped_cb_open", provider=provider_name)
                provider_requests.labels(provider=provider_name, outcome="skipped").inc()
                continue

            # Add to list of providers we attempted to contact
            providers_tried.append(provider_name)
            fallback_triggered = idx > 0

            # 2. Map Requested Model to Provider-Supported Equivalent
            mapped_model = self._map_model(request.model, provider_name, provider)
            adapted_request = request.model_copy(update={"model": mapped_model})

            # 3. Attempt Execution
            try:
                logger.info(
                    "router_attempting_provider",
                    provider=provider_name,
                    model=mapped_model,
                    request_id=request_id,
                )
                response = await provider.complete(adapted_request)

                # Record Success on the CB
                await cb.record_success()

                # Attach Gateway metadata to Response
                response.x_gateway.request_id = request_id
                response.x_gateway.fallback_triggered = fallback_triggered
                response.x_gateway.providers_tried = providers_tried

                provider_requests.labels(provider=provider_name, outcome="success").inc()
                return response

            except Exception as e:
                logger.warning(
                    "router_provider_failed",
                    provider=provider_name,
                    error=str(e),
                    request_id=request_id,
                )
                # Record Failure on the CB
                await cb.record_failure()
                provider_requests.labels(provider=provider_name, outcome="failure").inc()

                # Continue fallback loop
                continue

        # If all configured/tried providers failed
        raise AllProvidersFailedError(
            message="All providers failed in the routing chain.",
            providers_tried=providers_tried,
        )

    async def route_stream(
        self, request: ChatRequest, request_id: str
    ) -> tuple[AsyncGenerator[str, None], dict[str, Any]]:
        """
        Routes the ChatRequest through the fallback chain for streaming responses.

        Checks circuit breaker, maps model, initializes stream from provider.
        If initial connection fails, records CB failure and tries next provider.
        """
        chain = self.config_loader.get_chain()
        providers_tried = []
        fallback_triggered = False

        for idx, provider_name in enumerate(chain):
            provider = self.providers.get(provider_name)
            cb = self.circuit_breakers.get(provider_name)

            if not provider or not cb:
                logger.warning("router_invalid_provider_in_chain", provider=provider_name)
                continue

            if await cb.is_open():
                logger.warning("router_provider_skipped_cb_open", provider=provider_name)
                provider_requests.labels(provider=provider_name, outcome="skipped").inc()
                continue

            providers_tried.append(provider_name)
            fallback_triggered = idx > 0
            mapped_model = self._map_model(request.model, provider_name, provider)
            adapted_request = request.model_copy(update={"model": mapped_model})

            try:
                logger.info(
                    "router_attempting_provider_stream",
                    provider=provider_name,
                    model=mapped_model,
                    request_id=request_id,
                )
                stream_gen = await provider.complete_stream(adapted_request)

                await cb.record_success()
                provider_requests.labels(provider=provider_name, outcome="success").inc()

                meta = {
                    "provider_used": provider_name,
                    "model_used": mapped_model,
                    "request_id": request_id,
                    "fallback_triggered": fallback_triggered,
                    "providers_tried": providers_tried,
                }
                return stream_gen, meta

            except Exception as e:
                logger.warning(
                    "router_provider_stream_failed",
                    provider=provider_name,
                    error=str(e),
                    request_id=request_id,
                )
                await cb.record_failure()
                provider_requests.labels(provider=provider_name, outcome="failure").inc()
                continue

        raise AllProvidersFailedError(
            message="All providers failed in the routing chain.",
            providers_tried=providers_tried,
        )

    def _map_model(self, requested_model: str, provider_name: str, provider: Any) -> str:
        """
        Maps a requested model string to a model supported by the provider.
        """
        # If the provider natively supports the requested model, use it as-is
        if provider.supports_model(requested_model):
            return requested_model

        # Check virtual model mappings
        if requested_model in MODEL_MAPPING:
            mapped = MODEL_MAPPING[requested_model].get(provider_name)
            if mapped and provider.supports_model(mapped):
                return mapped

        # Fall back to default model for this provider configured in YAML config
        provider_config = self.config_loader.config.providers.get(provider_name)
        if provider_config:
            return provider_config.default_model

        # Ultimate fallback to the provider's first supported model list
        return provider.models[0]
