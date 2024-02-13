import logging

logger = logging.getLogger(__name__)
from typing import Any, Dict, List, Optional, Union
import asyncio
from asyncio.subprocess import Process, PIPE
import contextlib
import shlex
from datetime import datetime
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy
import time
from nicegui import ui  # type: ignore


@dataclass(kw_only=True)
class Result:
    name: str = ""
    command: str = ""
    return_code: Optional[int] = 0
    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)
    terminated: bool = False
    truncated: bool = False
    data: Any = None
    trace: str = ""
    cached: bool = False
    status: str = "success"
    timestamp: float = field(default_factory=time.time)

    @property
    def failed(self) -> bool:
        return False if self.status == "success" else True

    @property
    def date(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%Y/%m/%d")

    @property
    def time(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def stdout(self) -> str:
        return "".join(self.stdout_lines)

    @property
    def stderr(self) -> str:
        return "".join(self.stderr_lines)

    @property
    def properties(self) -> List:
        return list(self.to_dict().keys())

    def to_dict(self):
        d = deepcopy(self.__dict__)
        d["failed"] = self.failed
        d["date"] = self.date
        d["time"] = self.time
        d["stdout"] = self.stdout
        d["stderr"] = self.stderr
        return d

    def from_dict(self, d):
        self.name = d["name"]
        self.command = d["command"]
        self.return_code = d["return_code"]
        self.stdout_lines = d["stdout_lines"]
        self.stderr_lines = d["stderr_lines"]
        self.terminated = d["terminated"]
        self.data = d["data"]
        self.trace = d["trace"]
        self.cached = d["cached"]
        self.status = d["status"]
        self.timestamp = d["timestamp"]
        return self


def load_terminal_css():
    ui.add_head_html('<link href="static/xterm.css" rel="stylesheet">')
    ui.add_head_html('<link href="static/jse-theme-dark.css" rel="stylesheet">')


class Terminal(ui.element, component="../../static/terminal.js", libraries=["../../static/xterm.js"]):  # type: ignore[call-arg]
    def __init__(
        self,
        options: Dict,
    ) -> None:
        super().__init__()
        self._props["options"] = options

    def call_terminal_method(self, name: str, *args) -> None:
        self.run_method("call_api_method", name, *args)


class Cli:
    def __init__(self, seperator: Union[bytes, None] = b"\n") -> None:
        self.seperator: Union[bytes, None] = seperator
        self.stdout: List[str] = []
        self.stderr: List[str] = []
        self._terminate: asyncio.Event = asyncio.Event()
        self._busy: bool = False
        self._truncated: bool = False
        self.prefix_line: str = ""
        self._stdout_terminals: List[Terminal] = []
        self._stderr_terminals: List[Terminal] = []

    async def _wait_on_stream(self, stream: asyncio.streams.StreamReader) -> Union[str, None]:
        if self.seperator is None:
            buf = await stream.read(140)
        else:
            try:
                buf = await stream.readuntil(self.seperator)
            except asyncio.exceptions.IncompleteReadError as e:
                buf = e.partial
            except Exception as e:
                raise e
        return buf.decode("utf-8")

    async def _read_stdout(self, stream: asyncio.streams.StreamReader) -> None:
        while True:
            buf = await self._wait_on_stream(stream=stream)
            if buf:
                self.stdout.append(buf)
                for terminal in self._stdout_terminals:
                    terminal.call_terminal_method("write", buf)
            else:
                break

    async def _read_stderr(self, stream: asyncio.streams.StreamReader) -> None:
        while True:
            buf = await self._wait_on_stream(stream=stream)
            if buf:
                self.stderr.append(buf)
                for terminal in self._stderr_terminals:
                    terminal.call_terminal_method("write", buf)
            else:
                break

    async def _controller(self, process: Process, max_output_lines) -> None:
        while process.returncode is None:
            if max_output_lines > 0 and len(self.stderr) + len(self.stdout) > max_output_lines:
                self._truncated = True
                process.terminate()
            if self._terminate.is_set():
                process.terminate()
            try:
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(process.wait(), 0.1)
            except Exception as e:
                logger.exception(e)

    def terminate(self) -> None:
        self._terminate.set()

    async def execute(self, command: str, max_output_lines: int = 0) -> Result:
        self._busy = True
        c = shlex.split(command, posix=False)
        try:
            process = await asyncio.create_subprocess_exec(*c, stdout=PIPE, stderr=PIPE)
            if process is not None and process.stdout is not None and process.stderr is not None:
                self.stdout.clear()
                self.stderr.clear()
                self._terminate.clear()
                self._truncated = False
                terminated = False
                now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.prefix_line = f"<{now}> {command}\n"
                for terminal in self._stdout_terminals:
                    terminal.call_terminal_method("write", "\n" + self.prefix_line)
                await asyncio.gather(
                    self._controller(process=process, max_output_lines=max_output_lines),
                    self._read_stdout(stream=process.stdout),
                    self._read_stderr(stream=process.stderr),
                )
                if self._terminate.is_set():
                    terminated = True
                await process.wait()
        except Exception as e:
            raise e
        finally:
            self._terminate.clear()
            self._busy = False
        return Result(
            command=command,
            return_code=process.returncode,
            stdout_lines=self.stdout.copy(),
            stderr_lines=self.stderr.copy(),
            terminated=terminated,
            truncated=self._truncated,
        )

    async def shell(self, command: str, max_output_lines: int = 0) -> Result:
        self._busy = True
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=PIPE, stderr=PIPE)
            if process is not None and process.stdout is not None and process.stderr is not None:
                self.stdout.clear()
                self.stderr.clear()
                self._terminate.clear()
                self._truncated = False
                terminated = False
                now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                self.prefix_line = f"<{now}> {command}\n"
                for terminal in self._stdout_terminals:
                    terminal.call_terminal_method("write", "\n" + self.prefix_line)
                await asyncio.gather(
                    self._controller(process=process, max_output_lines=max_output_lines),
                    self._read_stdout(stream=process.stdout),
                    self._read_stderr(stream=process.stderr),
                )
                if self._terminate.is_set():
                    terminated = True
                await process.wait()
        except Exception as e:
            raise e
        finally:
            self._terminate.clear()
            self._busy = False
        return Result(
            command=command,
            return_code=process.returncode,
            stdout_lines=self.stdout.copy(),
            stderr_lines=self.stderr.copy(),
            terminated=terminated,
            truncated=self._truncated,
        )

    def clear_buffers(self):
        self.prefix_line = ""
        self.stdout.clear()
        self.stderr.clear()

    def register_stdout_terminal(self, terminal: Terminal) -> None:
        if terminal not in self._stdout_terminals:
            terminal.call_terminal_method("write", self.prefix_line)
            for line in self.stdout:
                terminal.call_terminal_method("write", line)
            self._stdout_terminals.append(terminal)

    def register_stderr_terminal(self, terminal: Terminal) -> None:
        if terminal not in self._stderr_terminals:
            for line in self.stderr:
                terminal.call_terminal_method("write", line)
            self._stderr_terminals.append(terminal)

    def release_stdout_terminal(self, terminal: Terminal) -> None:
        if terminal in self._stdout_terminals:
            self._stdout_terminals.remove(terminal)

    def release_stderr_terminal(self, terminal: Terminal) -> None:
        if terminal in self._stderr_terminals:
            self._stderr_terminals.remove(terminal)

    def register_terminal(self, terminal: Terminal) -> None:
        self.register_stdout_terminal(terminal=terminal)
        self.register_stderr_terminal(terminal=terminal)

    def release_terminal(self, terminal: Terminal) -> None:
        self.release_stdout_terminal(terminal=terminal)
        self.release_stderr_terminal(terminal=terminal)

    @property
    def is_busy(self):
        return self._busy
