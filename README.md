# hush

## Demo
[hush_demo.webm](https://github.com/natankeddem/hush/assets/44515217/f7545b98-657a-4771-83d3-54ef61e985b1)

## ***WARNING***

**Improper setup or bugs in this software may overheat your system!**

**This utility is still in early developement and may require breaking changes on updates. Your configuration may be lost on such updates and your fans will no longer be controlled. Care must be taken when using watchtower or similar tools to update this utility.**

## Information
GUI enabled Docker based fan controller. I appreciate all comments/feedback/bug reports.

## Features
* Single container controls multiple machines at once.
* Temperature calculation takes into account CPUs, Drives and GPUs and more sensors.
* Full GUI configuration, no YAML or INI file editing required.
* Allows monitoring of temperatures and fan speeds.
* Transmits MQTT sensor data to external message brokers, includes support for Home Assistant MQTT discovery.

## Supported Protocols

| Driver         | Credentials | Temperature | Fan Control | Notes                            |
|----------------|-------------|-------------|-------------|----------------------------------|
| iDRAC7         | OOB         | IPMI        | IPMI        |                                  |
| iDRAC8         | OOB         | IPMI        | IMPI        | also for iDRAC 9 3.30.30.30 and earlier                                  |
| iDRAC9         | OOB         | Redfish     | RedFish     | offset control only              |
| iLO4           | OOB         | Redfish     | Proprietary | must be running unlocked version |
| Supermicro X9  | OOB         | IPMI        | IPMI        |                                  |
| Supermicro X10 | OOB         | IPMI        | IPMI        |                                  |
| Supermicro X11 | OOB         | IPMI        | IPMI        |                                  |
| Cisco M3       | OOB         | XML API     | XML API     | fan profile control only         |
| Cisco M4       | OOB         | XML API     | XML API     | fan profile control only         |
| Cisco M5       | OOB         | XML API     | XML API     | fan profile control only         |
| SMART          | OS          | smartctl    |             |                                  |
| Nvidia GPU     | OS          | nvidia-smi  |             |                                  |

I am hoping to add more controls and sensors in the future.

## Installation
See docker-compose for reference.
