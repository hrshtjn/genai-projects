import os
from traceloop.sdk import Traceloop
from dotenv import load_dotenv

# Ensure .env is loaded before checking env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Disable local trace logging and force delta metrics
os.environ['TRACELOOP_TELEMETRY'] = "false"
os.environ['OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE'] = "delta"

# Dynatrace OTLP HTTP/protobuf endpoints require explicit protocol.
os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "http/protobuf")
os.environ.setdefault("OTEL_EXPORTER_OTLP_METRICS_PROTOCOL", "http/protobuf")

tenant = os.environ.get("DYNATRACE_TENANT", "")
token = os.environ.get("DYNATRACE_API_TOKEN", "")

otlp_base = f"https://{tenant}.live.dynatrace.com/api/v2/otlp"

# FORCE the specific trace and metric endpoints, bypassing Traceloop's auto-append
os.environ['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'] = f"{otlp_base}/v1/traces"
os.environ['OTEL_EXPORTER_OTLP_METRICS_ENDPOINT'] = f"{otlp_base}/v1/metrics"
os.environ['OTEL_EXPORTER_OTLP_HEADERS'] = f"Authorization=Api-Token {token}"

# Traceloop uses its own exporter defaults; point it at Dynatrace with custom headers.
os.environ["TRACELOOP_BASE_URL"] = otlp_base
os.environ["TRACELOOP_METRICS_ENDPOINT"] = otlp_base
os.environ["TRACELOOP_HEADERS"] = f"Authorization=Api-Token {token}"

if token and tenant:
    # Now we rely on the environment variables for routing, skip overriding in init
    Traceloop.init(
        app_name="dynatrace-adk-agent",
        disable_batch=True
    )
    print(
        f"Dynatrace OpenLLMetry enabled for tenant {tenant} via Traceloop OTLP exporter."
    )

    # Optional one-shot test span for Dynatrace validation.
    if os.environ.get("DYNATRACE_TEST_SPAN", "").lower() in {"1", "true", "yes"}:
        try:
            from opentelemetry import trace

            tracer = trace.get_tracer("dynatrace-test")
            with tracer.start_as_current_span("dynatrace.test.startup") as span:
                span.set_attribute("app.name", "dynatrace-adk-agent")
                span.add_event("startup")
            print("Dynatrace test span emitted.")
        except Exception as exc:
            print(f"Dynatrace test span failed: {exc}")
else:
    print("Dynatrace telemetry skipped: DYNATRACE_API_TOKEN or DYNATRACE_TENANT not set.")