import logging

logger = logging.getLogger(__name__)
import threading
from typing import List
import numpy as np
from scipy.interpolate import interp1d
import re
import math
from datetime import datetime as dt
from addict import Dict as AdDict
import hardware.idrac as idrac
import hardware.ilo as ilo
import hardware.supermicro as sm
import hardware.cisco as cisco
import hardware.smart as smart
import hardware.gpu as gpu
from tabs import configs
from simple_pid import PID


class Launcher:
    def __init__(self, monitor_tab) -> None:
        self._monitor_tab = monitor_tab
        self._fms = AdDict()

    def run(self):
        for name, config in configs.items():
            if name not in self._fms:
                self._fms[name]["machine"] = Machine(name=name, monitor_tab=self._monitor_tab)
                self._fms[name]["thread"] = threading.Thread()
            if self._fms[name]["thread"].is_alive() is False:
                sanitized_name = re.sub(r"\s+", "", name, flags=re.UNICODE)
                self._fms[name]["thread"] = threading.Thread(
                    name=f"{sanitized_name}_thread", args=(name, config), target=self.thread
                )
                self._fms[name]["thread"].start()

    def thread(self, name, config):
        self._fms[name]["machine"].configure(config)
        self._fms[name]["machine"].run()
        self._fms[name]["machine"].report()

    def close(self):
        logger.warning("Launcher shutdown initiated.")
        for fm in self._fms:
            try:
                fm["machine"].close()
            except:
                pass


