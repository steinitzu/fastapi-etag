from inspect import iscoroutinefunction
from typing import MutableMapping, Optional

from fastapi import FastAPI, HTTPException, Request, Response

from fastapi_etag.types import EtagGen


class CacheHit(HTTPException):
    ...


class Etag:
    def __init__(
        self, etag_gen: EtagGen, weak: bool = True, extra_headers: MutableMapping = None
    ):
        self.etag_gen = etag_gen
        self.weak = weak
        self.extra_headers = extra_headers

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
        headers = dict(self.extra_headers or {})
        if etag:
            if self.weak:
                etag = f'W/"{etag}"'
            headers.update(etag=etag)
            if not self.is_modified(etag, request):
                raise CacheHit(304, headers=headers)
        response.headers.update(headers)
        return etag


async def etag_exception_handler(request: Request, exc: CacheHit):
    return Response(status_code=304, headers=exc.headers)


def add_exception_handler(app: FastAPI):
    app.add_exception_handler(CacheHit, etag_exception_handler)
