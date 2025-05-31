import pytest
import logging
import uuid
import sqlalchemy
import json
import datetime

async def getRow(async_session_maker, tableName, id):
    statement = sqlalchemy.text(f"SELECT id, lastchange FROM {tableName} WHERE id=:id").bindparams(id=id)
    #statement = sqlalchemy.text(f"SELECT id, lastchange FROM {tableName}")
    print("statement", statement, flush=True)
    async with async_session_maker() as session:
        rows = await session.execute(statement)
        row = rows.first()
    return row    

prefix = "./tests/test_queries/gqls"
def readQuery(tablename, queryname):
    filename = f"{prefix}/{tablename}/{queryname}.gql"
    with open(filename, "r", encoding="utf-8") as fi:
        lines = fi.readlines()
    query = ''.join(lines)
    return query

def parser(json_dict):
    for (key, value) in json_dict.items():
        # if key in ["startdate", "enddate", "lastchange", "created"]:
        #     if value is None:
        #         dateValueWOtzinfo = None
        #     else:
        #         try:
        #             dateValue = datetime.datetime.fromisoformat(value)
        #             dateValueWOtzinfo = dateValue.replace(tzinfo=None)
        #         except:
        #             print("jsonconvert Error", key, value, flush=True)
        #             dateValueWOtzinfo = None
            
        #     json_dict[key] = dateValueWOtzinfo
        
        if (key in ["id", "changedby", "createdby"]) or ("_id" in key):
            
            if key == "outer_id":
                json_dict[key] = value
            elif value not in ["", None]:
                json_dict[key] = uuid.UUID(value)
            else:
                print(key, value)

    return json_dict

def readVariables(tablename, queryname):
    filename = f"{prefix}/{tablename}/{queryname}.var.json"
    with open(filename, "r", encoding="utf-8") as fi:
        # data = json.load(fi, object_hook=parser)
        data = json.load(fi)
    return data

def readResult(tablename, queryname):
    filename = f"{prefix}/{tablename}/{queryname}.res.json"
    with open(filename, "r", encoding="utf-8") as fi:
        # data = json.load(fi, object_hook=parser)
        data = json.load(fi)
    return data

def createQueryTest(tableName, queryName, variables=None, resultItem=None):
    @pytest.mark.asyncio
    async def result_test(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo, Env_GQLUG_ENDPOINT_URL_8124):

        def testResult(resp):
            print("response", resp)
            errors = resp.get("errors", None)
            assert errors is None, f"response has errors {errors}"
            
            respdata = resp.get("data", None)
            assert respdata is not None, f"response {resp} has not data"
            
            result = respdata["result"]
            assert result is not None, f"response {resp} has not entity"

            attributeNames = set(result.keys()) & set(expected_result.keys())
            print(f"tablename {tableName} \n datarow {expected_result} \n result {result}")
            for att in attributeNames:
                if att in ["lastchange"]:
                    continue
                assert f'{result[att]}' == f'{expected_result[att]}', f"attributes are different {att} in tablename {tableName} datarow {datarow} result {result}"

        schemaExecutor = SchemaExecutorDemo

        query = readQuery(tablename=tableName, queryname=queryName)
        if variables is None:
            variable_values = readVariables(tablename=tableName, queryname=queryName)
        else:
            variable_values = variables
        if resultItem is None:
            expected_result = readResult(tablename=tableName, queryname=queryName)
        else:
            expected_result = resultItem

        # append(queryname=f"{queryEndpoint}_{tableName}", query=query, variables=variable_values)        
        logging.info(f"query for {query} with {variable_values}")

        resp = await schemaExecutor(query, variable_values)
        testResult(resp)
        # resp = await clientExecutor(query, variable_values)
        # testResult(resp)

    return result_test
    
