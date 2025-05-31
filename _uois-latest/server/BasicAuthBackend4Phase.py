import os
from typing import Any
from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, AuthenticationError
)
from starlette.middleware.authentication import AuthenticationMiddleware
import aiohttp
import jwt
import json
import logging

JWTPUBLICKEY = "http://localhost:8000/oauth/publickey"
JWTRESOLVEUSERPATH = "http://localhost:8000/oauth/userinfo"

class BasicAuthBackend4Phase(AuthenticationBackend):
    def __init__(self, 
        JWTPUBLICKEY = JWTPUBLICKEY,
        JWTRESOLVEUSERPATH = JWTRESOLVEUSERPATH
        ) -> None:

        # super().__init__()
        self.publickey = None
        self.JWTPUBLICKEY = JWTPUBLICKEY
        self.JWTRESOLVEUSERPATH = JWTRESOLVEUSERPATH

    async def getPublicKey(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.JWTPUBLICKEY) as resp:
                print(resp.status)
                if resp.status != 200:
                    raise AuthenticationError("Public key not available")

                # publickey = await resp.read()
                publickey = await resp.text()
        self.publickey = publickey.replace('"', '').replace('\\n', '\n')
        print('got key', self.publickey)
        self.publickey = self.publickey.encode()
        return self.publickey

    async def authenticate(self, conn):
        print("# BEGIN #######################################")
        client = conn.client
        headers = conn.headers
        cookies = conn.cookies
        url = conn.url
        base_url = conn.base_url
        uri = url.path
        conn.url.path
        logging.debug(f'{base_url} {client}, {headers}, {cookies}')
        logging.debug(f'{uri}')
        print(f'{base_url} {client}, {headers}, {cookies}')
        print(f'{uri}')        
        
        # 1. ziskat jwt (cookies authorization nebo header Authorization: Bearer )
        jwtsource = cookies.get("authorization", None)
        if jwtsource is None:
            jwtsource = headers.get("Authorization", None)
            if jwtsource is not None:
                [_, jwtsource] = jwtsource.split("Bearer ")
            else:
                #unathorized
                pass

        print('got jwtsource', jwtsource)
        if jwtsource is None:
            raise AuthenticationError("missing code")

        # 2. ziskat verejny klic (async request to authority)
        publickey = self.publickey
        if publickey is None:
            publickey = await self.getPublicKey()
        
        # 3. overit jwt (lokalne)
        for i in range(2):
            try:
                jwtdecoded = jwt.decode(jwt=jwtsource, key=publickey, algorithms=["RS256"])
                break
            except jwt.InvalidSignatureError as e:
                # je mozne ulozit key do cache a pri chybe si key ziskat (obnovit) a provest revalidaci
                print(e)
            if (i == 1):
                # klic byl aktualizovan a presto doslo k vyjimce
                raise AuthenticationError("Invalid signature")
            
            # aktualizace klice, predchozi selhal
            publickey = await self.getPublicKey()
            print('publickey refreshed', publickey)
        
        print('got jwtdecoded', jwtdecoded)

        # 3A. pokud jwt obsahuje user.id, vzit jej primo
        user_id = jwtdecoded.get("user_id", None)
        print("some user?", user_id)
        userinfo = {"id": user_id}
        # 4. pouzit jwt jako parametr pro identifikaci uzivatele u autority
        # pro potvrzeni, ze token neni zneplatnen se zeptame na user_id
        # if user_id is None:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {jwtdecoded['access_token']}"}
            async with session.get(self.JWTRESOLVEUSERPATH, headers=headers) as resp:
                print(resp.status)
                assert resp.status == 200, "status not 200, token not valid, probably invalidated"
                userinfo = await resp.json()
                print("got userinfo", userinfo)
                user_id = userinfo["user"]["id"]

        logging.debug(f"We know that user is {user_id}")

        if user_id is None:
            raise AuthenticationError(f"Unknown user")
            
        print("# SUCCESS #######################################")
        return AuthCredentials(["authenticated"]), userinfo