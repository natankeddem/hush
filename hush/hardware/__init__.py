import logging

logger = logging.getLogger(__name__)
from typing import Optional, Union
from hush.interfaces import http, ssh, ipmitool
from hush import storage


class Device:
    def __init__(self, host: str) -> None:
        self.host: str = host
        self.hostname: str = ""
        self.username: str = ""
        self.password: Optional[str] = None
        self._temp: Optional[int] = None
        self._speed: Optional[Union[str, int]] = None
        self._ssh: Optional[ssh.Ssh] = None
        self._ipmitool: Optional[ipmitool.IpmiTool] = None
        self._json_request: Optional[http.Json] = None
        self._xml_request: Optional[http.Xml] = None

    async def close(self) -> None:
        logger.info(f"The close method is not implemented. {self}")

    async def get_temp(self) -> Optional[int]:
        logger.info(f"The get_temp method is not implemented. {self}")
        return None

    async def set_speed(self, speed) -> None:
        logger.info(f"The set_speed method is not implemented. {self}")
        self._speed = speed

    def get_os_credentials(self) -> None:
        self.password = storage.host(self.host)["os"]["password"]
        # self.use_key = storage.host(self.host)["os"]["use_key"]

    def get_oob_credentials(self) -> None:
        self.hostname = storage.host(self.host)["oob"]["hostname"]
        self.username = storage.host(self.host)["oob"]["username"]
        self.password = storage.host(self.host)["oob"]["password"]

    @property
    def ssh(self) -> ssh.Ssh:
        if self._ssh is None:
            self._ssh = ssh.Ssh(
                self.host,
                password=self.password,
            )
        return self._ssh

    @property
    def ipmi(self) -> ipmitool.IpmiTool:
        if self._ipmitool is None:
            self._ipmitool = ipmitool.IpmiTool(self.hostname, self.username, "" if self.password is None else self.password)
        return self._ipmitool

    @property
    def json_request(self) -> http.Json:
        if self._json_request is None:
            self._json_request = http.Json(self.hostname, self.username, self.password)
        return self._json_request

    @property
    def xml_request(self) -> http.Xml:
        if self._xml_request is None:
            self._xml_request = http.Xml(self.hostname, self.username, self.password)
        return self._xml_request
