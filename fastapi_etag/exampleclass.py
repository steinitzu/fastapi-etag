from fastapi import FastAPI
from starlette.requests import Request

from fastapi_etag import make_route_class


EtagRoute = make_route_class()

app = FastAPI()
app.router.route_class = EtagRoute


async def get_hello_etag(request: Request):
    name = request.path_params.get("name")
    if not name:
        return None
    return f"etagfor{name}"


@app.get("/hello/{name}")
@EtagRoute.add(get_hello_etag)
def hello(name: str):
    return {"hello": name}
