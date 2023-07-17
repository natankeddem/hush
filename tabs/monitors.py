import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *


class Monitors(Tab):
    def __init__(self):
        super().__init__()
        self._name = None
        self._card = None
        self._column = None
        self._expansions = dict()

    def tab_populate(self):
        self._card = ui.card().style("min-width: 600px").classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._column = ui.column().classes("w-full")

    def add_server_to_tab(self, name):
        row = add_row(name=name, column=self._column)
        if row is not None:
            with row:
                expansion = ui.expansion(name, icon="query_stats").classes("w-full")
                self._expansions[name] = expansion
                with expansion:
                    time = ui.label()
                    time.default_slot.name = "time"
                    temp = ui.label()
                    temp.default_slot.name = "temp"
                    adjust = ui.label()
                    adjust.default_slot.name = "adjust"
                    status = ui.label()
                    status.default_slot.name = "status"

    def remove_server_from_tab(self, name):
        remove_row(name, self._column)

    def update_field(self, name, field, value):
        if name in self._expansions:
            for c in self._expansions[name].default_slot.children:
                if c.default_slot.name == field:
                    c.text = value
