import os

os.environ["MPLCONFIGDIR"] = os.getcwd() + "/mpl/"
import mylogging
import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from tabs.connections import Connections
from tabs.sensors_ctrls import SensorsCtrls
from tabs.algorithms import Algorithms
from tabs.monitors import Monitors
from tabs.debug import Debug
import control

ui.colors(primary="#424242", secondary="#323232", accent="#424242")


@ui.page("/shutdown")
def shutdown():
    app.shutdown()


with ui.column().classes("w-full items-center") as tab_header_col:
    with ui.tabs().classes("w-full items-center") as tabs:
        connections_tab = ui.tab("Connections")
        sensors_ctrls_tab = ui.tab("Sensors & Ctrls")
        algorithms_tab = ui.tab("Algorithms")
        monitors_tab = ui.tab("Monitors")
        if os.environ.get("DISPLAY_DEBUG_TAB", "FALSE") == "TRUE":
            debug_tab = ui.tab("Debug")
with ui.column().classes("w-full items-center") as tabs_content_col:
    with ui.tab_panels(tabs, value=connections_tab, animated=False).classes("column items-center justify-center"):
        with ui.tab_panel(connections_tab).style("min-height: 600px"):
            connections = Connections()
        with ui.tab_panel(sensors_ctrls_tab).style("min-height: 600px"):
            sensors_ctrls = SensorsCtrls()
        with ui.tab_panel(algorithms_tab).style("min-height: 600px"):
            algorithms = Algorithms()
        with ui.tab_panel(monitors_tab).style("min-height: 600px"):
            monitors = Monitors()
        if os.environ.get("DISPLAY_DEBUG_TAB", "FALSE") == "TRUE":
            with ui.tab_panel(debug_tab).style("min-height: 600px"):
                debug = Debug()

app.on_connect(connections.handle_connection)
if os.environ.get("DISPLAY_DEBUG_TAB", "FALSE") == "TRUE":
    ui.timer(3, debug.update_log)
launcher = control.Launcher(monitor_tab=monitors)
ui.timer(1, launcher.run)
app.on_shutdown(launcher.close)
ui.run(title="hush", favicon="🙉", reload=False, dark=True)
