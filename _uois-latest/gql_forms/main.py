import os
import strawberry
import socket
import asyncio

from pydantic import BaseModel
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter
from strawberry.asgi import GraphQL

import logging
import logging.handlers

from src.GraphTypeDefinitions import schema
from src.DBDefinitions import startEngine, ComposeConnectionString
from src.utils.DBFeeder import initDB
from uoishelpers.authenticationMiddleware import createAuthentizationSentinel

# region logging setup

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s.%(msecs)03d\t%(levelname)s:\t%(message)s', 
    datefmt='%Y-%m-%dT%I:%M:%S')
SYSLOGHOST = os.getenv("SYSLOGHOST", None)
if SYSLOGHOST is not None:
    [address, strport, *_] = SYSLOGHOST.split(':')
    assert len(_) == 0, f"SYSLOGHOST {SYSLOGHOST} has unexpected structure, try `localhost:514` or similar (514 is UDP port)"
    port = int(strport)
    my_logger = logging.getLogger()
    my_logger.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address=(address, port), socktype=socket.SOCK_DGRAM)
    #handler = logging.handlers.SocketHandler('10.10.11.11', 611)
    my_logger.addHandler(handler)


# endregion

# region DB setup

## Definice GraphQL typu (pomoci strawberry https://strawberry.rocks/)
## Strawberry zvoleno kvuli moznosti mit federovane GraphQL API (https://strawberry.rocks/docs/guides/federation, https://www.apollographql.com/docs/federation/)
## Definice DB typu (pomoci SQLAlchemy https://www.sqlalchemy.org/)
## SQLAlchemy zvoleno kvuli moznost komunikovat s DB asynchronne
## https://docs.sqlalchemy.org/en/14/core/future.html?highlight=select#sqlalchemy.future.select


## Zabezpecuje prvotni inicializaci DB a definovani Nahodne struktury pro "Univerzity"
# from gql_workflow.DBFeeder import createSystemDataStructureRoleTypes, createSystemDataStructureGroupTypes

connectionString = ComposeConnectionString()

def singleCall(asyncFunc):
    """Dekorator, ktery dovoli, aby dekorovana funkce byla volana (vycislena) jen jednou. Navratova hodnota je zapamatovana a pri dalsich volanich vracena.
    Dekorovana funkce je asynchronni.
    """
    resultCache = {}

    async def result():
        if resultCache.get("result", None) is None:
            resultCache["result"] = await asyncFunc()
        return resultCache["result"]

    return result

@singleCall
async def RunOnceAndReturnSessionMaker():
    """Provadi inicializaci asynchronniho db engine, inicializaci databaze a vraci asynchronni SessionMaker.
    Protoze je dekorovana, volani teto funkce se provede jen jednou a vystup se zapamatuje a vraci se pri dalsich volanich.
    """

    makeDrop = os.getenv("DEMODATA", None) == "True"
    # makeDrop = False
    logging.info(f'starting engine for "{connectionString} makeDrop={makeDrop}"')

    result = await startEngine(
        connectionstring=connectionString, makeDrop=makeDrop, makeUp=True
    )

    logging.info(f"initializing system structures")

    ###########################################################################################################################
    #
    # zde definujte do funkce asyncio.gather
    # vlozte asynchronni funkce, ktere maji data uvest do prvotniho konzistentniho stavu
    
    # await initDB(result)
    asyncio.create_task(initDB(result))
    #
    #
    ###########################################################################################################################
    logging.info(f"all done")
    return result

# endregion

# region Sentinel setup
JWTPUBLICKEYURL = os.environ.get("JWTPUBLICKEYURL", "http://localhost:8000/oauth/publickey")
JWTRESOLVEUSERPATHURL = os.environ.get("JWTRESOLVEUSERPATHURL", "http://localhost:8000/oauth/userinfo")

