import asyncio
from nicegui import ui  # type: ignore
from hush import elements as el
import hush.logo as logo
from hush.tabs import Tab
from hush.tabs.monitor import Monitor
from hush.tabs.configure import Configure
from hush.tabs.control import Control
import logging

logger = logging.getLogger(__name__)


class Content:
    def __init__(self) -> None:
        self._header = None
        self._tabs = None
        self._tab = {}
        self._spinner = None
        self._host = None
        self._tab_panels = None
        self._grid = None
        self._tab_panel = {}
        self._host = None
        self._tasks = []
        self._manage = None
        self._automation = None
        self._history = None

    async def build(self):
        self._header = ui.header(bordered=True).classes("bg-dark q-pt-sm q-pb-xs")
        self._header.tailwind.border_color(f"[{el.orange}]").min_width("[920px]")
        self._header.visible = False
        with self._header:
            with ui.row().classes("w-full h-16 justify-between items-center"):
                self._tabs = ui.tabs()
                with self._tabs:
                    self._tab["monitor"] = ui.tab(name="Monitor").classes("text-secondary")
                    self._tab["configure"] = ui.tab(name="Configure").classes("text-secondary")
                    self._tab["control"] = ui.tab(name="Control").classes("text-secondary")
                with ui.row().classes("items-center"):
                    self._host_display = ui.label().classes("text-secondary text-h4")
                    logo.show()
        self._tab_panels = (
            ui.tab_panels(self._tabs, value="Monitor", on_change=lambda e: self._tab_changed(e), animated=False).classes("w-full h-full").bind_visibility_from(self._header)
        )

    async def _tab_changed(self, e):
        pass

    def _build_tab_panels(self):
        self._tab_panels.clear()
        with self._tab_panels:
            self._monitor_content = el.ContentTabPanel(self._tab["monitor"])
            self._configure_content = el.ContentTabPanel(self._tab["configure"])
            self._control_content = el.ContentTabPanel(self._tab["control"])
            with self._monitor_content:
                self._monitor = Monitor(host=self._host)
            with self._configure_content:
                self._configure = Configure(host=self._host, control_rebuild=self.rebuild_control_content)
            with self._control_content:
                self._control = Control(host=self._host)

    async def host_selected(self, name):
        self._host = name
        self._host_display.text = name
        self.hide()
        self._build_tab_panels()
        self._header.visible = True

    def hide(self):
        self._header.visible = False
        self._tab_panels.clear()

    def rebuild_control_content(self):
        self._control_content.clear()
        with self._control_content:
            self._control = Control(host=self._host)
