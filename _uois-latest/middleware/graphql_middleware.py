import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from metrics.prometheus_metrics import (
    GQL_ERRORS, GQL_QUERY_COUNT, GQL_QUERY_LATENCY,  SERVICE_NAME
)
from metrics.qos_monitor import qos_monitor

class GraphQLMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        graphql_paths = ["/gql", "/graphql", "/api/gql"]
        if any(request.url.path.startswith(path) for path in graphql_paths):
            body = await request.json()
            operation_name = body.get("operationName") or "anonymous"
            start_time = time.time()
            try:
                response = await call_next(request)
                
                is_error = response.status_code >= 400
                if is_error:
                    GQL_ERRORS.labels(service=SERVICE_NAME, operation=operation_name).inc()
                # else:
                # # Nếu là 200 nhưng có field "errors" trong body -> vẫn là lỗi GraphQL
                #     if "application/json" in response.headers.get("content-type", ""):
                #         raw_body = await response.body()
                #         try:
                #             resp_json = json.loads(raw_body)
                #             if "errors" in resp_json:
                #                 is_error = True
                #                 GQL_ERRORS.labels(service=SERVICE_NAME,operation=operation_name).inc()
                #         except Exception:
                #             pass  # nếu parse lỗi thì bỏ qua
            except Exception:
                is_error = True
                GQL_ERRORS.labels(service=SERVICE_NAME,operation=operation_name).inc()
                raise
            finally:
                response_time = (time.time() - start_time)
                GQL_QUERY_COUNT.labels(service=SERVICE_NAME,operation=operation_name).inc()
                GQL_QUERY_LATENCY.labels(service=SERVICE_NAME,operation=operation_name).observe(response_time)
                qos_monitor.record_request(response_time=response_time, is_error=is_error)
            return response
        else:
            return await call_next(request)
