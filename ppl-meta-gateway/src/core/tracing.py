"""
OpenTelemetry distributed tracing implementation for PPL Meta Gateway
"""

import os
from typing import Optional

import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger()


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(self, settings=None):
        if settings:
            self.service_name = settings.tracing_service_name
            self.service_version = settings.service_version
            self.environment = settings.environment
            self.jaeger_endpoint = settings.jaeger_endpoint
            self.jaeger_agent_host = settings.jaeger_agent_host
            self.jaeger_agent_port = settings.jaeger_agent_port
            self.sampling_rate = settings.tracing_sampling_rate
            self.enabled = settings.tracing_enabled
            self.excluded_urls = settings.tracing_excluded_urls
        else:
            # Fallback to environment variables
            self.service_name = os.getenv("SERVICE_NAME", "ppl-meta-gateway")
            self.service_version = os.getenv("SERVICE_VERSION", "1.4.0")
            self.environment = os.getenv("ENVIRONMENT", "development")
            self.jaeger_endpoint = os.getenv(
                "JAEGER_ENDPOINT", "http://localhost:14268/api/traces"
            )
            self.jaeger_agent_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
            self.jaeger_agent_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
            self.sampling_rate = float(os.getenv("TRACING_SAMPLING_RATE", "1.0"))
            self.enabled = os.getenv("TRACING_ENABLED", "true").lower() == "true"
            self.excluded_urls = os.getenv(
                "TRACING_EXCLUDED_URLS", "health,metrics,docs,redoc"
            )


class DistributedTracing:
    """Manages OpenTelemetry distributed tracing setup."""

    def __init__(self, config: Optional[TracingConfig] = None):
        self.config = config or TracingConfig()
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None

    def initialize(self) -> bool:
        """Initialize distributed tracing with OpenTelemetry."""
        if not self.config.enabled:
            logger.info("Distributed tracing is disabled")
            return False

        try:
            # Create resource with service information
            resource = Resource.create(
                {
                    "service.name": self.config.service_name,
                    "service.version": self.config.service_version,
                    "deployment.environment": self.config.environment,
                    "telemetry.sdk.name": "opentelemetry",
                    "telemetry.sdk.language": "python",
                }
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)

            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_agent_host,
                agent_port=self.config.jaeger_agent_port,
                collector_endpoint=self.config.jaeger_endpoint,
            )

            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(span_processor)

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer instance
            self.tracer = trace.get_tracer(
                instrumenting_module_name=self.config.service_name,
                instrumenting_library_version=self.config.service_version,
            )

            logger.info(
                "Distributed tracing initialized",
                service_name=self.config.service_name,
                jaeger_endpoint=self.config.jaeger_endpoint,
                sampling_rate=self.config.sampling_rate,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to initialize distributed tracing: {e}")
            return False

    def instrument_fastapi(self, app):
        """Instrument FastAPI application for automatic tracing."""
        if not self.config.enabled or not self.tracer_provider:
            return

        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                excluded_urls=self.config.excluded_urls,
            )
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")

    def instrument_httpx(self):
        """Instrument HTTPX client for automatic tracing of outbound requests."""
        if not self.config.enabled or not self.tracer_provider:
            return

        try:
            HTTPXClientInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("HTTPX client instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument HTTPX: {e}")

    def create_span(self, name: str, **attributes):
        """Create a new span with the given name and attributes."""
        if not self.tracer:
            return trace.NoOpSpan()

        span = self.tracer.start_span(name)
        for key, value in attributes.items():
            span.set_attribute(key, value)
        return span

    def get_current_span(self):
        """Get the current active span."""
        return trace.get_current_span()

    def add_span_attribute(self, key: str, value):
        """Add attribute to current span."""
        span = self.get_current_span()
        if span and span.is_recording():
            span.set_attribute(key, value)

    def add_span_event(self, name: str, **attributes):
        """Add event to current span."""
        span = self.get_current_span()
        if span and span.is_recording():
            span.add_event(name, attributes)

    def set_span_status(self, status_code, description: Optional[str] = None):
        """Set status of current span."""
        span = self.get_current_span()
        if span and span.is_recording():
            span.set_status(status_code, description)

    def shutdown(self):
        """Shutdown tracing and flush remaining spans."""
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("Distributed tracing shutdown completed")
            except Exception as e:
                logger.error(f"Error during tracing shutdown: {e}")


# Global tracing instance
tracing = DistributedTracing()


def setup_tracing(app, settings=None) -> bool:
    """Setup distributed tracing for the application."""
    global tracing
    tracing = DistributedTracing(TracingConfig(settings))
    success = tracing.initialize()
    if success:
        tracing.instrument_fastapi(app)
        tracing.instrument_httpx()
    return success


def get_tracer():
    """Get the global tracer instance."""
    return tracing.tracer


def create_span(name: str, **attributes):
    """Create a new span with the given name and attributes."""
    return tracing.create_span(name, **attributes)


def get_current_span():
    """Get the current active span."""
    return tracing.get_current_span()


def add_span_attribute(key: str, value):
    """Add attribute to current span."""
    tracing.add_span_attribute(key, value)


def add_span_event(name: str, **attributes):
    """Add event to current span."""
    tracing.add_span_event(name, **attributes)


def shutdown_tracing():
    """Shutdown tracing and flush remaining spans."""
    tracing.shutdown()
