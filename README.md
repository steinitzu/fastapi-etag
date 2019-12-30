# fastapi-etag

Basic etag support for FastAPI, allowing you to benefit from conditional caching in web browsers and reverse-proxy caching layers.

This does not generate etags that are a hash of the response content, but instead lets you pass in a custom etag generating function per endpoint that is called before executing the route function.  
This lets you bypass expensive API calls when client includes a matching etag in the `If-None-Match` header, in this case your endpoint is never called, instead returning a 304 response telling the client nothing has changed.

The etag logic is implement using a custom `APIRoute` class that you can add to individual routers or a whole app.  

Here's how you use it:

```python3
# app.py

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

```

Run this example with `uvicorn: uvicorn --port 8090 app:app`

Let's break it down:

```python3
EtagRoute = make_route_class()
```

Here we create a custom etag route class. The class contains a registry of endpoints
that have etag support.
You can create many classes like this within your application if you want separate endpoint registries.

```python3
app.router.route_class = EtagRoute
```
This tells fastapi to use the custom route class on all routes in the app.  
You can alternatively set this on individual routers as well.  

```python3
async def get_hello_etag(request: Request):
    name = request.path_params.get("name")
    return f"etagfor{name}"
```

This is the function that generates the etag for your endpoint.  
It can do anything you want, it could for example return a hash of a last modified timestamp in your database.  
It can be either a normal function or an async function.  
Only requirement is that it accepts one argument (request) and that it returns either a string (the etag) or `None` (in which case no etag header is added)


```python3
@app.get("/hello/{name}")
@EtagRoute.add(get_hello_etag)
def hello(name: str):
	...
```

The decorator adds the "/hello" endpoint to the registry of etag routes and specifies that the `get_hello_etag` should be used to generate etags for it. (no etag logic is added unless you do this)  
Note that by default your etag is converted to a weak etag, that means it is wrapped in `'W/"{your etag}"'`  
If you'd like to use strong etags, you can disable this by passing keyword argument `weak=False` to the decorator.


Now try it with curl:

```
curl -i "http://localhost:8090/hello/bob"
HTTP/1.1 200 OK
date: Mon, 30 Dec 2019 21:55:43 GMT
server: uvicorn
content-length: 15
content-type: application/json
etag: W/"etagforbob"

{"hello":"bob"}
```

Etag header is added

Now including the etag in `If-None-Match` header (mimicking a web browser):

```
curl -i -X GET "http://localhost:8090/hello/bob" -H "If-None-Match: W/\"etagforbob\""
HTTP/1.1 304 Not Modified
date: Mon, 30 Dec 2019 21:57:37 GMT
server: uvicorn
etag: W/"etagforbob"
```

It now returns no content, only the 304 telling us nothing has changed.


# TODO

* Deploy to pypi
* Tests