def createByIdTest(tableName):
    @pytest.mark.asyncio
    async def result_test(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo, Env_GQLUG_ENDPOINT_URL_8124):

        def testResult(resp):
            print("response", resp)
            errors = resp.get("errors", None)
            assert errors is None, f"response has errors {errors}"
            
            respdata = resp.get("data", None)
            assert respdata is not None, f"response {resp} has not data"
            
            result = respdata["result"]
            assert result is not None, f"response {resp} has not entity"

            attributeNames = set(result.keys()) & set(datarow.keys())
            print(f"tablename {tableName} \n datarow {datarow} \n result {result}")
            for att in attributeNames:
                if att in ["lastchange"]:
                    continue
                assert f'{result[att]}' == f'{datarow[att]}', f"attributes are different {att} in tablename {tableName} datarow {datarow} result {result}"

        clientExecutor = ClientExecutorDemo
        schemaExecutor = SchemaExecutorDemo

        data = DemoData
        datarow = data[tableName][0]
        # content = "{" + ", ".join(attributeNames) + "}"
        # query = "query($id: UUID!){" f"result: {queryEndpoint}(id: $id)" f"{content}" "}"
        query = readQuery(tablename=tableName, queryname="read")

        variable_values = {"id": f'{datarow["id"]}'}
        
        row = await getRow(SQLite, tableName=tableName, id=datarow["id"])
        assert row is not None, f"row with id={datarow['id']} not found in DB"

        # append(queryname=f"{queryEndpoint}_{tableName}", query=query, variables=variable_values)        
        logging.info(f"query for {query} with {variable_values}")

        resp = await schemaExecutor(query, variable_values)
        testResult(resp)
        # resp = await clientExecutor(query, variable_values)
        # testResult(resp)

    return result_test

def createPageTest(tableName):
    @pytest.mark.asyncio
    async def result_test(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo):

        def testResult(resp):
            errors = resp.get("errors", None)
            assert errors is None, f"resp has errors {errors}"
            respdata = resp.get("data", None)
            assert respdata is not None

            result = respdata.get("result", None)
            assert result is not None
            datarows = data[tableName]           
            
            attributeNames = set(result[0].keys()) & set(datarows[0].keys())

            for rowa, rowb in zip(result, datarows):
                for att in attributeNames:
                    if att in ["lastchange"]:
                        continue
                    assert f'{rowa[att]}' == f'{rowb[att]}', f"attributes are different {att} in tablename {tableName}"

        schemaExecutor = SchemaExecutorDemo
        clientExecutor = ClientExecutorDemo

        data = DemoData

        # content = "{" + ", ".join(attributeNames) + "}"
        # query = "query{" f"{queryEndpoint}" f"{content}" "}"
        query = readQuery(tablename=tableName, queryname="readpage")

        # append(queryname=f"{queryEndpoint}_{tableName}", query=query)

        resp = await schemaExecutor(query)
        testResult(resp)
        # resp = await clientExecutor(query)
        # testResult(resp)
        
    return result_test

def createResolveReferenceTest(tableName, gqltype, attributeNames=["id", "name"]):
    @pytest.mark.asyncio
    async def result_test(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo, Context, Env_GQLUG_ENDPOINT_URL_8124):

        def testResult(resp):
            # print(resp)
            errors = resp.get("errors", None)
            assert errors is None, f" response has errors {errors}"
            respdata = resp.get("data", None)
            assert respdata is not None, f"missing data in response {resp}"

            logging.info(respdata)
            respdata = respdata.get('_entities', None)
            assert respdata is not None, f"missing _entities in response {resp}"

            assert len(respdata) == 1, f"_entities has not just one member {respdata}"
            respdata = respdata[0]
            assert respdata is not None, f"got None value for id {rowid}"
            assert respdata['id'] == rowid, f"different id {respdata['id']} in response, expected {rowid}"

        schemaExecutor = SchemaExecutorDemo
        clientExecutor = ClientExecutorDemo

        content = "{" + ", ".join(attributeNames) + "}"

        data = DemoData
        table = data[tableName]
        for row in table:
            rowid = f"{row['id']}"

            # query = (
            #     'query($id: UUID!) { _entities(representations: [{ __typename: '+ f'"{gqltype}", id: $id' + 
            #     ' }])' +
            #     '{' +
            #     f'...on {gqltype}' + content +
            #     '}' + 
            #     '}')

            # variable_values = {"id": rowid}

            # query = ("query($rep: [_Any!]!)" + 
            #     "{" +
            #     "_entities(representations: $rep)" +
            #     "{"+
            #     f"    ...on {gqltype} {content}"+
            #     "}"+
            #     "}"
            # )
            query = readQuery(tablename=tableName, queryname="resolve")
            variable_values = {"rep": [{"__typename": f"{gqltype}", "id": f"{rowid}"}]}

            logging.info(f"query representations {query} with {variable_values}")
            # resp = await clientExecutor(query, {**variable_values})
            # testResult(resp)
            resp = await schemaExecutor(query, {**variable_values})
            testResult(resp)

        # append(queryname=f"{gqltype}_representation", query=query)

    return result_test

