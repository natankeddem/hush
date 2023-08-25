import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
import nicegui as ng
from addict import Dict as AdDict

configs_version = int(101)
configs_version_string = f"config_{configs_version}"
configs = app.storage.general.get(configs_version_string, None)
if configs is None:
    logger.warning(f"Storage version not found, updating version to {configs_version}.")
    logger.warning(f"Connections cleared, repeat setup procedure.")
    app.storage.general[configs_version_string] = dict()
configs = AdDict(dict(app.storage.general[configs_version_string]))


class Server:
    def __init__(self, name):
        self._name = name
        self._row = name

    def add(self, column):
        self._column = column
        with self._column:
            self._row = ui.row().classes("w-full bg-secondary items-center rounded-borders")

    def remove(self):
        if self._column is not None and self._row is not None:
            self._column.remove(self._row)

    @property
    def row(self):
        return self._row


class Tabs:
    def __init__(self):
        self._instances = dict()

    def register_tab(self, name, instance):
        self._instances[name] = instance

    def add_server(self, name, tabs=None):
        for class_name, instance in self._instances.items():
            if tabs is None or class_name in tabs:
                instance.add_server(name)

    def remove_server(self, name, tabs=None):
        if tabs is None:
            if name in configs:
                del configs[name]
            app.storage.general[configs_version_string] = configs.to_dict()
        for class_name, instance in self._instances.items():
            if tabs is None or class_name in tabs:
                instance.remove_server(name)

    def rebuild_server(self, name, tabs):
        self.remove_server(name=name, tabs=tabs)
        self.add_server(name=name, tabs=tabs)


tabs = Tabs()


class Tab:
    def __init__(self):
        tabs.register_tab(self.__class__.__name__, self)
        self._servers = dict()
        self._servers_column = None
        self._tab_populate()

    def add_server(self, name):
        if name not in self._servers:
            self._servers[name] = Server(name=name)
            if self._servers_column is not None:
                self._servers[name].add(column=self._servers_column)
                with self._servers[name].row as row:
                    self._add_server_content(name, row)

    def remove_server(self, name):
        if name in self._servers:
            self._servers[name].remove()
            del self._servers[name]

    def _tab_populate(self):
        pass

    def _add_server_content(self, name, row):
        pass
