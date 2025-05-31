import asyncio
import aiohttp

hostname = "http://host.docker.internal:33001"
async def getToken(username, password):
    keyurl = f"{hostname}/oauth/login3"
    async with aiohttp.ClientSession() as session:
        async with session.get(keyurl) as resp:
            # print(resp.status)
            keyJson = await resp.json()
            print(keyJson)

        payload = {**keyJson, "username": username, "password": password}
        async with session.post(keyurl, json=payload) as resp:
            # print(resp.status)
            tokenJson = await resp.json()
            # print(tokenJson)
    return tokenJson.get("token", None)
            
def query(q, token):
    async def post(variables, token=token):
        gqlurl = f"{hostname}/api/gql"
        payload = {"query": q, "variables": variables}
        # headers = {"Authorization": f"Bearer {token}"}
        cookies = {'authorization': token}
        async with aiohttp.ClientSession() as session:
            # print(headers, cookies)
            async with session.post(gqlurl, json=payload, cookies=cookies) as resp:
                # print(resp.status)
                if resp.status != 200:
                    print(await resp.text())
                else:
                    response = await resp.json()
                    return response
    return post

def readQuery(name, token):
    prefix = "./gqls"
    filename = f"{prefix}/{name}.gql"
    with open(filename, "r", encoding="utf-8") as fi:
        lines = fi.readlines()
    q = ''.join(lines)
    print(filename, q)
    f = query(q, token)
    return f

def decomposeDict(data, attrs):
    return (data.get(key, None) for key in attrs.keys())

def attributeTypeToStr(attribute):
    kind, name, ofType = (attribute.get(key, None) for key in ["kind", "name", "ofType"])
    if kind == "SCALAR":
        return name
    if kind == "OBJECT":
        return name
    if kind == "NON_NULL":
        if ofType:
            return f"{attributeTypeToStr(ofType)}"
        else:
            return ""
    if kind == "LIST":
        return f"[{attributeTypeToStr(ofType)}]"

def printAttributeType(attribute):
    t = attribute.get("type", None)
    print(":", attributeTypeToStr(t))
    # print(t)
    pass

def printAttribute(attribute):
    (name, description, fields) = (attribute.get(key, None) for key in ["name", "description", "_"])
    print("\t", name, f'(description="""{description if description else ""}""")', sep="", end="")
    printAttributeType(attribute)

def printType(type, attrs = ["name", "description", "fields"]):
    (name, description, fields) = (type.get(key, None) for key in attrs)
    print(name, f'(description="""{description if description else ""}""")', sep="")
    if fields:
        for field in fields:
            printAttribute(field)


async def listtypes(token):
    q = readQuery("introspection", token)
    response = await q(variables={}, token=token)
    # print(response)
    data = response["data"]
    # print(data)
    __schema = data["__schema"]
    typelist = __schema["types"]
    index = {}
    for type in typelist:
        (kind, name) = (type.get(key, None) for key in ["kind", "name"])
        if name.startswith("_"):
            continue
        if kind != "OBJECT":
            continue
        index[name] = type
    return index

async def main(username="john.newbie@world.com", password="john.newbie@world.com"):
    token = await getToken(username, password)
    index = await listtypes(token)
    for name, t in index.items():
        printType(t)

asyncio.run(main())
    