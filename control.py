import logging

logger = logging.getLogger(__name__)
import threading
from typing import List
import sys
import numpy as np
from scipy.interpolate import interp1d
import math
from datetime import datetime as dt
import hardware.idrac as idrac
import hardware.ilo as ilo
import hardware.supermicro as sm
import hardware.smart as smart
from tabs import configs


class Launcher:
    def __init__(self, monitor_tab) -> None:
        self._monitor_tab = monitor_tab
        self._fms = dict()

    def run(self):
        for name, config in configs.items():
            thread = threading.Thread(name="async_run", args=(name, config), target=self.thread)
            thread.start()

    def thread(self, name, config):
        if name not in self._fms:
            self._fms[name] = Machine(name=name, monitor_tab=self._monitor_tab)

        self._fms[name].configure(config)
        self._fms[name].run()
        self._fms[name].report()

    def close(self):
        for fm in self._fms:
            try:
                fm["instance"].close()
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
        self._meas_temp_list = None

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
            gpu_curve = None
            self._curves = [cpu_curve, drive_curve, gpu_curve]
            int_speed = None
            current_speed = None
            final_speed = None
            meas_temp_list = list()
            try:
                for t, c in dict(zip(self._temps, self._curves)).items():
                    if t is not None:
                        meas_temp = t.get_temp()
                        speed = c.calc(meas_temp)
                        meas_temp_list.append(meas_temp)
                        logger.debug(f"adjust={speed} values={c.speeds}")
                        if speed is not None:
                            if isinstance(speed, str) is True:
                                current_speed = c.speeds.index(speed)
                            else:
                                current_speed = speed
                            if int_speed is None or current_speed > int_speed:
                                int_speed = current_speed
                                if isinstance(speed, str) is True:
                                    final_speed = speed
                                else:
                                    final_speed = current_speed
                if final_speed is not None:
                    self._speed = final_speed
                    logger.info(f"Temperature={meas_temp} -> Fan Speed={self._speed}")
                    self.speed_ctrl.set_speed(self._speed)
                    self._meas_temp_list = meas_temp_list
                    self._status = True
            except Exception as e:
                self._status = False
                logger.error(f"Connection to {self._name} failed!")
                logger.error(f"{self._name}'s config={self._config}!")
                logger.exception(e)
            self._last_run_time = dt.now()

    def report(self):
        self._monitor_tab.update_field(self._name, "time", f"Last Run Time = {str(self._last_run_time)}")
        self._monitor_tab.update_field(self._name, "temp", f"Last Temperature = {self._meas_temp_list}")
        self._monitor_tab.update_field(self._name, "adjust", f"Last Control Adjustment = {str(self._speed)}")
        self._monitor_tab.update_field(self._name, "status", f"Last Status = {str(self._status)}")

    def close(self):
        pass

    @property
    def speed_ctrl(self):
        speed_ctrl_type = self._config.get("speed_ctrl_type", "None")
        if speed_ctrl_type == self._speed_ctrl_type:
            return self._speed_ctrl
        elif speed_ctrl_type == "iDRAC 7" or speed_ctrl_type == "iDRAC 8":
            self._speed_ctrl = idrac.Ipmi(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif speed_ctrl_type == "iDRAC 9":
            self._speed_ctrl = idrac.Redfish(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif speed_ctrl_type == "iLO 4":
            self._speed_ctrl = ilo.iLO4(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif speed_ctrl_type == "X9":
            self._speed_ctrl = sm.X9(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif speed_ctrl_type == "X10":
            self._speed_ctrl = sm.X10(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif speed_ctrl_type == "X11":
            self._speed_ctrl = sm.X11(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        else:
            self._speed_ctrl = None
        self._speed_ctrl_type = speed_ctrl_type
        return self._speed_ctrl

    @property
    def cpu_temp(self):
        cpu_temp_type = self._config.get("cpu_temp_type", "None")
        if cpu_temp_type == self._cpu_temp_type:
            return self._cpu_temp
        elif cpu_temp_type == "iDRAC 7" or cpu_temp_type == "iDRAC 8":
            self._cpu_temp = idrac.Ipmi(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif cpu_temp_type == "iDRAC 9":
            self._cpu_temp = idrac.Redfish(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif cpu_temp_type == "iLO 4":
            self._cpu_temp = ilo.iLO4(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif cpu_temp_type == "X9":
            self._cpu_temp = sm.X9(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif cpu_temp_type == "X10":
            self._cpu_temp = sm.X10(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        elif cpu_temp_type == "X11":
            self._cpu_temp = sm.X11(
                address=self._config["oob_address"],
                password=self._config["oob_password"],
                username=self._config["oob_username"],
            )
        else:
            self._cpu_temp = None
        self._cpu_temp_type = cpu_temp_type
        return self._cpu_temp

    @property
    def drive_temp(self):
        drive_temp_type = self._config.get("drive_temp_type", "None")
        if drive_temp_type == self._drive_temp_type:
            return self._drive_temp
        if drive_temp_type == "SMART":
            self._drive_temp = smart.Smart(
                address=self._config["ssh_address"],
                username=self._config["ssh_password"],
                password=self._config["ssh_username"],
            )
        else:
            self._drive_temp = None
        return self._drive_temp

    @property
    def gpu_temp(self):
        gpu_temp_type = self._config.get("gpu_temp_type", "None")
        if gpu_temp_type == self._gpu_temp_type:
            return self._gpu_temp
        if gpu_temp_type == "SMART":
            self._gpu_temp = smart.Smart(
                address=self._config["ssh_address"],
                username=self._config["ssh_password"],
                password=self._config["ssh_username"],
            )
        else:
            self._gpu_temp = None
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
            for s, t in zip(self._speeds, self._temps).items():
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
