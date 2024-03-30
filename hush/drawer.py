from typing import Optional
from nicegui import ui  # type: ignore
from hush import elements as el
from hush import storage
from hush.hardware import factory
from hush.interfaces import ssh
from hush.tabs import Tab

import logging

logger = logging.getLogger(__name__)


class Drawer(object):
    def __init__(self, main_column, on_click, hide_content) -> None:
        self._on_click = on_click
        self._hide_content = hide_content
        self._main_column = main_column
        self._header_row = None
        self._table = None
        self._name = ""
        self._hostname = ""
        self._username = ""
        self._password = ""
        self._buttons = {}
        self._selection_mode = None

    def build(self):
        def toggle_drawer():
            if chevron._props["icon"] == "chevron_left":
                content.visible = False
                drawer.props("width=0")
                chevron.props("icon=chevron_right")
                chevron.style("top: 16vh").style("right: -24px").style("height: 16vh")
            else:
                content.visible = True
                drawer.props("width=200")
                chevron.props("icon=chevron_left")
                chevron.style("top: 16vh").style("right: -12px").style("height: 16vh")

        with ui.left_drawer(top_corner=True).props("width=226 behavior=desktop bordered").classes("q-pa-none") as drawer:
            with ui.column().classes("h-full w-full q-py-xs q-px-md") as content:
                self._header_row = el.WRow().classes("justify-between")
                self._header_row.tailwind().height("12")
                with self._header_row:
                    with ui.row():
                        el.IButton(icon="add", on_click=self._display_host_dialog)
                        self._buttons["remove"] = el.IButton(icon="remove", on_click=lambda: self._modify_host("remove"))
                        self._buttons["edit"] = el.IButton(icon="edit", on_click=lambda: self._modify_host("edit"))
                    ui.label(text="HOSTS").classes("text-secondary")
                self._table = (
                    ui.table(
                        [
                            {
                                "name": "name",
                                "label": "Name",
                                "field": "name",
                                "required": True,
                                "align": "center",
                                "sortable": True,
                            }
                        ],
                        [],
                        row_key="name",
                        pagination={"rowsPerPage": 0, "sortBy": "name"},
                        on_select=lambda e: self._selected(e),
                    )
                    .on("rowClick", self._clicked, [[], ["name"], None])
                    .props("dense flat bordered binary-state-sort hide-header hide-pagination hide-selected-bannerhide-no-data")
                )
                self._table.tailwind.width("full")
                self._table.visible = False
                for name in storage.hosts.keys():
                    self._add_host_to_table(name)
            chevron = ui.button(icon="chevron_left", color=None, on_click=toggle_drawer).props("padding=0px")
            chevron.classes("absolute")
            chevron.style("top: 16vh").style("right: -12px").style("background-color: #0E1210 !important").style("height: 16vh")
            chevron.tailwind.border_color("[#E97451]")
            chevron.props(f"color=primary text-color=accent")

    def _add_host_to_table(self, name):
        if len(name) > 0:
            for row in self._table.rows:
                if name == row["name"]:
                    return
            self._table.add_rows({"name": name})
            self._table.visible = True

    async def _display_host_dialog(self, name=""):
        save = None

        async def send_key():
            s = ssh.Ssh(host=host_input.value, hostname=os_hostname_input.value, username=os_username_input.value, password=os_password_input.value)
            result = await s.send_key()
            if result.stdout.strip() != "":
                el.Notification(result.stdout.strip(), multi_line=True, type="positive")
                os_password_input.value = None
            if result.stderr.strip() != "":
                el.Notification(result.stderr.strip(), multi_line=True, type="negative")

        with ui.dialog() as host_dialog, el.Card():
            with el.DBody(height="[95vh]", width="[360px]"):
                with el.WColumn():
                    all_hosts = list(storage.hosts.keys())
                    for host in list(storage.hosts.keys()):
                        all_hosts.append(host.replace(" ", ""))
                    if name != "":
                        if name in all_hosts:
                            all_hosts.remove(name)
                        if name.replace(" ", "") in all_hosts:
                            all_hosts.remove(name.replace(" ", ""))

                    def host_check(value: str) -> Optional[bool]:
                        spaceless = value.replace(" ", "")
                        for invalid_value in all_hosts:
                            if invalid_value == spaceless:
                                return False
                        return None

                    host_input = el.VInput(label="Host", value=" ", invalid_characters="""'`"$\;&<>|(){}""", invalid_values=all_hosts, check=host_check)
                    with ui.tabs().classes("w-full") as tabs:
                        oob = ui.tab("OOB")
                        os = ui.tab("OS")
                    with ui.tab_panels(tabs, value=oob).classes("w-full"):
                        with ui.tab_panel(oob):
                            oob_hostname_input = el.VInput(label="Hostname", value=" ", invalid_characters="""!@#$%^&*'`"\/:;<>|(){}-_=+[],?~""")
                            oob_username_input = el.DInput(label="Username", value=" ")
                            oob_password_input = el.DInput(label="Password", value=" ").props("type=password")
                        with ui.tab_panel(os):
                            os_hostname_input = el.VInput(label="Hostname", value=" ", invalid_characters="""!@#$%^&*'`"\/:;<>|(){}-_=+[],?~""")
                            os_username_input = el.DInput(label="Username", value=" ")
                            with el.Card() as c:
                                c.tailwind.width("full")
                                os_password_input = el.DInput(label="Password", value=" ").props("type=password")
                                send_ea = el.ErrorAggregator(host_input, os_hostname_input, os_username_input, os_password_input)
                                el.DButton("SEND KEY", on_click=send_key).bind_enabled_from(send_ea, "no_errors").tailwind.width("full")
                            with el.Card() as c:
                                c.tailwind.width("full")
                                with ui.scroll_area() as s:
                                    s.tailwind.height("[100px]")
                                    public_key = await ssh.get_public_key("data")
                                    ui.label(public_key).classes("text-secondary break-all")
                save_ea = el.ErrorAggregator(host_input)
                el.DButton("SAVE", on_click=lambda: host_dialog.submit("save")).bind_enabled_from(save_ea, "no_errors")
            host_input.value = name
            if name != "":
                s = ssh.Ssh(name)
                oob_hostname_input.value = storage.host(name)["oob"]["hostname"]
                oob_username_input.value = storage.host(name)["oob"]["username"]
                oob_password_input.value = storage.host(name)["oob"]["password"]
                os_hostname_input.value = s.hostname
                os_username_input.value = s.username
                os_password_input.value = storage.host(name)["os"]["password"]

        result = await host_dialog
        if result == "save":
            host = host_input.value.strip()
            if len(host) > 0:
                ssh.Ssh(name).remove()
                ssh.Ssh(f"{name}_oob").remove()
                if name in storage.hosts:
                    del storage.hosts[name]
                for row in self._table.rows:
                    if name == row["name"]:
                        self._table.remove_rows(row)
                storage.host(host)["oob"]["hostname"] = oob_hostname_input.value
                storage.host(host)["oob"]["username"] = oob_username_input.value
                storage.host(host)["oob"]["password"] = oob_password_input.value
                if os_password_input.value is None:
                    storage.host(host)["os"]["password"] = None
                else:
                    storage.host(host)["os"]["password"] = None if os_password_input.value.strip() == "" else os_password_input.value.strip()
                ssh.Ssh(host, hostname=os_hostname_input.value, username=os_username_input.value)
                ssh.Ssh(f"{host }_oob", hostname=oob_hostname_input.value, username=oob_username_input.value)
                self._add_host_to_table(host)
                await factory.Factory.remove_host(name)

    def _modify_host(self, mode):
        self._hide_content()
        self._selection_mode = mode
        if mode is None:
            self._table._props["selected"] = []
            self._table.props("selection=none")
            for icon, button in self._buttons.items():
                button.props(f"icon={icon}")
        elif self._buttons[mode]._props["icon"] == "close":
            self._selection_mode = None
            self._table._props["selected"] = []
            self._table.props("selection=none")
            for icon, button in self._buttons.items():
                button.props(f"icon={icon}")
        else:
            self._table.props("selection=single")
            for icon, button in self._buttons.items():
                if mode == icon:
                    button.props("icon=close")
                else:
                    button.props(f"icon={icon}")

    async def _selected(self, e):
        self._hide_content()
        if self._selection_mode == "edit":
            if len(e.selection) > 0:
                await self._display_host_dialog(name=e.selection[0]["name"])
        if self._selection_mode == "remove":
            if len(e.selection) > 0:
                for row in e.selection:
                    ssh.Ssh(row["name"]).remove()
                    ssh.Ssh(f"{row['name']}_oob").remove()
                    if row["name"] in storage.hosts:
                        del storage.hosts[row["name"]]
                    self._table.remove_rows(row)
        self._modify_host(None)

    async def _clicked(self, e):
        if "name" in e.args[1]:
            host = e.args[1]["name"]
            if self._on_click is not None:
                await self._on_click(host)
