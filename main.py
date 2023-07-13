import mylogging
import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
import nicegui as ng
from collections import defaultdict
import asyncio
import threading
import hardware.fanctrl as fanctrl
import hardware.idrac as idrac
from addict import Dict as AdDict

from tabs.connections import Connections
from tabs.sensors_ctrls import SensorsCtrls
from tabs.algorithms import Algorithms
from tabs.monitors import Monitors
from tabs.debug import Debug
import control

ui.colors(primary="#424242", secondary="#323232", accent="#424242")

with ui.column().classes("w-full items-center") as config_header_col:
    with ui.tabs().classes("w-full items-center") as configs:
        connections_tab = ui.tab("Connections")
        sensors_ctrls_tab = ui.tab("Sensors & Ctrls")
        algorithms_tab = ui.tab("Algorithms")
        monitors_tab = ui.tab("Monitors")
        debug_tab = ui.tab("Debug")
with ui.column().classes("w-full items-center") as config_content_col:
    with ui.tab_panels(configs, value=connections_tab, animated=False).classes("column items-center justify-center"):
        with ui.tab_panel(connections_tab).style("min-height: 600px"):
            connections = Connections()
            connections.tab_populate()
        with ui.tab_panel(sensors_ctrls_tab).style("min-height: 600px"):
            sensors_ctrls = SensorsCtrls()
            sensors_ctrls.tab_populate()
        with ui.tab_panel(algorithms_tab).style("min-height: 600px"):
            algorithms = Algorithms()
            algorithms.tab_populate()
        with ui.tab_panel(monitors_tab).style("min-height: 600px"):
            monitors = Monitors()
            monitors.tab_populate()
        with ui.tab_panel(debug_tab).style("min-height: 600px"):
            debug = Debug()
            debug.tab_populate()

app.on_connect(connections.handle_connection)
ui.timer(3, debug.update_log)
machine = control.Machine(monitor_tab=monitors)
ui.timer(10, machine.run)
app.on_shutdown(machine.close )
ui.run(reload=False, dark=True)