def createInsertQuery(tableName, variables=None):
    @pytest.mark.asyncio
    async def test_insert_query(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo, Context, Env_GQLUG_ENDPOINT_URL_8124):    
        def testResult(resp, variables):
            # print(resp)
            errors = resp.get("errors", None)
            assert errors is None, f" response has errors {errors}"
            respdata = resp.get("data", None)
            assert respdata is not None, f"missing data in response {resp}"

            # logging.info(respdata)
            result = respdata.get('result', None)
            assert result is not None, f"missing result in response {resp}"

            entityid = result.get("id", None)
            assert entityid is not None, f"missing id in result {result}"

            msg = result.get("msg", None)
            assert msg is not None, f"missing msg in result {result}"

            entity = result.get("result", None)
            assert entity is not None, f"missing entity in result {result}"

            attributeNames = set(entity.keys()) & set(variables.keys())

            for attribute in attributeNames:
                assert entity[attribute] == f'{variables[attribute]}', f"attributes are different {attribute} in tablename {tableName}"
        
        queryname="create"
        query = readQuery(tablename=tableName, queryname=queryname)
        if variables is None:
            variable_values = readVariables(tablename=tableName, queryname=queryname)
        else:
            variable_values = variables

        # logging.debug("insertQuery")
        # async_session_maker = await prepare_in_memory_sqllite()
        # await prepare_demodata(async_session_maker)
        # context_value = createContext(async_session_maker)
        logging.debug(f"query for {query} with {variables}")
        print(f"query for {query} with {variables}")

        # append(queryname=f"query", query=query, variables=variables)
        resp = await SchemaExecutorDemo(
            query=query, 
            variable_values={**variable_values}
        )
        # resp = await schema.execute(
        #     query=query, 
        #     variable_values=variables, 
        #     context_value=context_value
        # )
        testResult(resp=resp, variables=variable_values)
    return test_insert_query