class Machine:
    def __init__(self, name, monitor_tab) -> None:
        self._name = name
        self._monitor_tab = monitor_tab
        self._config = None
        self._speed_ctrl_type = None
        self._cpu_temp_type = None
        self._drive_temp_type = None
        self._gpu_temp_type = None
        self._speed_ctrl_type = None
        self._cpu_temp_type = None
        self._drive_temp_type = None
        self._gpu_temp_type = None
        self._temps = None
        self._curves = None
        self._last_run_time = dt.now()
        self._status = None
        self._speed = None
        self._int_speed = None
        self._meas_temp_list = None
        self._measurements = AdDict()
        self._oob_address = ""
        self._oob_password = ""
        self._oob_username = ""
        self._os_address = ""
        self._os_password = ""
        self._os_username = ""
        self._pids = dict()
        self._pids["cpu"] = PID(5, 0.01, 0.1, setpoint=40)
        self._pids["drive"] = PID(5, 0.01, 0.1, setpoint=40)
        self._pids["gpu"] = PID(5, 0.01, 0.1, setpoint=40)

    def configure(self, config):
        self._config = config

    def run(self):
        elapsed_time = dt.now() - self._last_run_time
        rate = self._config.get("rate", 10)
        if rate is not None and rate > 0 and elapsed_time.seconds >= rate:
            self._temps = [self.cpu_temp, self.drive_temp, self.gpu_temp]
            cpu_curve = Curve(
                speeds=list(self._config["algo"]["curves"]["cpu"]["speed"].values()),
                temps=list(self._config["algo"]["curves"]["cpu"]["temp"].values()),
            )
            drive_curve = Curve(
                speeds=list(self._config["algo"]["curves"]["drive"]["speed"].values()),
                temps=list(self._config["algo"]["curves"]["drive"]["temp"].values()),
            )
            gpu_curve = Curve(
                speeds=list(self._config["algo"]["curves"]["gpu"]["speed"].values()),
                temps=list(self._config["algo"]["curves"]["gpu"]["temp"].values()),
            )
                if self._config["algo"][n].get("type", "curve") == "pid":
                    self._config_pid(n)
                    speed = round(-1 * self._pids[n](meas_temp))
                else:
                    speed = c.calc(meas_temp)

    def report(self):
        self._monitor_tab.update_field(self._name, "time", self._last_run_time)
        self._monitor_tab.update_field(self._name, "cpu_temp", self._measurements["cpu_temp"])
        self._monitor_tab.update_field(self._name, "drive_temp", self._measurements["drive_temp"])
        self._monitor_tab.update_field(self._name, "gpu_temp", self._measurements["gpu_temp"])
        self._monitor_tab.update_field(self._name, "speed", self._int_speed)
        self._monitor_tab.update_field(self._name, "status", self._status)

    def close(self):
        if self.speed_ctrl is not None:
            try:
                self.speed_ctrl.close()
            except:
                pass
        if self.cpu_temp is not None:
            try:
                self.cpu_temp.close()
            except:
                pass
        if self.drive_temp is not None:
            try:
                self.drive_temp.close()
            except:
                pass
        if self.gpu_temp is not None:
            try:
                self.gpu_temp.close()
            except:
                pass

    def store_credentials(self):
        self._oob_address = self._config.get("oob_address", "")
        self._oob_password = self._config.get("oob_password", "")
        self._oob_username = self._config.get("oob_username", "")
        self._os_address = self._config.get("os_address", "")
        self._os_password = self._config.get("os_password", "")
        self._os_username = self._config.get("os_username", "")

    def _config_pid(self, sensor):
        self._pids[sensor].tunings = (
            self._config["algo"][sensor]["pid"].get("kp", 5),
            self._config["algo"][sensor]["pid"].get("ki", 0.01),
            self._config["algo"][sensor]["pid"].get("kd", 0.1),
        )
        self._pids[sensor].setpoint = self._config["algo"][sensor]["pid"].get("target", 40)

    @property
    def have_credentials_changed(self):
        if (
            self._oob_address == self._config.get("oob_address", "")
            and self._oob_password == self._config.get("oob_password", "")
            and self._oob_username == self._config.get("oob_username", "")
            and self._os_address == self._config.get("os_address", "")
            and self._os_password == self._config.get("os_password", "")
            and self._os_username == self._config.get("os_username", "")
        ):
            return False
        return True

    @property
    def speed_ctrl(self):
        class_map = {
            "Dell iDRAC 7": {"class": idrac.Ipmi, "prefix": "oob"},
            "Dell iDRAC 8": {"class": idrac.Ipmi, "prefix": "oob"},
            "Dell iDRAC 9": {"class": idrac.Redfish, "prefix": "oob"},
            "HP iLO 4": {"class": ilo.iLO4, "prefix": "oob"},
            "Supermicro X9": {"class": sm.X9, "prefix": "oob"},
            "Supermicro X10": {"class": sm.X10, "prefix": "oob"},
            "Supermicro X11": {"class": sm.X11, "prefix": "oob"},
            "Cisco M3": {"class": cisco.M3, "prefix": "oob"},
            "Cisco M4": {"class": cisco.M3, "prefix": "oob"},
            "Cisco M5": {"class": cisco.M3, "prefix": "oob"},
        }
        speed_ctrl_type = self._config.get("speed_ctrl_type", "None")
        if speed_ctrl_type == self._speed_ctrl_type and self.have_credentials_changed is False:
            return self._speed_ctrl
        elif speed_ctrl_type == "None":
            self._speed_ctrl = None
        else:
            self._speed_ctrl = class_map[speed_ctrl_type]["class"](
                address=self._config[f"{class_map[speed_ctrl_type]['prefix']}_address"],
                password=self._config[f"{class_map[speed_ctrl_type]['prefix']}_password"],
                username=self._config[f"{class_map[speed_ctrl_type]['prefix']}_username"],
            )
        self._speed_ctrl_type = speed_ctrl_type
        return self._speed_ctrl

    @property
    def cpu_temp(self):
        class_map = {
            "Dell iDRAC 7": {"class": idrac.Ipmi, "prefix": "oob"},
            "Dell iDRAC 8": {"class": idrac.Ipmi, "prefix": "oob"},
            "Dell iDRAC 9": {"class": idrac.Redfish, "prefix": "oob"},
            "HP iLO 4": {"class": ilo.iLO4, "prefix": "oob"},
            "Supermicro X9": {"class": sm.X9, "prefix": "oob"},
            "Supermicro X10": {"class": sm.X10, "prefix": "oob"},
            "Supermicro X11": {"class": sm.X11, "prefix": "oob"},
            "Cisco M3": {"class": cisco.M3, "prefix": "oob"},
            "Cisco M4": {"class": cisco.M3, "prefix": "oob"},
            "Cisco M5": {"class": cisco.M3, "prefix": "oob"},
        }
        cpu_temp_type = self._config.get("cpu_temp_type", "None")
        if cpu_temp_type == self._cpu_temp_type and self.have_credentials_changed is False:
            return self._cpu_temp
        elif cpu_temp_type == "None":
            self._cpu_temp = None
        else:
            self._cpu_temp = class_map[cpu_temp_type]["class"](
                address=self._config[f"{class_map[cpu_temp_type]['prefix']}_address"],
                password=self._config[f"{class_map[cpu_temp_type]['prefix']}_password"],
                username=self._config[f"{class_map[cpu_temp_type]['prefix']}_username"],
            )
        self._cpu_temp_type = cpu_temp_type
        return self._cpu_temp

    @property
    def drive_temp(self):
        class_map = {
            "SMART": {"class": smart.Smart, "prefix": "os"},
        }
        drive_temp_type = self._config.get("drive_temp_type", "None")
        if drive_temp_type == self._drive_temp_type and self.have_credentials_changed is False:
            return self._drive_temp
        elif drive_temp_type == "None":
            self._drive_temp = None
        else:
            self._drive_temp = class_map[drive_temp_type]["class"](
                address=self._config[f"{class_map[drive_temp_type]['prefix']}_address"],
                password=self._config[f"{class_map[drive_temp_type]['prefix']}_password"],
                username=self._config[f"{class_map[drive_temp_type]['prefix']}_username"],
            )
        return self._drive_temp

    @property
    def gpu_temp(self):
        class_map = {
            "Nvidia": {"class": gpu.Nvidia, "prefix": "os"},
        }
        gpu_temp_type = self._config.get("gpu_temp_type", "None")
        if gpu_temp_type == self._gpu_temp_type:
            return self._gpu_temp
        elif gpu_temp_type == "None":
            self._gpu_temp = None
        else:
            self._gpu_temp = class_map[gpu_temp_type]["class"](
                address=self._config[f"{class_map[gpu_temp_type]['prefix']}_address"],
                password=self._config[f"{class_map[gpu_temp_type]['prefix']}_password"],
                username=self._config[f"{class_map[gpu_temp_type]['prefix']}_username"],
            )
        return self._gpu_temp


