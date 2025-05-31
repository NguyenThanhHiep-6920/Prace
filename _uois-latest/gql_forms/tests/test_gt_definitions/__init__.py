# import pytest
# from GraphTypeDefinitions import schema

# from ..shared import (
#     prepare_demodata,
#     prepare_in_memory_sqllite,
#     get_demodata,
#     createContext,
# )

# from ..gqlshared import (
#     createByIdTest, 
#     createPageTest, 
#     createResolveReferenceTest, 
#     createFrontendQuery, 
#     createUpdateQuery
# )








# @pytest.mark.asyncio
# async def test_large_query_1():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formrequests']
#     row = table[0]
#     rowid = f"{row['id']}"
#     query = 'query{requestById(id: "' + rowid + '''") { 
#         id
#         name
#         lastchange
#         histories {
#             request { id }
#             form {
#                 id
#                 name
#                 nameEn
#                 sections {
#                     id
#                     name
#                     order
#                     form { id }
#                     parts {
#                         id
#                         name
#                         items {
#                             id
#                             name
#                         }
#                     }
#                 }
#                 type {
#                     id
#                     name
#                     nameEn
#                     category {
#                         id
#                         name
#                         nameEn
#                     }
#                 }

#             }
#         }
#     }}'''

#     context_value = createContext(async_session_maker)
#     resp = await schema.execute(query, context_value=context_value)
#     data = resp.data
#     data = data['requestById']

#     print(data, flush=True)
    
#     assert resp.errors is None
#     assert data['id'] == rowid

# @pytest.mark.asyncio
# async def test_request_createdby():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formrequests']
#     row = table[0]
#     rowid = f"{row['id']}"
#     query = 'query{requestById(id: "' + rowid + '''") { 
#         id
#         name
#         lastchange
#         creator { id }
#     }}'''

#     context_value = createContext(async_session_maker)
#     resp = await schema.execute(query, context_value=context_value)
#     data = resp.data
#     data = data['requestById']

#     print(data, flush=True)
    
#     assert resp.errors is None
#     assert data['id'] == rowid

# @pytest.mark.asyncio
# async def test_large_query():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formrequests']
#     row = table[0]
#     user_id = row["createdby"]
#     user_id = f"{user_id}"

#     query = '''query($user_id: UUID!){
#         result: requestsPage(where:{createdby: {_eq: $user_id}}) { 
#         id
#         lastchange
#         creator {
#             id
#         }
#         histories {
#             id
#             request { id }
#             form { id }
#         }
#     }}'''

#     context_value = createContext(async_session_maker)
#     variable_values = {"user_id": user_id}
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     print(resp)
#     assert resp.errors is None
#     data = resp.data
#     data = data['result']
#     data = data[0]
#     #assert False
#     #respdata = resp.data['eventById']
    

#     assert data['creator']['id'] == user_id


# @pytest.mark.asyncio
# async def _test_resolve_section():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formparts']
#     row = table[0]

#     query = '''
#             query {
#                 _entities(representations: [{ __typename: "PartGQLModel", id: "''' + row['id'] +  '''" }]) {
#                     ...on PartGQLModel {
#                         id
#                         section { id }
#                         lastchange
#                         order
#                     }
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     resp = await schema.execute(query, context_value=context_value)
#     data = resp.data
#     print(data, flush=True)
#     data = data['_entities'][0]


# @pytest.mark.asyncio
# async def test_resolve_item():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formitems']
#     row = table[0]
#     rowid = f"{row['id']}"
#     query = '''
#             query($id: UUID!) {
#                 _entities(representations: [{ __typename: "FormItemGQLModel", id: $id }]) {
#                     ...on FormItemGQLModel {
#                         id
#                         part { id }
#                         lastchange
#                         order
#                         name
#                         value
#                         type { 
#                             id
#                             category { id }
#                         }
#                     }
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {"id": rowid}
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     data = resp.data
#     print(data, flush=True)
#     data = data['_entities'][0]