apolloQuery = "query __ApolloGetServiceDefinition__ { _service { sdl } }"
graphiQLQuery = "\n    query IntrospectionQuery {\n      __schema {\n        \n        queryType { name }\n        mutationType { name }\n        subscriptionType { name }\n        types {\n          ...FullType\n        }\n        directives {\n          name\n          description\n          \n          locations\n          args(includeDeprecated: true) {\n            ...InputValue\n          }\n        }\n      }\n    }\n\n    fragment FullType on __Type {\n      kind\n      name\n      description\n      \n      fields(includeDeprecated: true) {\n        name\n        description\n        args(includeDeprecated: true) {\n          ...InputValue\n        }\n        type {\n          ...TypeRef\n        }\n        isDeprecated\n        deprecationReason\n      }\n      inputFields(includeDeprecated: true) {\n        ...InputValue\n      }\n      interfaces {\n        ...TypeRef\n      }\n      enumValues(includeDeprecated: true) {\n        name\n        description\n        isDeprecated\n        deprecationReason\n      }\n      possibleTypes {\n        ...TypeRef\n      }\n    }\n\n    fragment InputValue on __InputValue {\n      name\n      description\n      type { ...TypeRef }\n      defaultValue\n      isDeprecated\n      deprecationReason\n    }\n\n    fragment TypeRef on __Type {\n      kind\n      name\n      ofType {\n        kind\n        name\n        ofType {\n          kind\n          name\n          ofType {\n            kind\n            name\n            ofType {\n              kind\n              name\n              ofType {\n                kind\n                name\n                ofType {\n                  kind\n                  name\n                  ofType {\n                    kind\n                    name\n                  }\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n  "


sentinel = createAuthentizationSentinel(
    JWTPUBLICKEY=JWTPUBLICKEYURL,
    JWTRESOLVEUSERPATH=JWTRESOLVEUSERPATHURL,
    queriesWOAuthentization=[apolloQuery, graphiQLQuery],
    onAuthenticationError=lambda item: JSONResponse({"data": None, "errors": ["Unauthenticated", item.query, f"{item.variables}"]}, 
    status_code=401))

# endregion

# region FastAPI setup
class Item(BaseModel):
    query: str
    variables: dict = {}
    operationName: str = None

async def get_context(request: Request):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
        
    #from src.Dataloaders import createLoadersContext, createUgConnectionContext
    from src.utils.Dataloaders import createLoadersContext
    context = createLoadersContext(asyncSessionMaker)
    i = Item(query = "")
    # i.query = ""
    # i.variables = {}
    logging.info(f"before sentinel current user is {request.scope.get('user', None)}")
    await sentinel(request, i)
    logging.info(f"after sentinel current user is {request.scope.get('user', None)}")
    # connectionContext = createUgConnectionContext(request=request)
    # result = {**context, **connectionContext}
    result = {**context}
    result["request"] = request
    result["user"] = request.scope.get("user", None)
    logging.info(f"context created {result}")
    return result


from metrics.qos_monitor import  update_qos_metrics_task, qos_monitor
#from server.prometheus import qos_monitoring_middleware
from metrics.prometheus_metrics import (
    GQL_QUERY_COUNT, GQL_QUERY_LATENCY, GQL_ERRORS, SERVICE_NAME
,) 
from fastapi import Request, Response
import time
import json

# app = FastAPI(root_path="/apif")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Other tasks
    initizalizedEngine = await RunOnceAndReturnSessionMaker()
    asyncio.create_task(update_qos_metrics_task())
    yield

app = FastAPI(lifespan=lifespan)

# from metrics.logging_config import setup_logging
# from metrics.logging_middleware import GraphQLLoggingMiddleware
# logger = setup_logging(SERVICE_NAME)  # log vào /logs/gql_forms.log
# app.add_middleware(GraphQLLoggingMiddleware, service_name=SERVICE_NAME)



# @app.middleware("http")
# async def graphql_middleware(request: Request, call_next):
#     graphql_paths = ["/gql", "/graphql", "/api/gql"]
#     if any(request.url.path.endswith(path) for path in graphql_paths) and request.method == "POST":
#         try:
#             body_bytes = await request.body()
#             body = json.loads(body_bytes.decode("utf-8"))
#             operation_name = body.get("operationName") or "anonymous"
#         except Exception:
#             operation_name = "unknown"
#             body_bytes = b""

#         start_time = time.time()
#         is_error = False
#         try:
#             # Recreate request stream since body was read
#             async def receive():
#                 return {"type": "http.request", "body": body_bytes}
#             request = Request(request.scope, receive=receive)

#             response = await call_next(request)

#             # Capture response content to check for GraphQL errors
#             body_content = b""
#             async for chunk in response.body_iterator:
#                 body_content += chunk

#             # Check for "errors" in GraphQL response
#             try:
#                 response_json = json.loads(body_content.decode("utf-8"))
#                 if isinstance(response_json, dict) and "errors" in response_json:
#                     is_error = True
#             except Exception:
#                 pass  # skip if body not valid JSON

#             if response.status_code >= 400:
#                 is_error = True

#             # Re-wrap response
#             response = Response(
#                 content=body_content,
#                 status_code=response.status_code,
#                 headers=dict(response.headers),
#                 media_type=response.media_type
#             )

#             if is_error:
#                 GQL_ERRORS.labels(service=SERVICE_NAME, operation=operation_name).inc()

