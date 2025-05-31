import time
from functools import wraps
from .prometheus_metrics import SERVICE_NAME, GQL_RESOLVER_COUNT, GQL_RESOLVER_LATENCY, GQL_RESOLVER_ERRORS
from graphql import parse, OperationDefinitionNode

from .prometheus_metrics import (
    GQL_QUERY_COUNT,
    GQL_QUERY_LATENCY,
    GQL_ERRORS,
    GQL_FIELDS_ACCESSED
)
from .qos_monitor import qos_monitor
def instrument_resolver():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Lấy field name từ info (tham số thứ 1 hoặc 2)
            info = kwargs.get("info", None)
            if not info and len(args) >= 2:
                info = args[1]
            field = getattr(info, "field_name", "unknown")

            GQL_RESOLVER_COUNT.labels(service=SERVICE_NAME, field=field).inc()
            start = time.time()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                GQL_RESOLVER_ERRORS.labels(service=SERVICE_NAME, field=field).inc()
                raise
            finally:
                duration = time.time() - start
                GQL_RESOLVER_LATENCY.labels(service=SERVICE_NAME, field=field).observe(duration)
        return wrapper
    return decorator


def monitor_apollo_gql(func):
    @wraps(func)
    async def wrapper(request, item, *args, **kwargs):
        start_time = time.time()
        is_error=False
        try:
            result = await func(request, item, *args, **kwargs)
            duration = time.time() - start_time

            

            # Kiểm tra lỗi trong kết quả GraphQL
            if isinstance(result, dict) and "errors" in result and result["errors"]:
                #GQL_ERRORS.labels(service=SERVICE_NAME).inc()
                is_error = True
                for error in result["errors"]:
                    msg = error.get("msg", "")
                    error_type = "unknown"
                    if "Cannot query field" in msg:
                        error_type = "validation_error"
                    elif msg.startswith("Syntax Error"):
                        error_type = "syntax_error"
                    elif "original_error" in error:
                        original_type = error["original_error"].get("type", "")
                        if original_type:
                            error_type = original_type
                    GQL_ERRORS.labels(service=SERVICE_NAME, error_type=error_type).inc()                


            # Ghi nhận các field được truy cập
            # if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
            #     for field in result["data"]:
            #         GQL_FIELDS_ACCESSED.labels(service=SERVICE_NAME, field_name=field).inc()
            # if isinstance(result, dict) and "data" in result:
            #     list(collect_fields(result["data"]))

            return result
        except Exception as e:
            duration = time.time() - start_time
            is_error = True
            #GQL_ERRORS.labels(service=SERVICE_NAME).inc()
            GQL_ERRORS.labels(service=SERVICE_NAME, error_type=type(e).__name__).inc()
            raise
        finally:
            # Metrics
            GQL_QUERY_COUNT.labels(service=SERVICE_NAME).inc()
            GQL_QUERY_LATENCY.labels(service=SERVICE_NAME).observe(duration)
            qos_monitor.record_request(response_time=duration, is_error=is_error)
    return wrapper

def extract_fields_from_query(query_str):
    try:
        ast = parse(query_str)
        fields = set()
        for defn in ast.definitions:
            if isinstance(defn, OperationDefinitionNode):
                for selection in defn.selection_set.selections:
                    fields.add(selection.name.value)
        return fields
    except Exception as e:
        print(f"[ERROR] Failed to parse query: {e}")
        return {"unknown"}

def collect_fields(data: dict):
    if isinstance(data, dict):
        for key, value in data.items():
            GQL_FIELDS_ACCESSED.labels(service=SERVICE_NAME, field_name=key).inc()
            yield from collect_fields(value)
    elif isinstance(data, list):
        for item in data:
            yield from collect_fields(item)