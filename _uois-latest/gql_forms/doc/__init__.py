import os
import logging

from fastapi.responses import FileResponse

def attachVoyager(app, path="/voyager"):
    logging.info("attaching voyager")
    
    @app.get(path, response_class=FileResponse)
    async def gql_schema_visualizer():
        realpath = os.path.realpath("./doc/voyager.html")
        return realpath    
    
    return gql_schema_visualizer