class Curve:
    def __init__(self, speeds, temps):
        self._speeds = speeds
        self._temps = temps

    def calc(self, temp):
        value = None
        if (
            isinstance(self._speeds, List) is True
            and isinstance(self._temps, List) is True
            and len(self._speeds) == len(self._temps)
        ):
            if isinstance(self._speeds[0], int) is True:
                value = self.temp2pwm(temp)
            else:
                value = self.temp2value(temp)
        return value

    def temp2value(self, temp):
        set_value = None
        temp_count = len(self._temps)
        value_count = len(self._speeds)
        if temp_count < 2 or value_count < 2:
            set_value = self._speeds[0]
        if temp <= self._temps[0]:
            set_value = self._speeds[0]
        elif temp > self._temps[-1]:
            set_value = self._speeds[-1]
        else:
            for s, t in zip(self._speeds, self._temps):
                if temp > t:
                    set_value = s
                logger.info(f"temp={t} speed={s} set_value={set_value}")
        return set_value

    def temp2pwm(self, temp):
        temps = self._temps
        temps.insert(0, 1)
        temps.append(120)
        pwms = self._speeds
        pwms.insert(0, self._speeds[0])
        pwms.append(self._speeds[-1])
        pwm_interp = interp1d(temps, pwms)
        temp_range = np.arange(min(temps), max(temps), 1)
        pwm = math.ceil(pwm_interp(temp_range)[temp - 1])
        return pwm

    @property
    def speeds(self):
        return self._speeds

    @property
    def temps(self):
        return self._temps