def createUpdateQuery(tableName, variables=None):
    @pytest.mark.asyncio
    async def test_update(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo, Context, Env_GQLUG_ENDPOINT_URL_8124):
        def testResult(resp, variables):
            # print(resp)
            errors = resp.get("errors", None)
            assert errors is None, f" response has errors {errors}"
            respdata = resp.get("data", None)
            assert respdata is not None, f"missing data in response {resp}"

            # logging.info(respdata)
            result = respdata.get('result', None)
            assert result is not None, f"missing result in response {resp}"

            entityid = result.get("id", None)
            assert entityid is not None, f"missing id in result {result}"

            msg = result.get("msg", None)
            assert msg is not None, f"missing msg in result {result}"

            entity = result.get("result", None)
            assert entity is not None, f"missing entity in result {result}"

            attributeNames = set(entity.keys()) & set(variables.keys())

            for attribute in attributeNames:
                assert f'{entity[attribute]}' == f'{variables[attribute]}', f"attributes are different {attribute} in tablename {tableName}"

        queryR = readQuery(tablename=tableName, queryname="read")
        queryU = readQuery(tablename=tableName, queryname="update")
        logging.debug("test_update")
        # variables["id"] = uuid.UUID(f"{variables['id']}")
        assert "$lastchange: DateTime!" in queryU, "query must have parameter $lastchange: DateTime!"
        assert "lastchange: $lastchange" in queryU, "query must use lastchange: $lastchange"
        
        if variables is None:
            variable_values = readVariables(tablename=tableName, queryname="update")
        else:
            variable_values = variables

        assert variable_values.get("id", None) is not None, "variables has not id"

        resp = await SchemaExecutorDemo(
            query=queryR, 
            variable_values={"id": variable_values['id']}
        )
        data = resp.get("data", None)
        assert data is not None, f"reading data got data None {resp}"
        result = data.get("result", None)
        assert result is not None, f"got no result {resp}"
        lastchange = result.get("lastchange", None)
        assert lastchange is not None, f"I do not know lastchange {resp}"

        resp = await SchemaExecutorDemo(
            query=queryU, 
            variable_values={**variable_values, "lastchange": lastchange}
        )
        testResult(resp, variables=variable_values)
        # async_session_maker = SQLite

        # print("variables['id']", variables, flush=True)
        # statement = sqlalchemy.text(f"SELECT id, lastchange FROM {tableName} WHERE id=:id").bindparams(id=variables['id'])
        # #statement = sqlalchemy.text(f"SELECT id, lastchange FROM {tableName}")
        # print("statement", statement, flush=True)
        # async with async_session_maker() as session:
        #     rows = await session.execute(statement)
        #     row = rows.first()
            
            # print("row", row)
            # id = row[0]
            # lastchange = row[1]

            # print(id, lastchange)

        # variables["lastchange"] = lastchange
        # variables["id"] = f'{variables["id"]}'
        
        # logging.debug(f"query for {query} with {variables}")
        # print(f"query for {query} with {variables}")

        # # append(queryname=f"query_{tableName}", mutation=query, variables=variables)
        # resp = await SchemaExecutorDemo(
        #     query=query, 
        #     variable_values=variables
        # )
        # # resp = await schema.execute(
        # #     query=query, 
        # #     variable_values=variables, 
        # #     context_value=context_value
        # # )

        # assert resp.get("errors", None) is None, resp["errors"]
        # respdata = resp.get("data", None)
        # assert respdata is not None, "GQL response is empty"
        # print("respdata", respdata)
        # keys = list(respdata.keys())
        # assert len(keys) == 1, "expected update test has one result"
        # key = keys[0]
        # result = respdata.get(key, None)
        # assert result is not None, f"{key} is None (test update) with {query}"
        # entity = None
        # for key, value in result.items():
        #     print(key, value, type(value))
        #     if isinstance(value, dict):
        #         entity = value
        #         break
        # assert entity is not None, f"expected entity in response to {query}, got {resp}"

        # for key in variables.keys():
        #     if key in ["id", "lastchange"]:
        #         continue
        #     value = entity[key]
        #     print("attribute check", type(key), f"[{key}] is {value} ?= {variables[key]}")
            # assert value == variables[key], f"test on update failed {value} != {variables[key]}"

        

    return test_update

def createFrontendQuery(query="{}", variables={}, asserts=[]):
    @pytest.mark.asyncio
    async def test_frontend_query(SQLite, DemoData, ClientExecutorDemo, SchemaExecutorDemo, Context, Env_GQLUG_ENDPOINT_URL_8124):    
        logging.debug("createFrontendQuery")
        # async_session_maker = await prepare_in_memory_sqllite()
        # await prepare_demodata(async_session_maker)
        # context_value = createContext(async_session_maker)
        logging.debug(f"query for {query} with {variables}")
        print(f"query for {query} with {variables}")

        # append(queryname=f"query", query=query, variables=variables)
        resp = await SchemaExecutorDemo(
            query=query, 
            variable_values=variables
        )
        # resp = await schema.execute(
        #     query=query, 
        #     variable_values=variables, 
        #     context_value=context_value
        # )

        assert resp.get("errors", None) is None, resp["errors"]
        respdata = resp.get("data", None)
        logging.info(f"query for \n{query} with \n{variables} got response: \n{respdata}")
        for a in asserts:
            a(respdata)
    return test_frontend_query