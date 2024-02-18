import logging

logger = logging.getLogger(__name__)
from typing import Literal, Optional
from hush import storage
from hush import hardware
from hush.hardware import cisco
from hush.hardware import nvidia
from hush.hardware import idrac
from hush.hardware import ilo
from hush.hardware import smart
from hush.hardware import supermicro


class Factory:
    drivers: dict = {}

    @classmethod
    async def driver(
        cls,
        host: str,
        group: str,
    ) -> Optional[hardware.Device]:
        name = storage.host(host)[group]
        if host not in cls.drivers:
            cls.drivers[host] = {}
        if group not in cls.drivers[host]:
            cls.drivers[host][group] = {}
            cls.drivers[host][group]["name"] = ""
            cls.drivers[host][group]["instance"] = None
        if cls.drivers[host][group]["name"] != name:
            if cls.drivers[host][group]["instance"] is not None:
                await cls.close(host, group)
            cls.drivers[host][group]["name"] = name
            if group == "speed":
                if name == "Dell iDRAC 7":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 8":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 9":
                    cls.drivers[host][group]["instance"] = idrac.Redfish(host)
                elif name == "HP iLO 4":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host)
                elif name == "Supermicro X9":
                    cls.drivers[host][group]["instance"] = supermicro.X9(host)
                elif name == "Supermicro X10":
                    cls.drivers[host][group]["instance"] = supermicro.X10(host)
                elif name == "Supermicro X11":
                    cls.drivers[host][group]["instance"] = supermicro.X11(host)
                elif name == "Cisco M3":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                elif name == "Cisco M4":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                elif name == "Cisco M5":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "cpu":
                if name == "Dell iDRAC 7":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 8":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 9":
                    cls.drivers[host][group]["instance"] = idrac.Redfish(host)
                elif name == "HP iLO 4":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host)
                elif name == "Supermicro X9":
                    cls.drivers[host][group]["instance"] = supermicro.X9(host)
                elif name == "Supermicro X10":
                    cls.drivers[host][group]["instance"] = supermicro.X10(host)
                elif name == "Supermicro X11":
                    cls.drivers[host][group]["instance"] = supermicro.X11(host)
                elif name == "Cisco M3":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                elif name == "Cisco M4":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                elif name == "Cisco M5":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            elif group == "drive":
                if name == "SMART":
                    cls.drivers[host][group]["instance"] = smart.Smart(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "gpu":
                if name == "Nvidia":
                    cls.drivers[host][group]["instance"] = nvidia.Gpu(host)
                if name == "Supermicro":
                    cls.drivers[host][group]["instance"] = supermicro.Gpu(host)
                else:
                    cls.drivers[host][group]["instance"] = None
        return cls.drivers[host][group]["instance"]

    @classmethod
    async def close(
        cls,
        host: str,
        group: str,
    ):
        await cls.drivers[host][group]["instance"].close()
        del cls.drivers[host]
