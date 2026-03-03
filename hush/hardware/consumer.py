import time
import logging
from typing import Optional, List, Dict
import numpy as np
from . import Device

logger = logging.getLogger(__name__)


class Consumer(Device):
    # Class-level dictionary to share cache across all instances of Consumer
    # Format: { "hostname": { "fan": {}, "fan_time": 0.0, "temp": {}, "temp_time": 0.0 } }
    _shared_hwmon_cache: Dict[str, Dict] = {}

    # Cache expiration time in seconds (5 minutes)
    CACHE_TTL = 300

    def __init__(self, host: str, temp_names: Optional[List[str]] = None, fan_names: Optional[List[str]] = None) -> None:
        super().__init__(host)
        self.temp_names: List[str] = temp_names if temp_names is not None else []
        self.fan_names: List[str] = fan_names if fan_names is not None else []
        self._speed: Optional[int] = None
        self._temp: Optional[int] = None

        # Initialize the shared cache structure for this host if it doesn't exist yet
        if self.host not in Consumer._shared_hwmon_cache:
            Consumer._shared_hwmon_cache[self.host] = {"fan": {}, "fan_time": 0.0, "temp": {}, "temp_time": 0.0}

        self.get_os_credentials()

    async def close(self):
        return

    async def get_temp(self, temp_names: Optional[List[str]] = None) -> Optional[int]:
        try:
            cache = Consumer._shared_hwmon_cache[self.host]

            # Auto-populate cache if empty or TTL expired
            if not cache["temp"] or (time.time() - cache["temp_time"] > self.CACHE_TTL):
                await self.get_cpu_temp_names(force_refresh=True)

            # Use injected class variables if no explicit names provided
            if temp_names is None:
                temp_names = self.temp_names

            paths_to_read = []
            if temp_names:
                # Force a single refresh if hardware changed or a requested sensor is missing
                if any(name not in cache["temp"] for name in temp_names):
                    await self.get_cpu_temp_names(force_refresh=True)

                # Link human readable names to hwmon references
                for name in temp_names:
                    if name in cache["temp"]:
                        paths_to_read.append(cache["temp"][name])

            # If no selections exist, fallback to reading all cached sensors
            if not paths_to_read:
                paths_to_read = list(cache["temp"].values())

            temps = []
            if paths_to_read:
                # Wrapped payload in single quotes to protect from the local container's shell
                cmd = "cat " + " ".join(paths_to_read) + " 2>/dev/null || true"
                result = await self.ssh.shell(f"'{cmd}'")

                for line in result.stdout_lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        val = float(line)
                        if val > 1000:
                            val = val / 1000.0
                        temps.append(val)
                    except ValueError:
                        continue

            # Fallback ONLY if no selections were provided and sysfs failed completely
            if not temps and not temp_names:
                result = await self.ssh.shell("'sensors -u 2>/dev/null || true'")
                for line in result.stdout_lines:
                    line = line.strip()
                    if line.endswith(":"):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            v = float(parts[-1])
                            temps.append(v)
                        except ValueError:
                            continue

            if not temps:
                raise RuntimeError(f"No hwmon temperature data available for {self.host}")

            self._temp = int(np.max(temps))
            return self._temp

        except Exception as e:
            logger.error(f"{self.host} consumer hwmon get_temp failed: {e}")
            raise e

    async def set_speed(self, speed: int, fan_names: Optional[List[str]] = None) -> None:
        try:
            if speed is None:
                return

            speed = max(0, min(100, int(speed)))
            if getattr(self, "_speed", None) == speed:
                return

            pwm_val = int(speed * 255 / 100)

            cache = Consumer._shared_hwmon_cache[self.host]

            # Auto-populate cache if empty or TTL expired
            if not cache["fan"] or (time.time() - cache["fan_time"] > self.CACHE_TTL):
                await self.get_fan_names(force_refresh=True)

            # Use injected class variables if no explicit names provided
            if fan_names is None:
                fan_names = self.fan_names

            paths_to_write = []
            if fan_names:
                # Force a refresh if a requested fan isn't recognized
                if any(name not in cache["fan"] for name in fan_names):
                    await self.get_fan_names(force_refresh=True)

                # Link human readable names to hwmon references
                for name in fan_names:
                    if name in cache["fan"]:
                        paths_to_write.append(cache["fan"][name])

            if paths_to_write:
                # Enable manual mode and write PWM for targeted fans.
                commands = []
                for path in paths_to_write:
                    enable_path = f"{path}_enable"
                    commands.append(f"[ -f {enable_path} ] && echo 1 2>/dev/null > {enable_path} || true")
                    commands.append(f"[ -f {path} ] && echo {pwm_val} 2>/dev/null > {path} || true")

                if commands:
                    cmd_str = " ; ".join(commands)
                    # Wrapped payload in single quotes to protect && and ; from the local container's shell
                    await self.ssh.shell(f"'{cmd_str}'")
            else:
                # Fallback: put ALL hwmon into manual mode and write PWM
                enable_cmd = 'for en in /sys/class/hwmon/*/pwm*_enable; do [ -f "$en" ] && echo 1 2>/dev/null > "$en" || true; done'
                pwm_cmd = (
                    f"for f in /sys/class/hwmon/*/pwm*; do "
                    f'if echo "$f" | grep -q "_enable" ; then continue; fi; '
                    f'[ -f "$f" ] && echo {pwm_val} 2>/dev/null > "$f" || true; done'
                )
                # Wrapped payload in single quotes
                await self.ssh.shell(f"'{enable_cmd}'")
                await self.ssh.shell(f"'{pwm_cmd}'")

            self._speed = speed
            logger.info(f"Set consumer hwmon fan speed {speed}% (pwm={pwm_val}) on {self.host}")
        except Exception as e:
            logger.error(f"{self.host} consumer hwmon set_speed failed: {e}")
            raise e

    async def get_fan_speed(self) -> Dict[str, int]:
        """
        Reads the actual RPM (speed) of the fans.
        Returns a dictionary mapping human-readable fan names to their RPM values.
        """
        try:
            cache = Consumer._shared_hwmon_cache[self.host]

            # Auto-populate cache if empty or TTL expired
            if not cache["fan"] or (time.time() - cache["fan_time"] > self.CACHE_TTL):
                await self.get_fan_names(force_refresh=True)

            # Use explicitly configured fans, or fallback to returning everything
            target_names = self.fan_names if self.fan_names else list(cache["fan"].keys())

            if not target_names:
                return {}

            # Execute a single command to retrieve ALL fan readouts instantly
            res = await self.ssh.shell("'grep -aH . /sys/class/hwmon/hwmon*/fan*_input 2>/dev/null || true'")
            raw_rpms = {}
            for line in res.stdout_lines:
                if ":" in line:
                    path, val = line.split(":", 1)
                    raw_rpms[path.strip()] = val.strip()

            results = {}
            for name in target_names:
                if name in cache["fan"]:
                    pwm_path = cache["fan"][name]
                    # Convert something like "/sys/.../hwmon0/pwm1" to "/sys/.../hwmon0/fan1_input"
                    hwmon_dir, filename = pwm_path.rsplit("/", 1)
                    idx = filename.replace("pwm", "")
                    fan_input_path = f"{hwmon_dir}/fan{idx}_input"

                    rpm_str = raw_rpms.get(fan_input_path, "0")
                    try:
                        results[name] = int(rpm_str)
                    except ValueError:
                        results[name] = 0

            return results

        except Exception as e:
            logger.error(f"{self.host} consumer hwmon get_fan_speed failed: {e}")
            raise e

    async def get_fan_names(self, force_refresh: bool = False) -> List[str]:
        cache = Consumer._shared_hwmon_cache[self.host]

        # Return cached names immediately if valid and not forced
        if not force_refresh and cache["fan"] and (time.time() - cache["fan_time"] < self.CACHE_TTL):
            return list(cache["fan"].keys())

        cache["fan"].clear()
        try:
            res_pwm = await self.ssh.shell("'ls -1 /sys/class/hwmon/hwmon*/pwm*[0-9] 2>/dev/null || true'")
            pwm_paths = [line.strip() for line in res_pwm.stdout_lines if line.strip()]

            if not pwm_paths:
                return []

            # Using . instead of ^ to perfectly match text without any regex shell quoting issues
            res_names = await self.ssh.shell("'grep -aH . /sys/class/hwmon/hwmon*/name 2>/dev/null || true'")
            hwmon_names = {}
            for line in res_names.stdout_lines:
                if ":" in line:
                    path, val = line.split(":", 1)
                    hwmon_names[path.rsplit("/", 1)[0]] = val.strip()

            for pwm_path in pwm_paths:
                hwmon_dir, filename = pwm_path.rsplit("/", 1)
                device_name = hwmon_names.get(hwmon_dir, "unknown")
                idx = filename.replace("pwm", "")

                # 100% static string guaranteed to survive reboots (e.g. "nct6775 - PWM 1")
                human_name = f"{device_name} - PWM {idx}"
                cache["fan"][human_name] = pwm_path

            cache["fan_time"] = time.time()

        except Exception as e:
            logger.debug(f"Failed to enumerate fan pwm files on {self.host}: {e}")

        return list(cache["fan"].keys())

    async def get_cpu_temp_names(self, force_refresh: bool = False) -> List[str]:
        cache = Consumer._shared_hwmon_cache[self.host]

        # Return cached names immediately if valid and not forced
        if not force_refresh and cache["temp"] and (time.time() - cache["temp_time"] < self.CACHE_TTL):
            return list(cache["temp"].keys())

        cache["temp"].clear()
        try:
            res_temps = await self.ssh.shell("'grep -aH . /sys/class/hwmon/hwmon*/temp*_input 2>/dev/null || true'")
            temp_files = []
            for line in res_temps.stdout_lines:
                if ":" in line:
                    path, val = line.split(":", 1)
                    if val.strip():
                        temp_files.append(path.strip())

            if not temp_files:
                return []

            res_names = await self.ssh.shell("'grep -aH . /sys/class/hwmon/hwmon*/name 2>/dev/null || true'")
            hwmon_names = {}
            for line in res_names.stdout_lines:
                if ":" in line:
                    path, val = line.split(":", 1)
                    hwmon_names[path.rsplit("/", 1)[0]] = val.strip()

            res_labels = await self.ssh.shell("'grep -aH . /sys/class/hwmon/hwmon*/temp*_label 2>/dev/null || true'")
            temp_labels = {}
            for line in res_labels.stdout_lines:
                if ":" in line:
                    path, val = line.split(":", 1)
                    temp_labels[path.strip()] = val.strip()

            for temp_path in temp_files:
                hwmon_dir, filename = temp_path.rsplit("/", 1)
                device_name = hwmon_names.get(hwmon_dir, "unknown")

                label_path = temp_path.replace("_input", "_label")
                label = temp_labels.get(label_path)

                if not label:
                    idx_str = filename.replace("temp", "").replace("_input", "")
                    label = f"Temp {idx_str}"

                human_name = f"{device_name} - {label}"
                cache["temp"][human_name] = temp_path

            cache["temp_time"] = time.time()

        except Exception as e:
            logger.debug(f"Failed to enumerate hwmon temp inputs on {self.host}: {e}")

        return list(cache["temp"].keys())
