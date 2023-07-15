import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *


class Connections(Tab):
    def __init__(self):
        super().__init__()
        self._name = None
        self.server_card = None
        self.servers_card = None
        self.servers_column = None
        self.server_column = None

    def tab_populate(self):
        self.server_card = ui.card().style("min-width: 600px").classes("justify-center")
        self.card_populate()
        self.servers_card = ui.card().style("min-width: 600px").classes("justify-center")
        with self.servers_card:
            self.servers_column = ui.column().classes("w-full")
            with self.servers_column:
                ui.label("Servers").classes("self-center text-h6")

    def card_populate(self, name=""):
        with self.server_card:
            self._name = ui.input(label="Name", value=name, on_change=lambda v: self.named_changed(v)).classes("w-full")
            self.server_column = ui.column().classes("w-full justify-center")
            self.column_populate()

    def column_populate(self):
        with self.server_column:
            with ui.tabs().classes("w-full items-center") as cons:
                oob_tab = ui.tab("OOB")
                ssh_tab = ui.tab("SSH")
            with ui.tab_panels(cons, value=oob_tab, animated=False).classes("w-full items-center").style(
                "min-height: 200px"
            ):
                if self._name.value in configs:
                    with ui.tab_panel(oob_tab):
                        oob_address = ui.input(
                            label="Address", value=configs[self._name.value].get("oob_address", "")
                        ).classes("w-full")
                        oob_username = ui.input(
                            label="Username", value=configs[self._name.value].get("oob_username", "")
                        ).classes("w-full")
                        oob_password = (
                            ui.input(label="Password", value=configs[self._name.value].get("oob_password", ""))
                            .classes("w-full")
                            .props("type=password")
                        )
                    with ui.tab_panel(ssh_tab):
                        ssh_address = ui.input(
                            label="Address", value=configs[self._name.value].get("ssh_address", "")
                        ).classes("w-full")
                        ssh_username = ui.input(
                            label="Username", value=configs[self._name.value].get("ssh_username", "")
                        ).classes("w-full")
                        ssh_password = (
                            ui.input(label="Password", value=configs[self._name.value].get("ssh_password", ""))
                            .classes("w-full")
                            .props("type=password")
                        )
                else:
                    with ui.tab_panel(oob_tab):
                        oob_address = ui.input(label="Address").classes("w-full")
                        oob_username = ui.input(label="Username").classes("w-full")
                        oob_password = ui.input(label="Password").classes("w-full").props("type=password")
                    with ui.tab_panel(ssh_tab):
                        ssh_address = ui.input(label="Address").classes("w-full")
                        ssh_username = ui.input(label="Username").classes("w-full")
                        ssh_password = ui.input(label="Password").classes("w-full").props("type=password")
            server_add = ui.button(
                "",
                on_click=lambda: self.save_connection(
                    name=self._name.value,
                    oob_address=oob_address.value,
                    oob_username=oob_username.value,
                    oob_password=oob_password.value,
                    ssh_address=ssh_address.value,
                    ssh_username=ssh_username.value,
                    ssh_password=ssh_password.value,
                ),
            ).classes("self-center")
            with server_add:
                ui.icon("save").classes("text-h7")

    def named_changed(self, name):
        if name.value in configs:
            self.server_column.clear()
            self.column_populate()
        else:
            self.server_column.clear()
            self.column_populate()

    def save_connection(self, name, oob_address, oob_username, oob_password, ssh_address, ssh_username, ssh_password):
        if name != "":
            configs[name]["oob_address"] = oob_address
            configs[name]["oob_username"] = oob_username
            configs[name]["oob_password"] = oob_password
            configs[name]["ssh_address"] = ssh_address
            configs[name]["ssh_username"] = ssh_username
            configs[name]["ssh_password"] = ssh_password
            app.storage.general["servers"] = configs.to_dict()
            self.add_server_to_tabs(name)

    def recall_server(self, name):
        self.server_card.clear()
        self.card_populate(name)

    def add_server_to_tab(self, name):
        row = add_row(name=name, column=self.servers_column)
        if row is not None:
            with row.classes("justify-between"):
                button = ui.button(
                    name,
                    on_click=lambda button: self.recall_server(name=button.sender.parent_slot.parent.default_slot.name),
                ).classes("q-ma-sm")
                button = ui.button(
                    on_click=lambda button: self.remove_server_from_tabs(
                        name=button.sender.parent_slot.parent.default_slot.name
                    )
                ).classes("q-ma-sm")
                with button:
                    ui.icon("delete").classes("text-h7")

    def remove_server_from_tab(self, name):
        remove_row(name, self.servers_column)

    def handle_connection(self):
        for name in configs.keys():
            self.add_server_to_tabs(name)
