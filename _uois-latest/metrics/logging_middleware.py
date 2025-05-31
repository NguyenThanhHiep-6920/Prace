import logging
import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
#from opentelemetry.trace import get_current_span


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.logger = logging.getLogger(service_name)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        # span = get_current_span()
        # trace_id = span.get_span_context().trace_id
        trace_id = request.headers.get('x-trace-id', 'unknown')

        self.logger.info(
            f"{request.client.host} - {request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms",
            extra={"trace_id": trace_id}
        )
        return response


class GraphQLLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str, gql_path: str = "/api/gql"):
        super().__init__(app)
        self.logger = logging.getLogger(service_name)
        self.gql_path = gql_path

    async def dispatch(self, request: Request, call_next):
        if request.url.path == self.gql_path and request.method == "POST":
            try:
                body = await request.body()
                gql_payload = json.loads(body)
                query = gql_payload.get("query", "").replace("\n", " ").strip()
                variables = gql_payload.get("variables", {})
            except Exception:
                query = "Invalid GraphQL query"
                variables = {}

            start_time = time.time()
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            gql_errors = False
            if isinstance(response, JSONResponse):
                response_body = b"".join([section async for section in response.body_iterator])
                try:
                    parsed = json.loads(response_body.decode())
                    gql_errors = bool(parsed.get("errors"))
                except Exception:
                    gql_errors = False
                response.body_iterator = iter([response_body])

            status = response.status_code
            status_type = "GraphQLError" if gql_errors else "OK"

            self.logger.info(
                f"[{status_type}] Status: {status} Duration: {duration_ms:.2f}ms Query: {query} Variables: {variables}"
            )
            return response
        return await call_next(request)