# @pytest.mark.asyncio
# async def test_reference_history():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formhistories']
#     row = table[0]
#     id = f'{row["id"]}'
#     query = '''
#             query($id: UUID!) {
#                 _entities(representations: [{ __typename: "RequestHistoryGQLModel", id: $id }]) {
#                     ...on RequestHistoryGQLModel {
#                         id
#                         name
#                         lastchange
#                         request { id }
#                         form { id }
#                     }
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {'id': id}

#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data
#     print(data, flush=True)
#     data = data['_entities'][0]
#     assert data['id'] == id


# @pytest.mark.asyncio
# async def test_reference_user():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['users']
#     row = table[0]
#     id = f'{row["id"]}'
#     query = '''
#             query($id: UUID!) {
#                 _entities(representations: [{ __typename: "UserGQLModel", id: $id }]) {
#                     ...on UserGQLModel {
#                         id
#                     }
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {'id': id}

#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data
#     print(data, flush=True)
#     data = data['_entities'][0]
#     assert data['id'] == id

    
# @pytest.mark.asyncio
# async def _test_requests_by_letters():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formrequests']
#     row = table[0]

#     query = '''
#             query($letters: String!) {
#                 requestsByLetters(letters: $letters) {
#                     id
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {'letters': row['name'][:4]}

#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data
#     print(data, flush=True)
#     data = data['requestsByLetters'][0]
#     assert data['id'] == row['id']

# @pytest.mark.asyncio
# async def _test_new_request():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
#     table = data['formtypes']
#     row = table[0]

#     query = '''
#             query($id: UUID!) {
#                 newRequest(formtypeId: $id) {
#                     id
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {'id': row['id']}
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data
#     print(data, flush=True)
#     data = data['newRequest']

#     rid = data['id']

#     query = '''
#             query($id: UUID!) {
#                 requestById(id: $id) {
#                     id
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {'id': rid}
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data
#     print(data, flush=True)
#     assert 'requestById' in data
#     data = data['requestById']
#     assert data['id'] == rid

#     print(data['id'], flush=True)

# @pytest.mark.asyncio
# async def test_say_hello_forms():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     query = '''
#             query($id: UUID!) {
#                 sayHelloForms(id: $id)
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {'id': '6d213a0d-2e24-4d4b-9595-90beb663a388'}
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data
#     print(data, flush=True)
#     data = data['sayHelloForms']
#     assert 'ello' in data

# @pytest.mark.asyncio
# async def _test_form_mutation():
#     async_session_maker = await prepare_in_memory_sqllite()
#     await prepare_demodata(async_session_maker)

#     data = get_demodata()
    
#     table = data["forms"]
#     row = table[0]
#     user_id = row["id"]


#     name = "form X"
#     query = '''
#             mutation(
#                 $name: String!
                
#                 ) {
#                 operation: formInsert(form: {
#                     name: $name
                    
#                 }){
#                     id
#                     msg
#                     entity: form {
#                         id
#                         name
#                         lastchange
#                     }
#                 }
#             }
#         '''

#     context_value = createContext(async_session_maker)
#     variable_values = {
#         "name": name
#     }
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
    
#     print(resp, flush=True)

#     assert resp.errors is None
#     data = resp.data['operation']
#     assert data["msg"] == "ok"
#     data = data["entity"]
#     assert data["name"] == name
    
#     #assert data["name"] == name
    
   
#     id = data["id"]
#     lastchange = data["lastchange"]
#     name = "NewName"
#     query = '''
#             mutation(
#                 $id: UUID!,
#                 $lastchange: DateTime!
#                 $name: String!
#                 ) {
#                 operation: formUpdate(form: {
#                 id: $id
#                 lastchange: $lastchange
#                 name: $name
#             }){
#                 id
#                 msg
#                 entity: form {
#                     name
#                     id
#                     lastchange
#                 }
#             }
#             }
#         '''
#     newName = "newName"
#     context_value = createContext(async_session_maker)
#     variable_values = {"id": id, "name": newName, "lastchange": lastchange}
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None

#     data = resp.data['operation']
#     assert data['msg'] == "ok"
#     data = data["entity"]
#     assert data["name"] == newName

#     # lastchange je jine, musi fail
#     resp = await schema.execute(query, context_value=context_value, variable_values=variable_values)
#     assert resp.errors is None
#     data = resp.data['operation']
#     assert data['msg'] == "fail"

#     pass
