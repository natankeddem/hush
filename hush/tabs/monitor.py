from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import deque
import asyncio
from datetime import datetime
import time
from nicegui import ui
from . import Tab


last_status: dict = {}
graph_history: dict = {}


@dataclass(kw_only=False)
class Status:
    host: str
    status: bool = False
    speed: Optional[int] = None
    temperatures: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def submit(self) -> None:
        if self.status is True:
            if self.host not in graph_history:
                graph_history[self.host] = {}
            if (len(self.temperatures.keys()) + 1) != len(graph_history[self.host].keys()):
                graph_history[self.host] = {}
                for sensor in self.temperatures.keys():
                    graph_history[self.host][sensor] = deque(maxlen=100)
                graph_history[self.host]["speed"] = deque(maxlen=100)
            for sensor, value in self.temperatures.items():
                graph_history[self.host][sensor].append(value)
            graph_history[self.host]["speed"].append(self.speed)
        last_status[self.host] = self


class Monitor(Tab):
    def __init__(self, host=None) -> None:
        self._time = None
        self._status = None
        self._timestamp = 0
        self._groups = ["speed", "cpu", "pci", "drive", "gpu", "chassis"]
        super().__init__(host)

    def _build(self):
        self._add_labels()
        self._add_chart()

    def _add_labels(self):
        self._time = ui.label()
        self._status = ui.label()

    def _add_chart(self):
        self._chart = ui.highchart(
            {
                "title": False,
                "chart": {
                    "type": "line",
                    "backgroundColor": "#222",
                },
                "xAxis": {
                    "title": {"text": None},
                    "labels": {"enabled": False},
                    "lineColor": "#FFF",
                    "tickColor": "#FFF",
                },
                "yAxis": {
                    "title": {"text": None},
                    "lineColor": "#FFF",
                    "tickColor": "#FFF",
                    "labels": {"style": {"color": "#FFF"}},
                },
                "legend": {"itemStyle": {"color": "#FFF"}},
                "tooltip": {"split": True, "shared": True, "distance": 30, "padding": 5},
                "series": [],
                "credits": {"enabled": False},
            }
        ).classes("w-full h-64")
        for group in self._groups:
            self._chart.options["series"].append(dict({"name": group.title(), "data": None}))
        ui.timer(interval=1, callback=self.update, once=True)

    async def update(self):
        while True:
            if self.host in last_status:
                if last_status[self.host].timestamp > self._timestamp:
                    self._timestamp = last_status[self.host].timestamp
                    time = datetime.fromtimestamp(self._timestamp).strftime("%m/%d/%Y @ %H:%M:%S")
                    self._time.text = f"Last Run Time = {time}"
                    self._status.text = f"Status = {'✅' if last_status[self.host].status is True else '❌'}"
                    if self.host in graph_history:
                        for group in self._groups:
                            if group in graph_history[self.host]:
                                self._chart.options["series"][self._groups.index(group)]["data"] = list(graph_history[self.host][group])
                            else:
                                self._chart.options["series"][self._groups.index(group)]["data"] = None
                        self._chart.update()
            await asyncio.sleep(1)
