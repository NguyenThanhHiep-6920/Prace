# import os
# from prometheus_client import make_asgi_app, Summary, Counter, Histogram, CollectorRegistry, multiprocess

# def get_registry():
#     if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
#         registry = CollectorRegistry()
#         multiprocess.MultiProcessCollector(registry)
#         return registry
#     else:
#         return CollectorRegistry()

# Sử dụng registry multiprocess nếu có
#prometheusClient = make_asgi_app(registry=get_registry())
from prometheus_client import make_asgi_app, Summary

def collectTime(metricprefix):
    s = Summary(f'{metricprefix}_processing_seconds', f'{metricprefix}_time_spent')

    def decorator(f):
        @s.time()
        def decorated(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated
    return decorator

prometheusClient = make_asgi_app
# def collectTime(metricprefix):
#     s = Summary(f'{metricprefix}_processing_seconds', f'{metricprefix}_time_spent')
#     def decorator(f):
#         async def decorated(*args, **kwargs):
#             with s.time():
#                 return await f(*args, **kwargs)
#         return decorated
#     return decorator

# def graphql_query_counter(metricprefix):
#     c = Counter(f'{metricprefix}_query_total', f'Total GraphQL queries on {metricprefix}')
#     def decorator(f):
#         async def decorated(*args, **kwargs):
#             c.inc()
#             return await f(*args, **kwargs)
#         return decorated
#     return decorator

# def graphql_query_duration(metricprefix):
#     h = Histogram(
#         f'{metricprefix}_query_duration_seconds',
#         f'Duration of GraphQL query on {metricprefix}',
#         buckets=(0.1, 0.5, 1, 2, 5, 10, float('inf'))
#     )
#     def decorator(f):
#         async def decorated(*args, **kwargs):
#             with h.time():
#                 return await f(*args, **kwargs)
#         return decorated
#     return decorator

