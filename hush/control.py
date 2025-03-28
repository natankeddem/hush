import logging

logger = logging.getLogger(__name__)
from typing import List
import asyncio
import numpy as np
from scipy.interpolate import interp1d
import math
from datetime import datetime as dt
from datetime import timedelta
from simple_pid import PID
from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo
from hush import storage
from hush.hardware.factory import Factory
from hush.tabs.monitor import Status


class Launcher:
    def __init__(self) -> None:
        self.times: dict = {}
        self.busy: bool = False

    async def run(self) -> None:
        self.busy = True
        hosts = list(storage.hosts.keys())
        for host in hosts:
            if not storage.host(host)["shared"].get("speed", None):
                delay = storage.host(host).get("delay", 30)
                if host not in self.times:
                    elapsed_time = timedelta(seconds=delay)
                else:
                    elapsed_time = dt.now() - self.times[host]
                shared_speed_hosts = []
                for h in hosts:
                    if host == storage.host(h)["shared"].get("speed", ""):
                        shared_speed_hosts.append(h)
                if delay is not None and delay > 0 and elapsed_time.seconds >= delay:
                    machine = Machine(host=host, shared_speed_hosts=shared_speed_hosts)
                    await machine.run()
                    self.times[host] = dt.now()
        self.busy = False

    async def wait_on_not_busy(self) -> None:
        while self.busy is True:
            await asyncio.sleep(0.5)


class Machine:
    def __init__(self, host: str, shared_speed_hosts: List[str]) -> None:
        self._host = host
        self._shared_speed_hosts = shared_speed_hosts

    async def run(self):
        try:
            await self._calc()
        except Exception as e:
            status = Status(host=self._host)
            status.submit()
            logger.error(f"Connection to {self._host} failed!")
            logger.error(f"{self._host}'s config={storage.host(self._host)}!")
            logger.exception(e)

    async def _calc(self):
        highest_speed = None
        current_speed = None
        final_speed = None
        temperatures = {}
        mqtt_active = False
        if (
            "mqtt" in storage.host(self._host)
            and storage.host(self._host)["mqtt"].get("hostname", "") != ""
            and storage.host(self._host)["mqtt"].get("username", "") != ""
            and storage.host(self._host)["mqtt"].get("password", "") != ""
        ):
            mqtt_settings = Settings.MQTT(
                host=storage.host(self._host)["mqtt"].get("hostname", ""),
                username=storage.host(self._host)["mqtt"].get("username", ""),
                password=storage.host(self._host)["mqtt"].get("password", ""),
            )
            mqtt_device_info = DeviceInfo(name=self._host, identifiers=self._host)
            mqtt_active = True
        control = await Factory.driver(self._host, "speed")
        hosts = self._shared_speed_hosts
        hosts.append(self._host)
        for host in hosts:
            for sensor in ["cpu", "pci", "drive", "gpu", "chassis"]:
                driver = await Factory.driver(host, sensor)
                if driver is not None:
                    meas_temp = await driver.get_temp()
                    if mqtt_active:
                        mqtt_names = {"cpu": "CPU Temperature", "pci": "PCI Temperature", "drive": "Drive Temperature", "gpu": "GPU Temperature", "chassis": "Chassis Temperature"}
                        mqtt_sensor_info = SensorInfo(
                            name=mqtt_names[sensor],
                            device_class="temperature",
                            unique_id=f"hush_{host.replace(' ','_')}_{sensor}_temperature",
                            unit_of_measurement="°C",
                            device=mqtt_device_info,
                        )
                        mqtt_sensor_settings = Settings(mqtt=mqtt_settings, entity=mqtt_sensor_info)
                        mqtt_sensor = Sensor(mqtt_sensor_settings)
                        mqtt_sensor.set_state(meas_temp)
                    temperatures[sensor] = meas_temp
                    if control is not None:
                        if storage.algo_sensor(host, sensor)["type"] == "pid":
                            pid = Pid(host, sensor)
                            speed = round(-1 * pid.controller(meas_temp))
                            logger.debug(f"{host} Temperature={meas_temp} Speed={speed}")
                        else:
                            curve = Curve(host, sensor)
                            speed = curve.calc(meas_temp)
                            logger.debug(f"{host} Temperature={meas_temp} Speed={speed} Speeds={curve.speeds}")
                    if speed is not None:
                        if isinstance(speed, str) is True:
                            current_speed = curve.speeds.index(speed)
                        else:
                            current_speed = speed
                        if highest_speed is None or current_speed > highest_speed:
                            highest_speed = current_speed
                            if isinstance(speed, str) is True:
                                final_speed = curve.speeds[highest_speed]
                            else:
                                final_speed = highest_speed
        if final_speed is not None:
            if mqtt_active:
                unit_of_measurement = None
                if isinstance(final_speed, int) or isinstance(final_speed, float):
                    unit_of_measurement = "%"
                mqtt_speed_info = SensorInfo(
                    name="Fan Speed", device_class=None, unique_id=f"hush_{self._host.replace(' ','_')}_fan_speed", unit_of_measurement=unit_of_measurement, device=mqtt_device_info
                )
                mqtt_speed_settings = Settings(mqtt=mqtt_settings, entity=mqtt_speed_info)
                mqtt_speed = Sensor(mqtt_speed_settings)
                mqtt_speed.set_state(final_speed)
            logger.info(f"{control.hostname} Fan Speed={final_speed}")
            await control.set_speed(final_speed)
            for host in hosts:
                status = Status(
                    host=host,
                    status=True,
                    speed=highest_speed,
                    temperatures=temperatures,
                )
                status.submit()
        else:
            for host in hosts:
                status = Status(host=self._host)
                status.submit()


class Curve:
    def __init__(self, host: str, sensor: str):
        self._speeds = list(storage.curve_speed(host, sensor).values())
        self._temps = list(storage.curve_temp(host, sensor).values())

    def calc(self, temp):
        value = None
        if isinstance(self._speeds, List) is True and isinstance(self._temps, List) is True and len(self._speeds) == len(self._temps):
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


class Pid:
    pids: dict = {}

    def __init__(self, host: str, sensor: str):
        self.host = host
        self.sensor = sensor
        self._controller = self.controller

    @property
    def controller(self) -> PID:
        if self.host not in self.pids:
            self.pids[self.host] = {}
        if self.sensor not in self.pids[self.host]:
            self.pids[self.host][self.sensor] = {}
        if self.pids[self.host][self.sensor] != storage.pid(self.host, self.sensor):
            self.pids[self.host][self.sensor] = storage.pid(self.host, self.sensor)
            self._controller = PID(
                self.pids[self.host][self.sensor]["Kp"],
                self.pids[self.host][self.sensor]["Ki"],
                self.pids[self.host][self.sensor]["Kd"],
                self.pids[self.host][self.sensor]["Target"],
            )
        return self._controller
