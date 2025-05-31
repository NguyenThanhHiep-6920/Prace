import asyncio
import aiohttp

hostname = "http://host.docker.internal:33001"
async def getToken(username, password):
    keyurl = f"{hostname}/oauth/login3"
    async with aiohttp.ClientSession() as session:
        async with session.get(keyurl) as resp:
            # print(resp.status)
            keyJson = await resp.json()
            # print(keyJson)

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
                    # print(response)
                    return response
    return post

def readQuery(tablename, queryname, token):
    prefix = "./gqls"
    filename = f"{prefix}/{tablename}/{queryname}.gql"
    with open(filename, "r", encoding="utf-8") as fi:
        lines = fi.readlines()
    q = ''.join(lines)
    # print(filename, q)
    f = query(q, token)
    return f

def checkReadResult(tablename, result):
    pass

def checkReadPageResult(tablename, results):
    for result in results:
        checkReadResult(tablename=tablename, result=result)
    pass

def extractResultFromResponse(response):
    errors = response.get("errors", None)
    assert errors is None, f"Got error response {response}"
    data = response.get("data", None)
    assert data is not None, f"Missing data, {response}"
    result = data.get("result", None)
    assert result is not None, f"Missing result in data, {result}"
    return result

async def readTableIds(tablename, token, variables={"skip": 0, "limit": 10}):
    queryFunc = readQuery(tablename=tablename, queryname="readpage", token=token)
    response = await queryFunc(variables=variables, token=token)
    results = extractResultFromResponse(response)
    for result in results:
        print(result)
    return results

async def main(username="john.newbie@world.com", password="john.newbie@world.com"):
    token = await getToken(username, password)
    tablenames = ["users", "groups", "memberships", "roles", "roletypes", "rolecategories"]
    for tablename in tablenames:
        ids = await readTableIds(tablename=tablename, token=token)
    pass

asyncio.run(main())