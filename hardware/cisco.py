from . import *

logger = logging.getLogger(__name__)
import xmltodict
import numpy as np
from enum import IntEnum
import requests
from datetime import datetime as dt
import time
from requests.packages import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/c/sw/api/4_3/b-cisco-imc-xml-api-43.pdf


class M3:
    class Fan_Policy(IntEnum):
        LOWPOWER = 0
        BALANCED = 1
        PERFORMANCE = 2
        HIGHPOWER = 3
        MAXIMUMPOWER = 4

    def __init__(self, address, password, username="admin"):
        self._address = address
        self._password = password
        self._username = username
        self._temp = None
        self._adjust = None
        self._base_path = f"https://{self._address}/nuova"
        self._last_cmd = None
        self._last_response = None
        self._cookie = None
        self._cookie_time = None
        self._cookie_timeout = None

    def close(self):
        cmd = f"<aaaLogout inCookie='{self.cookie}'></aaaLogout>"
        self.xml_cmd(cmd)

    def xml_cmd(self, cmd, timeout=10):
        self._last_cmd = cmd
        print(f"last cmd = {self._last_cmd}")
        self._last_response = requests.post(self._base_path, data=cmd, verify=False, timeout=timeout).text
        print(f"last resp = {self._last_response}")
        response = xmltodict.parse(self._last_response)
        return response

    def set_speed(self, speed):
        self._speed = speed
        if isinstance(speed, str) is True:
            policys = {
                "LowPower": self.Fan_Policy.LOWPOWER,
                "Balanced": self.Fan_Policy.BALANCED,
                "Performance": self.Fan_Policy.PERFORMANCE,
                "HighPower": self.Fan_Policy.HIGHPOWER,
                "MaxPower": self.Fan_Policy.MAXIMUMPOWER,
            }
            policy = policys[speed]
        elif isinstance(speed, IntEnum) is True:
            policy = speed
        elif isinstance(speed, int) is True:
            if speed < 25:
                policy = self.Fan_Policy.LOWPOWER
            elif speed < 50:
                policy = self.Fan_Policy.BALANCED
            elif speed < 75:
                policy = self.Fan_Policy.PERFORMANCE
            elif speed < 100:
                policy = self.Fan_Policy.HIGHPOWER
            else:
                policy = self.Fan_Policy.MAXIMUMPOWER
        else:
            policy = speed
        policys = {
            self.Fan_Policy.LOWPOWER: "Low Power",
            self.Fan_Policy.BALANCED: "Balanced",
            self.Fan_Policy.PERFORMANCE: "Performance",
            self.Fan_Policy.HIGHPOWER: "High Power",
            self.Fan_Policy.MAXIMUMPOWER: "Maximum Power",
        }
        cmd = f"<configConfMo cookie='{self.cookie}' inHierarchical='false' dn='sys/rack-unit-1/board/fan-policy'><inConfig><fanPolicy configuredFanPolicy='{policys[policy]}' dn='sys/rack-unit-1/board/fan-policy'></fanPolicy></inConfig></configConfMo>"
        try:
            response = self.xml_cmd(cmd)
            status = response["configConfMo"]["outConfig"]["fanPolicy"]["@configurationStatus"]
            if status != "SUCCESS":
                raise Exception
        except Exception as e:
            print(f"{self._address} failed to set fan policy")
            print(f"cmd = {self._last_cmd}")
            print(f"response = {self._last_response}")
            raise e

    def get_temp(self, core=None):
        try:
            cmd = f"<configResolveClass cookie='{self.cookie}' inHierarchical='false' classId='processorEnvStats'></configResolveClass>"
            response = self.xml_cmd(cmd)
            cpus = response["configResolveClass"]["outConfigs"]["processorEnvStats"]
            cpu_temps = list()
            for cpu in cpus:
                cpu_temps.append(float(cpu["@temperature"]))
            if core is None:
                self._temp = int(np.mean(cpu_temps))
            else:
                self._temp = cpu_temps[core]
        except Exception as e:
            print(f"{self._address} failed to get cpu temp")
            print(f"cmd = {self._last_cmd}")
            print(f"response = {self._last_response}")
            raise e

    @property
    def cookie(self):
        try:
            elapsed_time = None
            if self._cookie_time is not None:
                elapsed_time = dt.now() - self._cookie_time
            if self._cookie is None or elapsed_time.seconds > (self._cookie_timeout - 10):
                self._cookie_time = dt.now()
                cmd = f"<aaaLogin inName='{self._username}' inPassword='{self._password}'></aaaLogin>"
                response = self.xml_cmd(cmd)
                self._cookie = response["aaaLogin"]["@outCookie"]
                self._cookie_timeout = int(response["aaaLogin"]["@outRefreshPeriod"])
            return self._cookie
        except Exception as e:
            print(f"{self._address} failed to get cookie")
            print(f"cmd = {self._last_cmd}")
            print(f"response = {self._last_response}")
            raise e


def test():
    m = M3(address="10.0.2.25", password="password", username="admin2")
    # print(m.get_temp())
    policies = [
        m.Fan_Policy.LOWPOWER,
        m.Fan_Policy.BALANCED,
        m.Fan_Policy.PERFORMANCE,
        m.Fan_Policy.HIGHPOWER,
        m.Fan_Policy.MAXIMUMPOWER,
    ]
    for policy in policies:
        m.set_speed(policy)
        time.sleep(30)
    m.set_speed(m.Fan_Policy.LOWPOWER)
    m.close()


if __name__ == "__main__":
    test()
