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
                    name=f"{sanitized_name}_thread", args=(name, config), target=self._thread
                )
                self._fms[name]["thread"].start()

    def _thread(self, name, config):
        self._fms[name]["machine"].configure(config)
        self._fms[name]["machine"].run()

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
        self._cpu_sensor_type = None
        self._drive_sensor_type = None
        self._gpu_sensor_type = None
        self._sensors = None
        self._curve = None
        self._last_run_time = dt.now()
        self._status = None
        self._speed = None
        self._int_speed = None
        self._measurements = AdDict()
        self._oob_address = ""
        self._oob_password = ""
        self._oob_username = ""
        self._os_address = ""
        self._os_password = ""
        self._os_username = ""
        self._sensor_names = ["cpu", "drive", "gpu"]
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
            self._sensors = [self.cpu_sensor, self.drive_sensor, self.gpu_sensor]
            cpu_curve = Curve(
                speeds=list(self._config["algo"]["cpu"]["curve"]["speed"].values()),
                temps=list(self._config["algo"]["cpu"]["curve"]["temp"].values()),
            )
            drive_curve = Curve(
                speeds=list(self._config["algo"]["drive"]["curve"]["speed"].values()),
                temps=list(self._config["algo"]["drive"]["curve"]["temp"].values()),
            )
            gpu_curve = Curve(
                speeds=list(self._config["algo"]["gpu"]["curve"]["speed"].values()),
                temps=list(self._config["algo"]["gpu"]["curve"]["temp"].values()),
            )
            self._curve = [cpu_curve, drive_curve, gpu_curve]
            self._store_credentials()
            try:
                self._calc()
            except Exception as e:
                self._status = False
                logger.error(f"Connection to {self._name} failed!")
                logger.error(f"{self._name}'s config={self._config}!")
                logger.exception(e)
            self._last_run_time = dt.now()

    def _calc(self):
        highest_speed = None
        current_speed = None
        final_speed = None
        for s, c, n in zip(self._sensors, self._curve, self._sensor_names):
            if s is not None:
                meas_temp = s.get_temp()
                self._measurements[n] = meas_temp
                if self._config["algo"][n].get("type", "curve") == "pid":
                    self._config_pid(n)
                    speed = round(-1 * self._pids[n](meas_temp))
                else:
                    speed = c.calc(meas_temp)
                logger.debug(f"adjust={speed} values={c.speeds}")
                if speed is not None:
                    if isinstance(speed, str) is True:
                        current_speed = c.speeds.index(speed)
                    else:
                        current_speed = speed
                    if highest_speed is None or current_speed > highest_speed:
                        highest_speed = current_speed
                        if isinstance(speed, str) is True:
                            final_speed = c.speeds[highest_speed]
                        else:
                            final_speed = highest_speed
        if final_speed is not None:
            self._speed = final_speed
            self._int_speed = highest_speed
            logger.info(f"Temperature={meas_temp} -> Fan Speed={self._speed}")
            self.speed_ctrl.set_speed(self._speed)
            self._status = True
        self._report()

    def _report(self):
        self._monitor_tab.update_field(self._name, "time", self._last_run_time)
        self._monitor_tab.update_field(self._name, "cpu_temp", self._measurements["cpu"])
        self._monitor_tab.update_field(self._name, "drive_temp", self._measurements["drive"])
        self._monitor_tab.update_field(self._name, "gpu_temp", self._measurements["gpu"])
        self._monitor_tab.update_field(self._name, "speed", self._int_speed)
        self._monitor_tab.update_field(self._name, "status", self._status)

    def close(self):
        if self.speed_ctrl is not None:
            try:
                self.speed_ctrl.close()
            except:
                pass
        if self.cpu_sensor is not None:
            try:
                self.cpu_sensor.close()
            except:
                pass
        if self.drive_sensor is not None:
            try:
                self.drive_sensor.close()
            except:
                pass
        if self.gpu_sensor is not None:
            try:
                self.gpu_sensor.close()
            except:
                pass

    def _store_credentials(self):
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
            "Dell iDRAC 7": {"class": idrac.Ipmi, "prefix": "oob", "pid_output_limits": (-100, -5)},
            "Dell iDRAC 8": {"class": idrac.Ipmi, "prefix": "oob", "pid_output_limits": (-100, -5)},
            "Dell iDRAC 9": {"class": idrac.Redfish, "prefix": "oob", "pid_output_limits": (-5, 0)},
            "HP iLO 4": {"class": ilo.iLO4, "prefix": "oob", "pid_output_limits": (-100, -5)},
            "Supermicro X9": {"class": sm.X9, "prefix": "oob", "pid_output_limits": (-100, -5)},
            "Supermicro X10": {"class": sm.X10, "prefix": "oob", "pid_output_limits": (-100, -5)},
            "Supermicro X11": {"class": sm.X11, "prefix": "oob", "pid_output_limits": (-100, -5)},
            "Cisco M3": {"class": cisco.M3, "prefix": "oob", "pid_output_limits": (-5, 0)},
            "Cisco M4": {"class": cisco.M3, "prefix": "oob", "pid_output_limits": (-5, 0)},
            "Cisco M5": {"class": cisco.M3, "prefix": "oob", "pid_output_limits": (-5, 0)},
        }
        speed = self._config.get("speed", "None")
        if speed == self._speed_ctrl_type and self.have_credentials_changed is False:
            return self._speed_ctrl
        elif speed == "None":
            self._speed_ctrl = None
        else:
            self._speed_ctrl = class_map[speed]["class"](
                address=self._config[f"{class_map[speed]['prefix']}_address"],
                password=self._config[f"{class_map[speed]['prefix']}_password"],
                username=self._config[f"{class_map[speed]['prefix']}_username"],
            )
            for sensor in self._sensor_names:
                self._pids[sensor] = PID(
                    self._config["algo"][sensor]["pid"].get("kp", 5),
                    self._config["algo"][sensor]["pid"].get("ki", 0.01),
                    self._config["algo"][sensor]["pid"].get("kd", 0.1),
                    setpoint=self._config["algo"][sensor]["pid"].get("target", 40),
                )
                self._pids[sensor].output_limits = class_map[speed]["pid_output_limits"]
        self._speed_ctrl_type = speed
        return self._speed_ctrl

    @property
    def cpu_sensor(self):
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
        cpu_sensor = self._config.get("cpu", "None")
        if cpu_sensor == self._cpu_sensor_type and self.have_credentials_changed is False:
            return self._cpu_sensor
        elif cpu_sensor == "None":
            self._cpu_sensor = None
        else:
            self._cpu_sensor = class_map[cpu_sensor]["class"](
                address=self._config[f"{class_map[cpu_sensor]['prefix']}_address"],
                password=self._config[f"{class_map[cpu_sensor]['prefix']}_password"],
                username=self._config[f"{class_map[cpu_sensor]['prefix']}_username"],
            )
        self._cpu_sensor_type = cpu_sensor
        return self._cpu_sensor

    @property
    def drive_sensor(self):
        class_map = {
            "SMART": {"class": smart.Smart, "prefix": "os"},
        }
        drive_sensor = self._config.get("drive", "None")
        if drive_sensor == self._drive_sensor_type and self.have_credentials_changed is False:
            return self._drive_sensor
        elif drive_sensor == "None":
            self._drive_sensor = None
        else:
            self._drive_sensor = class_map[drive_sensor]["class"](
                address=self._config[f"{class_map[drive_sensor]['prefix']}_address"],
                password=self._config[f"{class_map[drive_sensor]['prefix']}_password"],
                username=self._config[f"{class_map[drive_sensor]['prefix']}_username"],
            )
        return self._drive_sensor

    @property
    def gpu_sensor(self):
        class_map = {
            "Nvidia": {"class": gpu.Nvidia, "prefix": "os"},
        }
        gpu_sensor = self._config.get("gpu", "None")
        if gpu_sensor == self._gpu_sensor_type:
            return self._gpu_sensor
        elif gpu_sensor == "None":
            self._gpu_sensor = None
        else:
            self._gpu_sensor = class_map[gpu_sensor]["class"](
                address=self._config[f"{class_map[gpu_sensor]['prefix']}_address"],
                password=self._config[f"{class_map[gpu_sensor]['prefix']}_password"],
                username=self._config[f"{class_map[gpu_sensor]['prefix']}_username"],
            )
        return self._gpu_sensor


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
