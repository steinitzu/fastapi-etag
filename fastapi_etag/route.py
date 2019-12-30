from typing import Callable, Union, Dict, Awaitable, Optional
from inspect import iscoroutinefunction

from starlette.requests import Request
from starlette.responses import Response
from fastapi.routing import APIRoute

EtagGen = Callable[[Request], Union[Optional[str], Awaitable[Optional[str]]]]


class Registry:
    path_config: Dict[Callable, EtagGen]

    def __init__(self):
        self.path_config = dict()

    def add(self, etag_gen: EtagGen, weak=True):
        def decorator(func):
            self.path_config[func] = etag_gen, weak
            return func

        return decorator

    def get(self, key: Callable):
        return self.path_config.get(key)


class BaseEtagRoute(APIRoute):
    registry: Registry

    def get_route_handler(self):
        orig_handler = super().get_route_handler()

        async def custom_handler(request: Request):
            settings = self.registry.get(self.endpoint)
            etag_func, weak = settings
            if not etag_func:
                return await orig_handler(request)
            etag = (
                await etag_func(request)
                if iscoroutinefunction(etag_func)
                else etag_func(request)
            )
            if etag and weak:
                etag = f'W/"{etag}"'
            modified = self.is_modified(etag, request)
            if modified:
                resp = await orig_handler(request)
            else:
                resp = Response("", 304)
            if etag:
                resp.headers["etag"] = etag
            return resp

        return custom_handler

    def is_modified(self, etag, request: Request):
        if not etag:
            return True
        client_etag = request.headers.get("if-none-match")
        return not client_etag or etag != client_etag

    @classmethod
    def add(cls, etag_gen: EtagGen, weak=True):
        return cls.registry.add(etag_gen, weak=weak)


def make_route_class(registry: Registry = None):
    class EtagRoute(BaseEtagRoute):
        pass

    EtagRoute.registry = registry or Registry()

    return EtagRoute
