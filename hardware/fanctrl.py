import logging

logger = logging.getLogger(__name__)
from typing import List
import sys

import numpy as np
from scipy.interpolate import interp1d
import math
import datetime
from hardware.idrac import Redfish

try:
    import mysecret
except:
    logger.info("mysecret was not loaded")


class Machine:
    def __init__(self, temp_cb=None, adjust_cb=None, curve=None):
        self.temp_cb = temp_cb
        self.adjust_cb = adjust_cb
        self.curve = curve
        self._temp = None
        self._adjust = None
        self._status = None
        self._last_run_time = None

    def run(self):
        int_adjust = None
        current_adjust = None
        final_adjust = None
        temp_list = list()
        try:
            for temp_cb, curve in dict(zip(self.temp_cb, self.curve)).items():
                if temp_cb is not None:
                    temp = temp_cb()
                    adjust = curve.calc(temp)
                    temp_list.append(temp)
                    logger.debug(f"adjust={adjust} values={curve.values}")
                    if adjust is not None:
                        if isinstance(adjust, str) is True:
                            current_adjust = curve.values.index(adjust)
                        else:
                            current_adjust = adjust
                        if int_adjust is None or current_adjust > int_adjust:
                            int_adjust = current_adjust
                            if isinstance(adjust, str) is True:
                                final_adjust = adjust
                            else:
                                final_adjust = current_adjust
            if final_adjust is not None:
                self.adjust = final_adjust
                logger.info(f"Temperature={temp} -> Fan Speed={self.adjust}")
                self.adjust_cb(self.adjust)
                self.temp = temp_list
                self.status = True
        except Exception as e:
            self.status = False
            raise e
        self.last_run_time = datetime.datetime.now()

    @property
    def temp_cb(self):
        return self._temp_cb

    @temp_cb.setter
    def temp_cb(self, temp_cb):
        if isinstance(temp_cb, List) is True:
            self._temp_cb = temp_cb
        else:
            self._temp_cb = [temp_cb]

    @property
    def adjust_cb(self):
        return self._adjust_cb

    @adjust_cb.setter
    def adjust_cb(self, adjust_cb):
        self._adjust_cb = adjust_cb

    @property
    def curve(self):
        return self._curve

    @curve.setter
    def curve(self, curve):
        if isinstance(curve, List) is True:
            self._curve = curve
        else:
            self._curve = [curve]

    @property
    def temp(self):
        return self._temp

    @temp.setter
    def temp(self, temp):
        self._temp = temp

    @property
    def adjust(self):
        return self._adjust

    @adjust.setter
    def adjust(self, adjust):
        self._adjust = adjust

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def last_run_time(self):
        return self._last_run_time

    @last_run_time.setter
    def last_run_time(self, time):
        self._last_run_time = datetime.datetime.now()


class Curve:
    def __init__(self, curve):
        logger.info(f"curve={curve}")
        self.values = list()
        self.temps = list()
        self._curve = curve
        for values, temps in self._curve.items():
            self.values.append(values)
            self.temps.append(temps)

    def calc(self, temp):
        value = None
        if isinstance(self.values, List) is True and len(self.values) > 0:
            if isinstance(self.values[0], int) is True:
                value = self.temp2pwm(temp)
            else:
                value = self.temp2value(temp)
        return value

    def temp2value(self, temp):
        set_value = None
        temp_count = len(self.temps)
        value_count = len(self.values)
        if temp_count < 2 or value_count < 2:
            set_value = self.values[0]
        if temp <= self.temps[0]:
            set_value = self.values[0]
        elif temp > self.temps[-1]:
            set_value = self.values[-1]
        else:
            for v, t in self._curve.items():
                if temp > t:
                    set_value = v
                logger.info(f"temp={t} value={v} set_value={set_value}")
        return set_value

    def temp2pwm(self, temp):
        temps = self.temps
        temps.insert(0, 1)
        temps.append(120)
        pwms = self.values
        pwms.insert(0, self.values[0])
        pwms.append(self.values[-1])
        pwm_interp = interp1d(temps, pwms)
        temp_range = np.arange(min(temps), max(temps), 1)
        pwm = math.ceil(pwm_interp(temp_range)[temp - 1])
        return pwm


if __name__ == "__main__":
    ti = Redfish("10.1.7.180", password=mysecret.password)
    t = ti.get_cpu_temp
    pi = Redfish("10.1.7.180", password=mysecret.password)
    p = pi.set_fan_offset
    c = Curve(curve={20: 20, 30: 30, 10: 40, 50: 60, 100: 90})
    # c = Curve(
    #     curve={
    #         pi.Fan_Offset.OFF: 20,
    #         pi.Fan_Offset.LOW: 30,
    #         pi.Fan_Offset.MEDIUM: 10,
    #         pi.Fan_Offset.HIGH: 60,
    #         pi.Fan_Offset.MAX: 90,
    #     }
    # )
    r = Machine(temp_cb=t, adjust_cb=p, curve=c)
    ts = np.arange(10, 100, 1)
    for n in ts:
        ti._temp = n
        r.run()
