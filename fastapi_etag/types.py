from typing import Awaitable, Callable, Optional, Union

from starlette.requests import Request

EtagGen = Callable[[Request], Union[Optional[str], Awaitable[Optional[str]]]]
