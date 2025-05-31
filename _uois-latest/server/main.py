import logging
import os
import asyncio
import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from mockoauthserver import server as OAuthServer

#uvicorn server.main:app --env-file environment.txt --port 8000 --reload
from .users import (
    ComposeConnectionString, 
    startEngine, initDB, 
    getDemoData, passwordValidator, emailMapper
)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s.%(msecs)03d\t%(levelname)s:\t%(message)s', 
    datefmt='%Y-%m-%dT%I:%M:%S')


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

    makeDrop = os.getenv("DEMO", None) in ["True", True]
    logging.info(f'starting engine for "{connectionString} makeDrop={makeDrop}"')

    asyncSessionMaker = await startEngine(
        connectionstring=connectionString, makeDrop=makeDrop, makeUp=True
    )

    logging.info(f"initializing system structures")

    asyncio.create_task(initDB(asyncSessionMaker))
    # await initDB(asyncSessionMaker)

    logging.info(f"all done")
    return asyncSessionMaker

# endregion


DEMO = os.getenv("DEMO", None)
assert DEMO is not None, "DEMO environment variable must be explicitly defined"
assert (DEMO == "True") or (DEMO == "False"), "DEMO environment variable can have only `True` or `False` values"
DEMO = DEMO == "True"

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



from middleware.graphql_middleware import GraphQLMiddleware
from metrics.qos_monitor import  update_qos_metrics_task, qos_monitor
#from server.prometheus import qos_monitoring_middleware
from metrics.prometheus_metrics import (
    GQL_QUERY_COUNT, GQL_QUERY_LATENCY, GQL_ERRORS, SERVICE_NAME
,) 
import time



# app = FastAPI(root_path="/apif")
@asynccontextmanager
async def lifespan(app: FastAPI):
    initizalizedEngine = await RunOnceAndReturnSessionMaker()
    #asyncio.create_task(update_qos_metrics_task())
    yield

# @asynccontextmanager
# async def subAppLifespan(app: FastAPI):
#     asyncio.create_task(update_qos_metrics_task())
#     yield

app = FastAPI(lifespan=lifespan)

from metrics.logging_config import setup_logging
from metrics.logging_middleware import GraphQLLoggingMiddleware
logger = setup_logging(SERVICE_NAME)  # log vào /logs/gql_forms.log
app.add_middleware(GraphQLLoggingMiddleware, service_name=SERVICE_NAME)


from fastapi import Request, Response
import json
import time

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


# Middleware log toàn bộ HTTP requests
#app.add_middleware(RequestLoggingMiddleware, service_name="frontend")

# Nếu có GraphQL: middleware log query content luôn
#app.add_middleware(GraphQLLoggingMiddleware, service_name="frontend", gql_path="/api/gql")


# @app.get("/health")
# async def health_check():
#     metrics = qos_monitor.calculate_metrics()
#     is_healthy = metrics["availability"] >= 95.0  # Ngưỡng tính khả dụng
        
#     if is_healthy:
#         return {"status": "healthy", "metrics": metrics}
#     else:
#         return {"status": "unhealthy", "metrics": metrics}
# Middleware đo QoS cho tất cả các app

from .appindex import createIndexResponse
# @app.exception_handler(StarletteHTTPException)
# async def custom_http_exception_handler(request, exc):
#     print(exc)
#     return await createIndexResponse(request=request)

# from .authenticationMiddleware import BasicAuthenticationMiddleware302, BasicAuthBackend
from uoishelpers.authenticationMiddleware import BasicAuthenticationMiddleware302, BasicAuthBackend

#prepiseme BasicAuthBackend pomoci plneho 4. fazoveho, ten zabezpeci funkcnot pri zrusenem tokenu
from .BasicAuthBackend4Phase import BasicAuthBackend4Phase as BasicAuthBackend

JWTPUBLICKEY = os.environ.get("JWTPUBLICKEY", "http://localhost:8000/oauth/publickey")
JWTRESOLVEUSERPATH = os.environ.get("JWTRESOLVEUSERPATH", "http://localhost:8000/oauth/userinfo")


from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app, metric_namespace="frontnend").expose(app, endpoint="/metrics")

# from .prometheus import prometheusClient
# app.mount("/metrics", prometheusClient)


# ###################################################################################
# from prometheus_fastapi_instrumentator import Instrumentator,metrics
# from prometheus_fastapi_instrumentator.metrics import Info
# from typing import Callable
# import time
# from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, make_asgi_app
# from fastapi import Response


# #https://github.com/trallnag/prometheus-fastapi-instrumentator?tab=readme-ov-file#adding-metrics
# #create instrumentator
# instrumentator = Instrumentator(
#     should_group_status_codes=False,
#     should_ignore_untemplated=True,
#     should_respect_env_var=True,
#     should_instrument_requests_inprogress=True,
#     excluded_handlers=[".*admin.*", "/metrics"],
#     env_var_name="ENABLE_METRICS",
#     inprogress_name="inprogress",
#     inprogress_labels=True,
# )
# #instrumentator= Instrumentator()

# #Adding metrics

