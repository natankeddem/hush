import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *


class Connections(Tab):
    def __init__(self):
        self._server_card = None
        self._servers_card = None
        self._server_column = None
        self._name = ""
        super().__init__()

    def _tab_populate(self):
        self._server_card = ui.card().style("min-width: 700px").classes("justify-center no-shadow border-[2px]")
        self._card_populate()
        self._servers_card = ui.card().style("min-width: 700px").classes("justify-center no-shadow border-[2px]")
        with self._servers_card:
            self._servers_column = ui.column().classes("w-full")
            with self._servers_column:
                ui.label("Servers").classes("self-center text-h6")

    def _card_populate(self, name=""):
        with self._server_card:
            ui.input(label="Name (Required)", value=name, on_change=lambda e: self._name_changed(e.value)).classes(
                "w-full"
            )
            with ui.row().classes("w-full justify-center"):
                with ui.card().classes("w-full justify-center no-shadow border-[2px]"):
                    self._server_column = ui.column().classes("w-full justify-center")
                    self._column_populate()

    def _column_populate(self):
        with self._server_column:
            ui.label("Credentials").classes("self-center text-h6")
            with ui.tabs().classes("w-full items-center") as cons:
                oob_tab = ui.tab("OOB")
                os_tab = ui.tab("OS")
            with ui.tab_panels(cons, value=oob_tab, animated=False).classes("w-full items-center").style(
                "min-height: 200px"
            ):
                if self._name in configs:
                    with ui.tab_panel(oob_tab):
                        oob_address = ui.input(
                            label="Address", value=configs[self._name].get("oob_address", "")
                        ).classes("w-full")
                        oob_username = ui.input(
                            label="Username", value=configs[self._name].get("oob_username", "")
                        ).classes("w-full")
                        oob_password = (
                            ui.input(label="Password", value=configs[self._name].get("oob_password", ""))
                            .classes("w-full")
                            .props("type=password")
                        )
                    with ui.tab_panel(os_tab):
                        os_address = ui.input(label="Address", value=configs[self._name].get("os_address", "")).classes(
                            "w-full"
                        )
                        os_username = ui.input(
                            label="Username", value=configs[self._name].get("os_username", "")
                        ).classes("w-full")
                        os_password = (
                            ui.input(label="Password", value=configs[self._name].get("os_password", ""))
                            .classes("w-full")
                            .props("type=password")
                        )
                else:
                    with ui.tab_panel(oob_tab):
                        oob_address = ui.input(label="Address").classes("w-full")
                        oob_username = ui.input(label="Username").classes("w-full")
                        oob_password = ui.input(label="Password").classes("w-full").props("type=password")
                    with ui.tab_panel(os_tab):
                        os_address = ui.input(label="Address").classes("w-full")
                        os_username = ui.input(label="Username").classes("w-full")
                        os_password = ui.input(label="Password").classes("w-full").props("type=password")
            server_add = ui.button(
                "",
                on_click=lambda: self._save_connection(
                    oob_address=oob_address.value,
                    oob_username=oob_username.value,
                    oob_password=oob_password.value,
                    os_address=os_address.value,
                    os_username=os_username.value,
                    os_password=os_password.value,
                ),
            ).classes("self-center")
            with server_add:
                ui.icon("save")

    def _name_changed(self, name):
        self._name = name
        if name in configs:
            self._server_column.clear()
            self._column_populate()
        else:
            self._server_column.clear()
            self._column_populate()

    def _save_connection(self, oob_address, oob_username, oob_password, os_address, os_username, os_password):
        if self._name != "":
            configs[self._name]["oob_address"] = oob_address
            configs[self._name]["oob_username"] = oob_username
            configs[self._name]["oob_password"] = oob_password
            configs[self._name]["os_address"] = os_address
            configs[self._name]["os_username"] = os_username
            configs[self._name]["os_password"] = os_password
            app.storage.general[configs_version_string] = configs.to_dict()
            tabs.add_server(self._name)

    def _recall_server(self, name):
        self._name = name
        self._server_card.clear()
        self._card_populate(name)

    def _add_server_content(self, name, row):
        row.classes("justify-between")
        button = ui.button(name, on_click=lambda: self._recall_server(name)).classes("q-ma-sm")
        with ui.row().classes("flex-center"):
            ui.number(
                label="Rate",
                value=configs[name].get("rate", 10),
                min=0,
                max=3600,
                step=1,
                format="%.0f",
                suffix="s",
                on_change=lambda e: self._set_rate(name, e.value),
            ).style("max-width: 100px").props("outlined dense").classes("text-right q-pa-xs q-ma-xs")
            button = ui.button(on_click=lambda: tabs.remove_server(name)).classes("q-ma-sm")
            with button:
                ui.icon("delete").classes("text-h5")

    def _set_rate(self, name, rate):
        configs[name]["rate"] = rate
        app.storage.general[configs_version_string] = configs.to_dict()

    def handle_connection(self):
        for name in configs.keys():
            tabs.add_server(name)
