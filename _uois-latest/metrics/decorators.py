import time
from functools import wraps
from .prometheus_metrics import SERVICE_NAME, GQL_RESOLVER_COUNT, GQL_RESOLVER_LATENCY, GQL_RESOLVER_ERRORS

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


# def extract_fields_from_query(query_str):
#     try:
#         ast = parse(query_str)
#         fields = set()
#         for defn in ast.definitions:
#             if isinstance(defn, OperationDefinitionNode):
#                 for selection in defn.selection_set.selections:
#                     fields.add(selection.name.value)
#         return fields
#     except Exception as e:
#         print(f"[ERROR] Failed to parse query: {e}")
#         return {"unknown"}
