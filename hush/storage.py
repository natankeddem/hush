import logging

logger = logging.getLogger(__name__)
from typing import Dict, Literal
from nicegui import app

configs_version = int(102)
configs_version_string = f"config_{configs_version}"
hosts = app.storage.general.get(configs_version_string, None)
if hosts is None:
    logger.warning(f"Storage version not found, updating version to {configs_version}.")
    logger.warning(f"Connections cleared, repeat setup procedure.")
    app.storage.general[configs_version_string] = {}
hosts = app.storage.general[configs_version_string]

for h in hosts:
    if "cpu" in hosts[h]:
        if hosts[h]["cpu"] == "HP iLO 4":
            hosts[h]["cpu"] = "HP iLO 4 All"
    if "pci" in hosts[h]:
        if hosts[h]["pci"] == "HP iLO 4":
            hosts[h]["pci"] = "HP iLO 4 All"
    if "speed" in hosts[h]:
        if hosts[h]["speed"] == "HP iLO 4":
            hosts[h]["speed"] = "HP iLO 4 All"
    if "drive" in hosts[h]:
        if hosts[h]["drive"] == "SMART":
            hosts[h]["drive"] = "SMART All"
    if "speed" in hosts[h]:
        if hosts[h]["speed"] == "Supermicro X10":
            hosts[h]["speed"] = "Supermicro X10 All"
    if "speed" in hosts[h]:
        if hosts[h]["speed"] == "Supermicro X11":
            hosts[h]["speed"] = "Supermicro X11 All"
    if "ilo4" not in hosts[h]:
        hosts[h]["ilo4"] = {}
    if "smart" not in hosts[h]:
        hosts[h]["smart"] = {}
    if "chassis" not in hosts[h]:
        hosts[h]["chassis"] = "None"
    if "shared" not in hosts[h]:
        hosts[h]["shared"] = {}
    if "supermicro" not in hosts[h]:
        hosts[h]["supermicro"] = {}
    if "idrac" not in hosts[h]:
        hosts[h]["idrac"] = {}


def host(name: str) -> dict:
    if name not in hosts:
        hosts[name] = {
            "oob": {
                "hostname": "",
                "username": "",
                "password": "",
            },
            "os": {
                "password": None,
            },
            "mqtt": {
                "hostname": "",
                "username": "",
                "password": "",
            },
            "cpu": "None",
            "pci": "None",
            "speed": "None",
            "drive": "None",
            "gpu": "None",
            "chassis": "None",
            "delay": 30,
            "algo": {},
            "ilo4": {},
            "smart": {},
            "idrac": {},
            "shared": {},
        }
    return hosts[name]


def algo(host_name: str) -> dict:
    h = host(host_name)
    if "algo" not in h:
        h["algo"] = {}
    return h["algo"]


def algo_sensor(host_name: str, sensor: str) -> dict:
    a = algo(host_name)
    if sensor not in a:
        a[sensor] = {}
    if "type" not in a[sensor]:
        a[sensor]["type"] = "curve"
    return a[sensor]


def curve(host_name: str, sensor: str) -> dict:
    s = algo_sensor(host_name, sensor)
    if "curve" not in s:
        s["curve"] = {}
    return s["curve"]


def curve_speed(host_name: str, sensor: str, default=None) -> dict:
    c = curve(host_name, sensor)
    if "speed" not in c:
        if default is None:
            c["speed"] = {
                "Min": None,
                "Low": None,
                "Medium": None,
                "High": None,
                "Max": None,
            }
        else:
            c["speed"] = default
    return c["speed"]


def curve_temp(host_name: str, sensor: str, default=None) -> dict:
    c = curve(host_name, sensor)
    if "temp" not in c:
        if default is None:
            c["temp"] = {
                "Min": 30,
                "Low": 40,
                "Medium": 50,
                "High": 60,
                "Max": 70,
            }
        else:
            c["temp"] = default
    return c["temp"]


def pid(host_name: str, sensor: str) -> Dict[str, float]:
    s = algo_sensor(host_name, sensor)
    if "pid" not in s:
        s["pid"] = {"Kp": 5, "Ki": 0.01, "Kd": 0.1, "Target": 40}
    return s["pid"]


def pid_coefficient(host_name: str, sensor: str, coefficient: Literal["Kp", "Ki", "Kd", "Target"]) -> float:
    return pid(host_name, sensor)[coefficient]
