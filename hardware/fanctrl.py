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
        calcs_made = 0
        try:
            for temp_cb, curve in dict(zip(self.temp_cb, self.curve)).items():
                if temp_cb is not None:
                    self.temp = temp_cb()
                    adjust = curve.calc(self.temp)
                    if adjust is not None:
                        if self.adjust is None or adjust > self.adjust:
                            self.adjust = adjust
                    calcs_made = calcs_made + 1
            if calcs_made != 0:
                logger.info(f"ma= {self.adjust}")
                self.adjust_cb(self.adjust)
                self.status = True
        except:
            logger.info(f"{sys.exc_info()[0]}")
            self.status = False
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

    # temp_cb, adjust_cb, curve
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
        self.values = list()
        self.temps = list()
        for values, temps in curve.items():
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
        value = None
        temp_count = len(self.temps)
        value_count = len(self.values)
        if temp_count < 2 or value_count < 2:
            value = self.values[0]
        if temp <= self.temps[0]:
            value = self.values[0]
        elif temp > self.temps[-1]:
            value = self.values[-1]
        else:
            itemp = 0
            for t in self.temps:
                if temp > t:
                    value = self.values[itemp]
                itemp = itemp + 1
        return value

    def temp2pwm(self, temp):
        # logger.info(f"t={temp}")
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
