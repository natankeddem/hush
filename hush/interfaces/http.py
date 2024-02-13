import logging

logger = logging.getLogger(__name__)
from typing import Any, Dict, Optional
import httpx
import json
import xmltodict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Http:
    def __init__(self, hostname: str, username: str, password: Optional[str] = None):
        self.hostname: str = hostname
        self.username: str = username
        self.password: str = "" if password is None else password
        self.base_path: str = f"https://{self.hostname}/"


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


class Xml(Http):
    async def post(self, data: str, timeout: int = 10) -> Dict[str, Any]:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.base_path,
                content=data,
                timeout=timeout,
                follow_redirects=True,
            )
            return xmltodict.parse(response.text)
