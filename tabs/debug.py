import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *


class Debug(Tab):
    def __init__(self):
        self._name = None
        self._card = None
        self._column = None
        self._log = None
        super().__init__()

    def _tab_populate(self):
        self._card = ui.card().classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._column = ui.column().classes("w-full")
            with self._column:
                self._log = ui.log(max_lines=10).style("min-width: 700px").style("min-height: 400px")

    def update_log(self):
        if self._log is not None:
            self._log.push(f"{configs}")
