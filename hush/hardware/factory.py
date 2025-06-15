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
from hush.hardware import openjbod


class Factory:
    drivers: dict = {}

    @classmethod
    async def remove_host(cls, host: str) -> None:
        if host in cls.drivers:
            groups = list(cls.drivers[host].keys())
            for group in groups:
                await cls.close(host, group)
            del cls.drivers[host]

    @classmethod
    def add_group(cls, host: str, group: str) -> None:
        cls.drivers[host][group] = {}
        cls.drivers[host][group]["name"] = ""
        cls.drivers[host][group]["instance"] = None

    @classmethod
    async def driver(
        cls,
        host: str,
        group: str,
    ) -> Optional[hardware.Device]:
        name = storage.host(host).get(group, "None")
        if name == "Shared":
            host = storage.host(host)["shared"][group]
            name = storage.host(host).get(group, "None")
        if host not in cls.drivers:
            cls.drivers[host] = {}
        if group not in cls.drivers[host]:
            cls.add_group(host, group)
        if cls.drivers[host][group]["name"] != name:
            if cls.drivers[host][group]["instance"] is not None:
                await cls.close(host, group)
                cls.add_group(host, group)
            cls.drivers[host][group]["name"] = name
            if group == "speed":
                if name == "Dell iDRAC 7":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 8":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 9":
                    cls.drivers[host][group]["instance"] = idrac.Redfish(host)
                elif name == "HP iLO 4 All":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host, fans=[])
                elif name == "HP iLO 4 Discrete":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host, fans=storage.host(host)["ilo4"].get(group, []))
                elif name == "Supermicro X9":
                    cls.drivers[host][group]["instance"] = supermicro.X9(host)
                elif name == "Supermicro X10 All":
                    cls.drivers[host][group]["instance"] = supermicro.X10(host)
                elif name == "Supermicro X10 Discrete":
                    cls.drivers[host][group]["instance"] = supermicro.X10(host, speed_zones=storage.host(host)["supermicro"].get(group, []))
                elif name == "Supermicro X11 All":
                    cls.drivers[host][group]["instance"] = supermicro.X11(host)
                elif name == "Supermicro X11 Discrete":
                    cls.drivers[host][group]["instance"] = supermicro.X11(host, speed_zones=storage.host(host)["supermicro"].get(group, []))
                elif name == "Cisco M3":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                elif name == "Cisco M4":
                    cls.drivers[host][group]["instance"] = cisco.M4(host)
                elif name == "Cisco M5":
                    cls.drivers[host][group]["instance"] = cisco.M5(host)
                elif name == "OpenJBOD":
                    cls.drivers[host][group]["instance"] = openjbod.Rp2040(host)
                elif name == "Nvidia":
                    cls.drivers[host][group]["instance"] = nvidia.Gpu(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "cpu":
                if name == "Dell iDRAC 7":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 8":
                    cls.drivers[host][group]["instance"] = idrac.Ipmi(host)
                elif name == "Dell iDRAC 9":
                    cls.drivers[host][group]["instance"] = idrac.Redfish(host)
                elif name == "HP iLO 4 All":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host)
                    await cls.drivers[host][group]["instance"].set_cpu_temp_names()
                elif name == "HP iLO 4 Discrete":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host, temps=storage.host(host)["ilo4"].get(group, []))
                elif name == "Supermicro X9":
                    cls.drivers[host][group]["instance"] = supermicro.X9(host)
                elif name == "Supermicro X10":
                    cls.drivers[host][group]["instance"] = supermicro.X10(host)
                elif name == "Supermicro X11":
                    cls.drivers[host][group]["instance"] = supermicro.X11(host)
                elif name == "Cisco M3":
                    cls.drivers[host][group]["instance"] = cisco.M3(host)
                elif name == "Cisco M4":
                    cls.drivers[host][group]["instance"] = cisco.M4(host)
                elif name == "Cisco M5":
                    cls.drivers[host][group]["instance"] = cisco.M5(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "pci":
                if name == "HP iLO 4 All":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host)
                    await cls.drivers[host][group]["instance"].set_pci_temp_names()
                elif name == "HP iLO 4 Discrete":
                    cls.drivers[host][group]["instance"] = ilo.iLO4(host, temps=storage.host(host)["ilo4"].get(group, []))
                else:
                    cls.drivers[host][group]["instance"] = None
            elif group == "drive":
                if name == "SMART All":
                    cls.drivers[host][group]["instance"] = smart.Smart(host)
                elif name == "SMART Discrete":
                    cls.drivers[host][group]["instance"] = smart.Smart(host, drives=storage.host(host)["smart"].get(group, []))
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "gpu":
                if name == "Nvidia":
                    cls.drivers[host][group]["instance"] = nvidia.Gpu(host)
                elif name == "Supermicro":
                    cls.drivers[host][group]["instance"] = supermicro.Gpu(host)
                else:
                    cls.drivers[host][group]["instance"] = None
            if group == "chassis":
                if name == "OpenJBOD":
                    cls.drivers[host][group]["instance"] = openjbod.Rp2040(host)
                else:
                    cls.drivers[host][group]["instance"] = None
        return cls.drivers[host][group]["instance"]

    @classmethod
    async def close(
        cls,
        host: str,
        group: str,
    ):
        if host in cls.drivers:
            if group in cls.drivers[host]:
                if "instance" in cls.drivers[host][group]:
                    if cls.drivers[host][group]["instance"] is not None:
                        instance = cls.drivers[host][group]["instance"]
                        logger.info(f"Closing hardware driver for {host}: {instance}")
                        try:
                            await instance.close()
                        except Exception as e:
                            logger.info(f"Failed to close hardware driver for {host}: {instance}")
        if host in cls.drivers:
            if group in cls.drivers[host]:
                del cls.drivers[host][group]

    @classmethod
    async def close_all(cls):
        for host in cls.drivers.keys():
            if isinstance(cls.drivers[host], dict) is True:
                groups = list(cls.drivers[host].keys())
                for group in groups:
                    await cls.close(host=host, group=group)
