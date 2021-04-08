import pytest
from fastapi import Depends
from requests import Response
from starlette.requests import Request

from fastapi_etag import add_exception_handler, Etag


EXTRA_HEADERS = {"Cache-Control": "public, max-age=30", "X-Custom-Header": "asdf"}


@pytest.fixture(autouse=True)
def hello_endpoint(app):
    add_exception_handler(app)

    async def get_hello_etag(request: Request):
        return "etagfor" + request.path_params["name"]

    @app.get("/hello/{name}", dependencies=[Depends(Etag(get_hello_etag))])
    async def hello(name: str):
        return {"hello": name}

    @app.get("/no-etag", dependencies=[Depends(Etag(lambda x: None))])
    async def get_missing_etag():
        """
        This endpoint has no stored etag
        """
        return {"a": "b"}

    @app.get(
        "/hello/{name}/extra-headers",
        dependencies=[Depends(Etag(get_hello_etag, extra_headers=EXTRA_HEADERS))],
    )
    async def hello_extra_headers(name: str):
        return {"hello": name}


def test_example_produces_etag(client):
    r: Response = client.get("/hello/foo")
    assert r.status_code == 200
    assert r.headers == {
        "content-length": "15",
        "content-type": "application/json",
        "etag": 'W/"etagforfoo"',
    }
    assert r.json() == {"hello": "foo"}


def test_example_produces_304(client):
    r: Response = client.get("/hello/foo", headers={"If-None-Match": 'W/"etagforfoo"'})
    assert r.status_code == 304
    assert r.headers == {"etag": 'W/"etagforfoo"'}
    assert r.text == ""


def test_example_wrong_etag_produces_200(client):
    r: Response = client.get(
        "/hello/foo", headers={"If-None-Match": "not-the-correct-etag"}
    )
    assert r.status_code == 200
    assert r.headers == {
        "content-length": "15",
        "content-type": "application/json",
        "etag": 'W/"etagforfoo"',
    }
    assert r.json() == {"hello": "foo"}


def test_example_no_etag_produces_200(client):
    r: Response = client.get("/no-etag")
    assert r.status_code == 200
    assert r.headers == {"content-length": "9", "content-type": "application/json"}
    assert r.json() == {"a": "b"}


def test_example_extra_headers_miss_includes_headers(client):
    r: Response = client.get("/hello/foo/extra-headers")
    assert r.status_code == 200
    for key, value in EXTRA_HEADERS.items():
        assert r.headers[key] == value


def test_example_extra_headers_hit_includes_headers(client):
    r: Response = client.get(
        "/hello/foo/extra-headers", headers={"If-None_match": "etagforfoo"}
    )
    assert r.status_code == 200
    for key, value in EXTRA_HEADERS.items():
        assert r.headers[key] == value
