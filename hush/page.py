import asyncio
from nicegui import app, Client, ui  # type: ignore
from hush import elements as el
from hush.drawer import Drawer
from hush.content import Content
from hush.interfaces import cli
import logging

logger = logging.getLogger(__name__)


def build():
    @ui.page("/", response_timeout=30)
    async def index(client: Client) -> None:
        el.load_element_css()
        ui.colors(
            primary=el.orange,
            secondary=el.orange,
            accent=el.orange,
            dark=el.dark,
            positive="#21BA45",
            negative="#C10015",
            info="#5C8984",
            warning="#F2C037",
        )
        column = ui.column()
        content = Content()
        drawer = Drawer(column, content.host_selected, content.hide)
        drawer.build()
        await content.build()