#         except Exception:
#             is_error = True
#             GQL_ERRORS.labels(service=SERVICE_NAME, operation=operation_name).inc()
#             raise
#         finally:
#             response_time = time.time() - start_time
#             GQL_QUERY_COUNT.labels(service=SERVICE_NAME, operation=operation_name).inc()
#             GQL_QUERY_LATENCY.labels(service=SERVICE_NAME, operation=operation_name).observe(response_time)
#             qos_monitor.record_request(response_time=response_time, is_error=is_error)

#         return response
#     # Non-GraphQL requests go through normally
#     return await call_next(request)

# @app.middleware("http")
# async def graqphql_middleware(request: Request, call_next):
#     graphql_paths = ["/gql"]
#     is_graphql = (
#         request.method == "POST" and 
#         any(request.url.path.startswith(p) for p in graphql_paths) and
#         request.headers.get("content-type", "").startswith("application/json")
#     )
#     if not is_graphql:
#         return await call_next(request)
    
#     # # Default fallback
#     # operation_name = "unknown"
#     # # Step 1: Read body and extract operationName
#     # try:
#     #     # Read and parse body
#     #     body_bytes = await request.body()
#     #     body = json.loads(body_bytes.decode("utf-8"))
#     #     operation_name = body.get("operationName") or "anonymous"
#     #     # if isinstance(body, dict):
#     #     #     operation_name = body.get("operationName") or "anonymous"
#     #     # elif isinstance(body, list):  # Batch queries
#     #     #     operation_name = ",".join(
#     #     #         (entry.get("operationName") or "anonymous")
#     #     #         if isinstance(entry, dict) else "invalid_entry"
#     #     #         for entry in body
#     #     #     )
#     #     # else:
#     #     #     operation_name = "malformed"
#     # except Exception:
#     #     body_bytes = b""
#     #     operation_name = "invalid_json"
#     #     # Let request continue normally, still record timing below

#     # # Step 2: Recreate request stream
#     # async def receive():
#     #     return {"type": "http.request", "body": body_bytes}
#     # request = Request(request.scope, receive=receive)
#     # # Step 3: Time and execute the request

#     start_time = time.time()
#     is_error = False
#     try:
#         response = await call_next(request)

#         # Step 4: Inspect response body for GraphQL errors
#         body_content = b""
#         async for chunk in response.body_iterator:
#             body_content += chunk

#         try:
#             json_response = json.loads(body_content.decode("utf-8"))
#             if isinstance(json_response, dict) and "errors" in json_response:
#                 is_error = True
#         except Exception:
#             pass  # not a JSON response, skip error check

#         # Step 5: Rewrap response body
#         response = Response(
#             content=body_content,
#             status_code=response.status_code,
#             headers=dict(response.headers),
#             media_type=response.media_type
#         )

#         if response.status_code >= 400:
#             is_error = True

#     except Exception:
#         is_error = True
#         raise
#     finally:
#         duration = time.time() - start_time
#         GQL_QUERY_COUNT.labels(service=SERVICE_NAME).inc()
#         GQL_QUERY_LATENCY.labels(service=SERVICE_NAME).observe(duration)
#         if is_error:
#             GQL_ERRORS.labels(service=SERVICE_NAME).inc()
#             #GQL_ERRORS.labels(service=SERVICE_NAME, operation=operation_name).inc()
#         qos_monitor.record_request(response_time=duration, is_error=is_error)

#     return response
def gql_query_requests_total() -> Callable[[Info], None]:
    METRIC = Counter(
        "gql_query_requests_total", 
        "Total number of gql query requests",
        ["handler","method"]
    )
    def instrumentation(info: Info) -> None:
        if info.modified_handler == "/gql" and info.method=="POST":
            METRIC.labels(handler="/gql",method="POST").inc()
    return instrumentation
Instrumentator().add(gql_query_requests_total())

# Middleware đo QoS cho tất cả các app
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app, metric_namespace="gql_forms").expose(app, endpoint="/metrics")

from prometheus_fastapi_instrumentator import Instrumentator,metrics
from prometheus_fastapi_instrumentator.metrics import Info
from typing import Callable
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, make_asgi_app

#create instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="inprogress",
    inprogress_labels=True,
)
instrumentator= Instrumentator()

def gql_query_requests_total() -> Callable[[Info], None]:
    METRIC = Counter(
        "gql_query_requests_total", 
        "Total number of  HTTP gql query requests by method and handler",
        ["handler","method"]
    )
    def instrumentation(info: Info) -> None:
        if info.modified_handler =="/gql" and info.method=="POST":
            METRIC.labels(handler="/gql",method="POST").inc()
    return instrumentation

