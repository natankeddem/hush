import logging

logger = logging.getLogger(__name__)
from typing import Any, Dict, Optional
import httpx
import json
import xmltodict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Http:
    def __init__(self, hostname: str, username: str, password: Optional[str] = None, secure: bool = True):
        self.hostname: str = hostname
        self.username: str = username
        self.password: str = "" if password is None else password
        self.secure: bool = secure
        self.base_path: str = f"http{'s' if self.secure else ''}://{self.hostname}/"


class Json(Http):
    async def get(self, path: str, timeout: int = 10) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                self.base_path + path,
                auth=(self.username, self.password),
                timeout=timeout,
                follow_redirects=True,
            )
            return response.json()

    async def patch(self, path: str, payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.patch(
                self.base_path + path,
                json=payload,
                headers={"content-type": "application/json"},
                auth=(self.username, self.password),
                timeout=timeout,
                follow_redirects=True,
            )
            return response.json()

    async def post(self, path: str, payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.base_path + path,
                json=payload,
                auth=(self.username, self.password),
                timeout=timeout,
                follow_redirects=True,
            )
            return response.json()


class Xml(Http):
    async def post(self, data: str, timeout: int = 20) -> Dict[str, Any]:
        logger.debug(f"XML Post -> {data}")
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.base_path,
                content=data,
                timeout=timeout,
            )
            logger.debug(f"XML Post <- {response.text}")
            return xmltodict.parse(response.text)
