from prometheus_client import Counter, Histogram, Gauge, Summary,REGISTRY
import os


SERVICE_NAME = os.getenv("SERVICE_NAME", "gql_forms")
# def prefix(name):
#     return f"{SERVICE_METRICS_PREFIX}{name}"

GQL_ERRORS = Counter(
    'graphql_errors_total',
    'Total GraphQL query errors',
    #['service', 'operation']
    ['service','error_type']
)

GQL_FIELDS_ACCESSED= Counter(
    'graphql_fields_accessed_total',
    'Number of access by field',
    ['service,field']
)
GQL_RESOLVER_ERRORS = Counter('graphql_resolver_errors_total','Total resolver errors',['service', 'field_name'])
GQL_RESOLVER_COUNT= Counter('graphql_resolvers_total','Total resolver accessed',['service', 'field_name'])
GQL_RESOLVER_LATENCY = Histogram('graphql_resolver_duration_seconds','Duration of resolver',['service', 'field_name'],buckets=(0.1, 0.5, 1, 2, 5, 10, float('inf')))

GQL_QUERY_COUNT = Counter(
    'graphql_query_total',
    'Total GraphQL queries forwarded',
    #['service', 'operation']
    ['service']
)

GQL_QUERY_LATENCY = Histogram(
    'graphql_query_duration_seconds',
    'Duration of GraphQL queries',
    #['service', 'operation'],
    ['service'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, float('inf'))
)

# Các metrics cho QoS (Quality of GraphQL Service)
QOS_AVAILABILITY = Gauge("service_availability_percent", "Service Availability Percentage",['service'])
QOS_AVG_RESPONSE_TIME = Gauge("service_average_response_time_seconds", "Average Response Time",['service'])
QOS_P95_RESPONSE_TIME = Gauge("service_p95_response_time_seconds", "95th Percentile Response Time",['service'])
QOS_P99_RESPONSE_TIME = Gauge("service_p99_response_time_seconds", "99th Percentile Response Time",['service'])
QOS_ERROR_RATE = Gauge("service_error_rate", "Service Error Rate",['service'])
QOS_REQUEST_RATE = Gauge("service_request_rate", "Requests per Second",['service'])