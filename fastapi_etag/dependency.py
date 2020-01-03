from typing import Optional

from fastapi import HTTPException, FastAPI
from starlette.requests import Request
from starlette.responses import Response
from inspect import iscoroutinefunction

from fastapi_etag.types import EtagGen


class CacheHit(HTTPException):
    pass


class Etag:
    def __init__(self, etag_gen: EtagGen, weak=True):
        self.etag_gen = etag_gen
        self.weak = weak

    def is_modified(self, etag: Optional[str], request: Request):
        if not etag:
            return True
        client_etag = request.headers.get("if-none-match")
        return not client_etag or etag != client_etag

    async def __call__(self, request: Request, response: Response) -> Optional[str]:
        etag = (
            await self.etag_gen(request)  # type: ignore
            if iscoroutinefunction(self.etag_gen)
            else self.etag_gen(request)
        )
        if etag and self.weak:
            etag = f'W/"{etag}"'
        modified = self.is_modified(etag, request)
        if etag:
            headers = {"etag": etag}
        if not modified:
            raise CacheHit(304, headers=headers)
        response.headers.update(headers)
        return etag


async def etag_exception_handler(request: Request, exc: CacheHit):
    return Response("", 304, headers=exc.headers)


def add_exception_handler(app: FastAPI):
    app.add_exception_handler(CacheHit, etag_exception_handler)
