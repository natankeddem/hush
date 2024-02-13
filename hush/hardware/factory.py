import logging

logger = logging.getLogger(__name__)
from typing import Literal, Optional
from hush import storage
from . import Device
from .cisco import M3
from .gpu import Nvidia
from .idrac import Ipmi, Redfish
from .ilo import iLO4
from .smart import Smart
from .supermicro import X9, X10, X11


class Factory:
    drivers: dict = {}

    @classmethod
    async def driver(
        cls,
        host: str,
        group: str,
    ) -> Optional[Device]:
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
                    cls.drivers[host][group]["instance"] = Ipmi(host)
                elif name == "Dell iDRAC 8":
                    cls.drivers[host][group]["instance"] = Ipmi(host)
                elif name == "Dell iDRAC 9":
                    cls.drivers[host][group]["instance"] = Redfish(host)
                elif name == "HP iLO 4":
                    cls.drivers[host][group]["instance"] = iLO4(host)
                elif name == "Supermicro X9":
                    cls.drivers[host][group]["instance"] = X9(host)
                elif name == "Supermicro X10":
                    cls.drivers[host][group]["instance"] = X10(host)
                elif name == "Supermicro X11":
                    cls.drivers[host][group]["instance"] = X11(host)
                elif name == "Cisco M3":
                    cls.drivers[host][group]["instance"] = M3(host)
                elif name == "Cisco M4":
                    cls.drivers[host][group]["instance"] = M3(host)
                elif name == "Cisco M5":
                    cls.drivers[host][group]["instance"] = M3(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "cpu":
                if name == "Dell iDRAC 7":
                    cls.drivers[host][group]["instance"] = Ipmi(host)
                elif name == "Dell iDRAC 8":
                    cls.drivers[host][group]["instance"] = Ipmi(host)
                elif name == "Dell iDRAC 9":
                    cls.drivers[host][group]["instance"] = Redfish(host)
                elif name == "HP iLO 4":
                    cls.drivers[host][group]["instance"] = iLO4(host)
                elif name == "Supermicro X9":
                    cls.drivers[host][group]["instance"] = X9(host)
                elif name == "Supermicro X10":
                    cls.drivers[host][group]["instance"] = X10(host)
                elif name == "Supermicro X11":
                    cls.drivers[host][group]["instance"] = X11(host)
                elif name == "Cisco M3":
                    cls.drivers[host][group]["instance"] = M3(host)
                elif name == "Cisco M4":
                    cls.drivers[host][group]["instance"] = M3(host)
                elif name == "Cisco M5":
                    cls.drivers[host][group]["instance"] = M3(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            elif group == "drive":
                if name == "SMART":
                    cls.drivers[host][group]["instance"] = Smart(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "gpu":
                if name == "Nvidia":
                    cls.drivers[host][group]["instance"] = Nvidia(host)
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
