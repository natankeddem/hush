# hush

## ***WARNING***

**Improper setup or bugs in this software may overheat your system!**

**This utility is still in early developement and may require breaking changes on updates. Your configuration may be lost on such updates and your fans will not long be controlled. Care must be taken when using watchtower or similar tools to update this utility.**

## Information
GUI enabled Docker based fan controller. I appreciate all comments/feedback/bug reports.

## Features
* Single container controls multiple machines at once.
* Tempurature calculation takes into account CPUs, Drives and GPUs.
* Full GUI configuration, no YAML or INI file editing required.
* Allows monitoring of temperatures and fan speeds.

## Supported Protocols

| Driver         | Credentials | Temperature | Fan Control | Notes                            |
|----------------|-------------|-------------|-------------|----------------------------------|
| iDRAC7         | OOB         | IPMI        | IPMI        |                                  |
| iDRAC8         | OOB         | IPMI        | IMPI        |                                  |
| iDRAC9         | OOB         | Redfish     | RedFish     | offset control only              |
| iLO4           | OOB         | Redfish     | Proprietary | must be running unlocked version |
| Supermicro X9  | OOB         | IPMI        | IPMI        |                                  |
| Supermicro X10 | OOB         | IPMI        | IPMI        |                                  |
| Supermicro X11 | OOB         | IPMI        | IPMI        |                                  |
| SMART          | OS          | smartctl    |             |                                  |
| Nvidia GPU     | OS          | nvidia-smi  |             |                                  |

I am hoping to add more controls and sensors in the future.

## Installation
See docker-compose for reference.
