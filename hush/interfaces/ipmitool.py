import logging

logger = logging.getLogger(__name__)
from hush.interfaces import cli


class IpmiTool(cli.Cli):
    def __init__(self, hostname: str, username: str, password: str):
        super().__init__()
        self._hostname: str = hostname
        self._username: str = username
        self._password: str = password
        self.base_command = f"ipmitool -I lanplus -H {self._hostname} -U {self._username} -P {self._password}"

    async def execute(self, command: str) -> cli.Result:
        command = f"{self.base_command} {command}"
        result = await super().execute(command)
        if result.return_code != 0:
            logger.error(f"{self._hostname} failed to run_cmd {command}")
            raise Exception
        return result
