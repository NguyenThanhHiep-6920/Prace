# FAQs


## Comments on Dabatase Models

SQLAlchemy allows to use `comment` named parameter for `Column`.
This comments will be attached to table definition.
They become readable directly from SQL Server.

## Comments on GraphQL entities

`strawberry` package offers `description` named parameter for:
- types
- inputs
- fields
- ...

Such `description` becomes a part of GQL endpoint and introspection query can fetch it.
It is also part of several documentation UIs (GrpahiQL, Voyager, ...)

## How to convert py file into directory

This is handy for spagetti source code.
If you have long sourcefile, you should split it into several files.
First step to do is create directory with same name as file (without `.py`).
Then move file inside this directory and rename it to `__init__.py`.
At this stage the code should be still ok.

Now you can extract items (classes, functions, ...) to separate files.
Do not forget to add `import` statement in `__init__.py` file to import items from separated files.
This way the code is possible divide into several files.

Do not forget to test if your changes are ok.

## Circular import 

```
ImportError: cannot import name 'FormWhereFilter' from partially initialized module 'GraphTypeDefinitions.FormGQLModel' (most likely due to a circular import)
```

In file A you are importing somehow item from file B while somewhere in file B you are importing item from file A.
For type annotations next thing could be used
```python
from typing import Annotated
FormCategoryGQLModel = Annotated["FormCategoryGQLModel", strawberry.lazy(".FormCategoryGQLModel")]
```

where `FormCategoryGQLModel` is type lazily initialized from file `.FormCategoryGQLModel`.

Annotated type cannot act as original class. To use original class (`ItemCategoryGQLModel.resolve_reference` as an example) you must import this class localy (see below).

```python
@strawberry.field(description="""Type category""")
async def category(self, info: strawberry.types.Info) -> typing.Optional["ItemCategoryGQLModel"]:
    from .ItemCategoryGQLModel import ItemCategoryGQLModel
    return await ItemCategoryGQLModel.resolve_reference(info=info, id=self.category_id)
```

## Dataloaders

Asynchronous dataloaders are usefull while you want load many items from same dabase table.
They allow convert many statements (usually queries by primary key) into one.

They also supports cacheing to avoid multiple fetches for same entity.
If you want to make cache constistent, you need to catch all CUD operations.
Such operations must, at least, clear appropriate part of cache.

When using cache, multiple loaders for same table must be joined into one loader.

If you want, it is possible to extend cache functionality by redis.

## Tests

This is project exposing an API. 
Thus majority of tests should be doable by posting a query to API endpoint.
There are sets of test creators, see file `tests/gqlshared.py`.
This file conains functions:
- `createByIdTest`
- `createPageTest`
- `createResolveReferenceTest`
- `createFrontendQuery`
- `createUpdateQuery`

### `createByIdTest`
This post a "`ById`" query. 
Result is a single entity identified by Id.
Result is compared to data stored in `systemdata.json` file (key `tableName`).

```python
test_query_form_by_id = createByIdTest(tableName="forms", queryEndpoint="formById")
```

### `createPageTest`
```python
test_query_form_page = createPageTest(tableName="forms", queryEndpoint="formPage")
```

### `createResolveReferenceTest`
This is functionality for federated API.
```python
test_reference_forms = createResolveReferenceTest(tableName='forms', gqltype='FormGQLModel', attributeNames=["id", "name", "lastchange", "valid", "status", "sections {id}", "creator {id}"])
```

### `createFrontendQuery`
This simply post a query (`R` opearation) and checks (see `asserts`) if conditions are met.

```python
test_form_insert = createFrontendQuery(query="""
    mutation($id: UUID!, $name: String!) { 
        result: formInsert(form: {id: $id, name: $name}) { 
            id
            msg
            form {
                id
                name
                type { id }
            }
        }
    }
    """, 
    variables={"id": "ccde3a8b-81d0-4e2b-9aac-42e0eb2255b3", "name": "new form"},
    asserts=[]
)
```

### `createUpdateQuery`
For update a `lastchange` must be known, but this is different for every single run. A database query should give actual value.
When the value is known, update is possible and result (response) should be tested.
```python
test_form_update = createUpdateQuery(
    query="""
        mutation($id: UUID!, $name: String!, $lastchange: DateTime!) {
            formUpdate(form: {id: $id, name: $name, lastchange: $lastchange}) {
                id
                msg
                form {
                    id
                    name
                }
            }
        }
    """,
    variables={"id": "190d578c-afb1-11ed-9bd8-0242ac110002", "name": "new name"},
    tableName="forms"
)
```