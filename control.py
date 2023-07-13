import logging

logger = logging.getLogger(__name__)
import threading
import hardware.fanctrl as fanctrl
import hardware.idrac as idrac
import hardware.ilo as ilo
from tabs import configs


class Machine:
    def __init__(self, monitor_tab) -> None:
        self._monitor_tab = monitor_tab
        self._fms = dict()

    def run(self):
        for name, config in configs.items():
            thread = threading.Thread(name="async_run", args=(name, config), target=self.thread)
            thread.start()

    def close(self):
        for fm in self._fms:
            try:
                fm.close()
            except:
                pass
    def thread(self, name, config):
        if name not in self._fms:
            pwm_ctrl_type = config.get("pwm_ctrl_type", "None")
            if pwm_ctrl_type == "iDRAC 7" or pwm_ctrl_type == "iDRAC 8":
                adjust_cb = idrac.Ipmi(
                    address=config["oob_address"], username=config["oob_username"], password=config["oob_password"]
                ).set_pwm
            elif pwm_ctrl_type == "iDRAC 9":
                adjust_cb = idrac.Redfish(
                    address=config["oob_address"], username=config["oob_username"], password=config["oob_password"]
                ).set_fan_offset
            elif pwm_ctrl_type == "iLO 4":
                adjust_cb = ilo.iLO4(
                    address=config["oob_address"], username=config["oob_username"], password=config["oob_password"]
                ).set_pwm
            else:
                adjust_cb = None
            cpu_temp_type = config.get("cpu_temp_type", "None")
            if cpu_temp_type == "iDRAC 7" or cpu_temp_type == "iDRAC 8":
                cpu_temp_cb = idrac.Ipmi(
                    address=config["oob_address"], username=config["oob_username"], password=config["oob_password"]
                ).get_cpu_temp
            elif cpu_temp_type == "iDRAC 9":
                cpu_temp_cb = idrac.Redfish(
                    address=config["oob_address"], username=config["oob_username"], password=config["oob_password"]
                ).get_cpu_temp
            elif pwm_ctrl_type == "iLO 4":
                cpu_temp_cb = ilo.iLO4(
                    address=config["oob_address"], username=config["oob_username"], password=config["oob_password"]
                ).get_cpu_temp
            else:
                cpu_temp_cb = None
            drive_temp_cb = None

            self._fms[name] = fanctrl.Machine()
            self._fms[name].temp_cb = [cpu_temp_cb, drive_temp_cb]
            self._fms[name].adjust_cb = adjust_cb
        cpu_curve = fanctrl.Curve(
            curve=dict(
                zip(
                    list(config["algo"]["curves"]["cpu"]["pwm"].values()),
                    list(config["algo"]["curves"]["cpu"]["temp"].values()),
                )
            )
        )
        drive_curve = fanctrl.Curve(
            curve=dict(
                zip(
                    list(config["algo"]["curves"]["drive"]["pwm"].values()),
                    list(config["algo"]["curves"]["drive"]["temp"].values()),
                )
            )
        )
        self._fms[name].curve = [cpu_curve, drive_curve]
        self._fms[name].run()
        self._monitor_tab.update_field(name, "time", f"Last Run Time = {str(self._fms[name].last_run_time)}")
        self._monitor_tab.update_field(name, "temp", f"Last Temperature = {str(self._fms[name].temp)}")
        self._monitor_tab.update_field(name, "adjust", f"Last Control Adjustment = {str(self._fms[name].adjust)}")
        self._monitor_tab.update_field(name, "status", f"Last Status = {str(self._fms[name].status)}")