# #this function add metric that only takes status as label
# instrumentator.add(
#     metrics.requests(
#         metric_name="http_requests_total",
#         metric_doc="Total number of requests by  status",
#         #metric_namespace="frontnend",
#         should_include_method= False,
#         should_include_handler= False,
#         should_include_status=True,
#     )
# )

# instrumentator.add(
#     metrics.latency(
#         metric_name="http_request_duration_seconds",
#         metric_doc="Duration of HTTP requests in seconds by handler",
#         should_include_method= False,
#         should_include_handler= True,
#         should_include_status= False ,
#         buckets = (0.5,1,1.5,2,4,float("inf"))
#     )
# )

# # create Metrics

# # ok rui
# def http_successful_requests_total() -> Callable[[Info], None]:
#     METRIC = Counter(
#         "http_successful_requests_total", 
#         "Total number of successful HTTP requests (2xx: success, 3xx: redirect) by method and handler",
#         ["status"]
#     )

#     def instrumentation(info: Info) -> None:
#         # Kiểm tra nếu mã trạng thái HTTP là 2xx
#         #if 200 <= info.request.status_code < 300:
#         #tại sao lại là modified_status vì mình đã xem ở trong Info
#         if info.modified_status == "2xx":
#             METRIC.labels("2xx").inc()  # Tăng counter khi có request thành công
#         if info.modified_status == "3xx":
#             METRIC.labels("3xx").inc() 
#         #METRIC.labels(status="2xx").inc
#     return instrumentation
# instrumentator.add(http_successful_requests_total())

# #ok rui
# def gql_query_requests_total() -> Callable[[Info], None]:
#     METRIC = Counter(
#         "gql_query_requests_total", 
#         "Total number of  HTTP gql query requests by method and handler",
#         ["handler","method"]
#         #In GraphQL API, the server almost always returns HTTP status code 200
#         #status code 4xx: error from client
#     )
#     def instrumentation(info: Info) -> None:
#         if info.modified_handler =="/api/gql" and info.method=="POST":
#             METRIC.labels(handler="/api/gql",method="POST").inc()
#     return instrumentation
# instrumentator.add(gql_query_requests_total())

# #Perform instrumentation with specify namespace 
# #instrumentator.instrument(app, metric_namespace="frontnend")
# instrumentator.instrument(app)

# #expose endpoint
# #@app.on_event("startup")
# #async def startup():
# instrumentator.expose(app, endpoint="/metrics")

import json

#######################################################################
#
# pouziti html jako SPA - single page applications
# predpoklada se, ze html maji integrovany router (react-router) 
# a ze si obslouzi zbytek cesty
# aplikace jsou chraneny autentizaci
#
#######################################################################
configFile = "config.json"
dirName = ""
if __file__:
    dirName = os.path.dirname(__file__)

print("executing in", dirName)

configFile = dirName + "/" + configFile
def createApp(key, setup):
    file = setup["file"]
    print(f"creating sub app {key} with setup {setup}")
    subApp = FastAPI()
    @subApp.get("/{file_path:path}")
    async def getFile(file_path: str):
        filename = dirName + "/htmls/" + file
        print(f"serving app {file} from `{filename}`")
        if os.path.isfile(filename):
            return FileResponse(filename)
        else:
            return RedirectResponse("/")
    
    if not DEMO:
        subApp.add_middleware(BasicAuthenticationMiddleware302, backend=BasicAuthBackend(JWTPUBLICKEY=JWTPUBLICKEY, JWTRESOLVEUSERPATH=JWTRESOLVEUSERPATH))
    app.mount("/" + key, subApp)

with open(configFile, "r", encoding="utf-8") as f:
    config = json.load(f)
    print(f"app config set to\n{config}")
    for key, setup in config.items():
        createApp(key, setup)

@app.get("/logout")
def logout():
    result = RedirectResponse("/oauth/login2?redirect_uri=/", status_code=303)
    result.delete_cookie("authorization")
    return result

#######################################################################
#
# tato cast je pro FAKE autentizaci
# poskytuje autentizacni (prihlasovaci stranku)
# ma volny pristup
#
#######################################################################
demoData = getDemoData()
users = demoData.get("users", [])

async def bindedPasswordValidator(email, password):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
    result = await passwordValidator(asyncSessionMaker, email, password)
    logging.info(f"check for {email} & {password} -> {result}")
    return result

async def bindedEmailMapper(email):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
    logging.info(f"bindedEmailMapper {email}")

    result = await emailMapper(asyncSessionMaker, email)
    return result

db_users = [{"id": user["id"], "email": user["email"]} for user in users]
print(f"first user {db_users[0]}", flush=True)
app.mount("/oauth", OAuthServer.createServer(
    db_users=db_users,
    passwordValidator=bindedPasswordValidator,
    emailMapper=bindedEmailMapper
    ))

#######################################################################
#
# tato cast je proxy pro API endpoint
# je dostupna jen s autentizaci
#
#######################################################################
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from opentelemetry import trace
# from opentelemetry.instrumentation.requests import RequestsInstrumentor
# from opentelemetry.sdk.resources import SERVICE_NAME, Resource
# # Init provider
# trace.set_tracer_provider(TracerProvider())
# tracer = trace.get_tracer_provider().get_tracer(__name__)

