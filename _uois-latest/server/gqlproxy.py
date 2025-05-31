import os
import aiohttp
from fastapi.responses import JSONResponse, FileResponse
from fastapi import Request
from pydantic import BaseModel
# from graphql import parse, OperationDefinitionNode
# from metrics.prometheus_metrics import (
#     GQL_QUERY_COUNT, GQL_QUERY_LATENCY, GQL_ERRORS, GQL_FIELDS_ACCESSED
# ) 

from .prometheus import collectTime

class Item(BaseModel):
    query: str
    variables: dict = None
    operationName: str = None

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
def connectProxy(app):

    proxy = os.environ.get("GQL_PROXY", "http://10.0.2.27:33001/gql")
    print("using proxy", proxy)

    @app.get("/gql", response_class=FileResponse)
    async def apigql_get():
        realpath = os.path.realpath("./pyserver/graphiql.html")
        result = realpath
        return result

    @app.get("/doc", response_class=FileResponse)
    async def apidoc_get():
        realpath = os.path.realpath("./pyserver/voyager.html")
        result = realpath
        return result

    @collectTime("gqlquery")
    @app.post("/gql", response_class=JSONResponse)
    async def apigql_post(data: Item, request: Request):
        print(data, flush=True)
        gqlQuery = {}
        if (data.operationName) is not None:
            gqlQuery["operationName"] = data.operationName

        gqlQuery["query"] = data.query
        if (data.variables) is not None:
            gqlQuery["variables"] = data.variables

        print(gqlQuery, flush=True)
        # print(demoquery)
        headers = request.headers
        print(headers)
        print(headers.items())
        print(headers.__dict__)
        c = dict(headers.items())
        headers = {"cookie": c.get("cookie", None)}
        authorizationHeader = c.get("authorization", None)
        if authorizationHeader is not None:
            headers["authorization"] = authorizationHeader
        AuthorizationHeader = c.get("Authorization", None)
        if authorizationHeader is not None:
            headers["Authorization"] = AuthorizationHeader
        print("outgoing:", headers)
        async with aiohttp.ClientSession() as session:
            async with session.post(proxy, json=gqlQuery, headers=headers) as resp:
                # print(resp.status)
                json = await resp.json()
        return JSONResponse(content=json, status_code=resp.status)
    # #@collectTime("gqlquery")
    # @app.post("/gql", response_class=JSONResponse)
    # async def apigql_post(data: Item, request: Request):
    #     #GQL_QUERY_COUNT.inc()
    #     fields = extract_fields_from_query(data.query)
    #     # backend_service = request.headers.get("x-gql-service")
    #     # if not backend_service:
    #     #     backend_service="unknown"
    #         #return JSONResponse(content={"error": "Missing x-gql-service header"}, status_code=400)
    #     for field_name in fields:
    #         GQL_FIELDS_ACCESSED.labels(field_name=field_name).inc()
    #     print(data, flush=True)
    #     gqlQuery = {}
    #     if (data.operationName) is not None:
    #         gqlQuery["operationName"] = data.operationName

    #     gqlQuery["query"] = data.query
    #     if (data.variables) is not None:
    #         gqlQuery["variables"] = data.variables

    #     print(gqlQuery, flush=True)
    #     # print(demoquery)
    #     headers = request.headers
    #     print(headers)
    #     print(headers.items())
    #     print(headers.__dict__)
    #     c = dict(headers.items())
    #     headers = {"cookie": c.get("cookie", None)}
    #     authorizationHeader = c.get("authorization", None)
    #     if authorizationHeader is not None:
    #         headers["authorization"] = authorizationHeader
    #     AuthorizationHeader = c.get("Authorization", None)
    #     if authorizationHeader is not None:
    #         headers["Authorization"] = AuthorizationHeader
    #     print("outgoing:", headers)
    #     try:
    #         with GQL_QUERY_LATENCY.time():
    #             async with aiohttp.ClientSession() as session:
    #                 async with session.post(proxy, json=gqlQuery, headers=headers) as resp:
    #                     json = await resp.json()
    #                     if not 200 <= resp.status < 300:
    #                         GQL_ERRORS.inc() 
    #                         #graphql_errors_total.labels(backend_service=backend_service).inc()       
    #         return JSONResponse(content=json, status_code=resp.status)
    #     except Exception:
    #         GQL_ERRORS.inc()
    #         return JSONResponse(content={"error": "Failed to query backend"}, status_code=500)