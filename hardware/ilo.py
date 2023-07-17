from . import *

logger = logging.getLogger(__name__)
import subprocess
import shlex
import requests
import json
from requests.packages import urllib3
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class iLO4(Device):
    def __init__(self, address, password, username="Administrator"):
        super().__init__(address=address, password=password, username=username)
        self.base_path = f"https://{self._address}/redfish/v1/"
        self.base_cmd = f"sshpass -p {self._password} ssh -o StrictHostKeychecking=no {self._username}@{self._address} -o PubKeyAcceptedKeyTypes=+ssh-rsa -o HostKeyAlgorithms=+ssh-dss -o KexAlgorithms=+diffie-hellman-group14-sha1"
        self._fan_count = None

    def close(self):
        for fan in range(self._fan_count):
            self.ssh_cmd(f"fan p {fan} unlock")

    def redfish_cmd(self, path):
        response = requests.get(
            f"{self.base_path}{path}",
            verify=False,
            auth=(self._username, self._password),
        )
        return json.loads(response.content)

    def ssh_cmd(self, command):
        full_cmd = f"{self.base_cmd} {command}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=5)
        value = value.stdout.decode("utf-8")
        return value

    def get_fan_count(self):
        fans = self.redfish_cmd("chassis/1/Thermal")["Fans"]
        self._fan_count = len(fans)
        return self._fan_count

    def get_temp(self, core=None):
        cpu_temps = list()
        temperatures = self.redfish_cmd("chassis/1/Thermal")["Temperatures"]
        for t in temperatures:
            if t["Name"].find("CPU") != -1:
                cpu_temps.append(int(t["CurrentReading"]))
        if core is None:
            self._temp = int(np.mean(cpu_temps))
        else:
            self._temp = cpu_temps[core]
        return self._temp

    def set_speed(self, speed):
        self._speed = speed
        if self._fan_count is None:
            self.get_fan_count()
        pwm = (self._speed / 100) * 255
        for fan in range(self._fan_count):
            self.ssh_cmd(f"fan p {fan} lock {pwm}")


def test():
    i = iLO4(address="10.1.4.50", username="Administrator", password=my_secret_ilo_password)
    print(i.get_temp())
    i.set_speed(60)
    i.close()


if __name__ == "__main__":
    test()