# # Add exporter (đẩy trace tới Grafana Tempo hoặc OTLP endpoint)
# otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4318/v1/traces", insecure=True)
# span_processor = BatchSpanProcessor(otlp_exporter)
# trace.get_tracer_provider().add_span_processor(span_processor)

# # Gắn vào FastAPI
# FastAPIInstrumentor.instrument_app(app) 

# # Setup logger cho service (vd: frontend)
# setup_logging(service_name="frontend", log_dir="/logs")


apiApp = FastAPI()
if not DEMO:
    apiApp.add_middleware(BasicAuthenticationMiddleware302, backend=BasicAuthBackend(JWTPUBLICKEY=JWTPUBLICKEY, JWTRESOLVEUSERPATH=JWTRESOLVEUSERPATH))
app.mount("/api", apiApp)

from .gqlproxy import connectProxy
connectProxy(apiApp)

#######################################################################
#
# tato cast je pro debug
# je dostupna jen s autentizaci
#
#######################################################################

debugApp = FastAPI()

@debugApp.get("/")
async def hello(requets: Request):
    client = requets.client
    headers = requets.headers
    cookies = requets.cookies
    import aiohttp
    import jwt
    bearer = cookies.get("authorization")
    token = bearer.replace("Bearer ", "")

    JWTPUBLICKEYURL="http://locahost:8000/oauth/publickey"
    JWTPUBLICKEYURL="http://127.0.0.1:8000/oauth/publickey"
    async with aiohttp.ClientSession() as session:
        async with session.get(JWTPUBLICKEYURL) as resp:
            assert resp.status == 200, resp
            pktext = await resp.text() 
    print(f"have pktext={pktext}")
    logging.info(f"have pktext={pktext}")
    pkey = pktext.replace('"', "").replace("\\n", "\n")
    jwtdecoded = jwt.decode(jwt=token, key=pkey, algorithms=["RS256"])
    print(f"jwtdecoded = {jwtdecoded}")
    logging.info(f"jwtdecoded = {jwtdecoded}")
    userid = jwtdecoded["user_id"]
    print(f"userid = {userid}")
    logging.info(f"userid = {userid}")
    print(f"SUCCESS")
    logging.info(f"SUCCESS")
    return {
        "hello": "world",
        "client": client,
        "headers": headers,
        "cookies": cookies,
        "token": token,
        "publickey": pkey,
        "jwtdecoded": jwtdecoded,
        "userid": userid
        }

if not DEMO:
    debugApp.add_middleware(BasicAuthenticationMiddleware302, backend=BasicAuthBackend(JWTPUBLICKEY=JWTPUBLICKEY, JWTRESOLVEUSERPATH=JWTRESOLVEUSERPATH))

app.mount("/debug", debugApp)

#######################################################################
#
# tato cast je pro index - portal
# je dostupna jen s autentizaci
#
#######################################################################

indexApp = FastAPI()
@indexApp.get("/")
async def index(request: Request):
    return await createIndexResponse(request=request)
app.mount("/index", indexApp)

if not DEMO:
    indexApp.add_middleware(BasicAuthenticationMiddleware302, backend=BasicAuthBackend(JWTPUBLICKEY=JWTPUBLICKEY, JWTRESOLVEUSERPATH=JWTRESOLVEUSERPATH))

#######################################################################
#
# tato cast je pro index - portal
# je dostupna jen s autentizaci
#
#######################################################################

analyticsApp = FastAPI()
@analyticsApp.get("/{file_path:path}/")
async def analytics(file_path, request: Request):
    
    headers = dict(request.headers)
    query_params=request.query_params
    fullurl = (request.url.include_query_params(**query_params))
    # print(fullurl)
    path = request.url.path
    fulluri = path + f"{fullurl}".split(request.url.path)[1]
    # fulluri = (request._url)
    # fulluri = (request.url.path)
    # print(fulluri)
    remoteurl = f"http://analytics:8000{fulluri}"
    # print(remoteurl)
    try:
        print("remoteurl", remoteurl)
        print("headers", headers)
        del headers["host"]
        async with aiohttp.ClientSession() as session:
            async with session.get(remoteurl, headers=headers) as resp:
                # print(resp.status)
                text = await resp.text()
    except Exception as e:
        print("except", e)
            
    return HTMLResponse(content=text, status_code=resp.status)
    
app.mount("/analysis", analyticsApp)

if not DEMO:
    indexApp.add_middleware(BasicAuthenticationMiddleware302, backend=BasicAuthBackend(JWTPUBLICKEY=JWTPUBLICKEY, JWTRESOLVEUSERPATH=JWTRESOLVEUSERPATH))

#######################################################################
#
# tato cast je pro root
# je dostupna bez autentizace, ale dela jen presmerovani
#
#######################################################################

@app.get("/")
async def index(request: Request):
    return RedirectResponse("/index", status_code=302)
