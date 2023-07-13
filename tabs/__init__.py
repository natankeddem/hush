import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
import nicegui as ng
from addict import Dict as AdDict

if app.storage.general.get("servers", None) is None:
    app.storage.general["servers"] = AdDict()
configs = AdDict(dict(app.storage.general["servers"]))
tab_instances = dict()


def add_row(name, column):
    add = True
    for r in column.default_slot.children:
        if type(r) is ng.elements.row.Row:
            if name == r.default_slot.name:
                add = False
    if add is True:
        with column:
            row = ui.row().classes("w-full bg-secondary items-center rounded-borders")
            row.default_slot.name = name
            return row


def remove_row(name, column):
    for r in column.default_slot.children:
        if type(r) is ng.elements.row.Row:
            if name == r.default_slot.name:
                column.remove(r)


class Tab:
    def __init__(self):
        tab_instances[self.__class__.__name__] = self

    def add_server_to_tab(self, name):
        pass

    def add_server_to_tabs(self, name, tabs=None):
        for class_name, instance in tab_instances.items():
            if tabs is None or class_name in tabs:
                instance.add_server_to_tab(name)

    def remove_server_from_tab(self, name):
        pass

    def remove_server_from_tabs(self, name, tabs=None):
        if tabs is None:
            if name in configs:
                del configs[name]
            if name in app.storage.general["servers"]:
                del app.storage.general["servers"][name]
        for class_name, instance in tab_instances.items():
            if tabs is None or class_name in tabs:
                instance.remove_server_from_tab(name)