def gql_query_errors_total() -> Callable[[Info], None]:
    METRIC = Counter(
        "gql_query_errors_total", 
        "Total number of  HTTP gql query errors by method and handler",
        ["handler","method","status"]
    )
    def instrumentation(info: Info) -> None:
        if info.modified_handler =="/gql" and info.method=="POST" and info.modified_status=="4xx":
            METRIC.labels(handler="/gql",method="POST", status="4xx").inc()
        if info.modified_handler =="/gql" and info.method=="POST" and info.modified_status=="5xx":
            METRIC.labels(handler="/gql",method="POST", status="5xx").inc()
    return instrumentation

instrumentator.add(gql_query_requests_total())
instrumentator.add(gql_query_errors_total())
instrumentator.instrument(app, metric_namespace="gql_forms")
instrumentator.expose(app, endpoint="/metrics")

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)

@app.get("/gql")
async def graphiql(request: Request):
    return await graphql_app.render_graphql_ide(request)

from metrics.decorators import monitor_apollo_gql


@app.post("/gql")
@monitor_apollo_gql
async def apollo_gql(request: Request, item: Item):
    DEMOE = os.getenv("DEMO", None)

    sentinelResult = await sentinel(request, item)
    if DEMOE in ["False", "false"]:
        if sentinelResult:
            logging.info(f"sentinel test failed for query={item} \n request={request}")
            return sentinelResult
        logging.info(f"sentinel test passed for query={item}")
    else:
        request.scope["user"] = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
        logging.info(f"sentinel skippend because of DEMO mode for query={item} for user {request.scope['user']}")
    try:
        context = await get_context(request)
        schemaresult = await schema.execute(query=item.query, variable_values=item.variables, operation_name=item.operationName, context_value=context)
    except Exception as e:
        logging.info(f"error during schema execute {e}")
        return {"data": None, "errors": [f"{type(e).__name__}: {e}"]}
    
    # logging.info(f"schema execute result \n{schemaresult}")
    result = {"data": schemaresult.data}
    if schemaresult.errors:
        result["errors"] = [
            {
                "msg": error.message,
                "locations": error.locations,
                "path": error.path,
                "nodes": error.nodes,
                "source": error.source,
                "original_error": { "type": f"{type(error.original_error)}", "msg": f"{error.original_error}" },
                # "msg_r": f"{error}",
                "msg_e": f"{error}".split('\n')
            } for error in schemaresult.errors]
    return result

logging.info("All initialization is done")

# @app.get('/hello')
# def hello():
#    return {'hello': 'world'}

###########################################################################################################################
#
# pokud jste pripraveni testovat GQL funkcionalitu, rozsirte apollo/server.js
#
###########################################################################################################################
# endregion

# region ENV setup tests
def envAssertDefined(name, default=None):
    result = os.getenv(name, None)
    assert result is not None, f"{name} environment variable must be explicitly defined"
    return result

DEMO = envAssertDefined("DEMO", None)
GQLUG_ENDPOINT_URL = envAssertDefined("GQLUG_ENDPOINT_URL", None)
JWTPUBLICKEYURL = envAssertDefined("JWTPUBLICKEYURL", None)
JWTRESOLVEUSERPATHURL = envAssertDefined("JWTRESOLVEUSERPATHURL", None)

assert (DEMO in ["True", "true", "False", "false"]), "DEMO environment variable can have only `True` or `False` values"
DEMO = DEMO in ["True", "true"]


if DEMO:
    print("####################################################")
    print("#                                                  #")
    print("# RUNNING IN DEMO                                  #")
    print("#                                                  #")
    print("####################################################")

    logging.info("####################################################")
    logging.info("#                                                  #")
    logging.info("# RUNNING IN DEMO                                  #")
    logging.info("#                                                  #")
    logging.info("####################################################")
else:
    print("####################################################")
    print("#                                                  #")
    print("# RUNNING DEPLOYMENT                               #")
    print("#                                                  #")
    print("####################################################")

    logging.info("####################################################")
    logging.info("#                                                  #")
    logging.info("# RUNNING DEPLOYMENT                               #")
    logging.info("#                                                  #")
    logging.info("####################################################")    

logging.info(f"DEMO = {DEMO}")
logging.info(f"SYSLOGHOST = {SYSLOGHOST}")
logging.info(f"GQLUG_ENDPOINT_URL = {GQLUG_ENDPOINT_URL}")
logging.info(f"JWTPUBLICKEYURL = {JWTPUBLICKEYURL}")
logging.info(f"JWTRESOLVEUSERPATHURL = {JWTRESOLVEUSERPATHURL}")
# endregion