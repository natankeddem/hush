import logging

logger = logging.getLogger(__name__)
try:
    from .mysecret import *
except:
    logger.info("mysecret was not loaded")


class Device:
    def __init__(self, address, password, username):
        self._address = address
        self._password = password
        self._username = username
        self._temp = None
        self._adjust = None

    def close(self):
        logger.info(f"The close method is not implemented. {self._address} {self}")

    def get_temp(self):
        logger.info(f"The get_temp method is not implemented. {self._address} {self}")
        return None

    def set_adjust(self, adjust):
        logger.info(f"The set_adjust method is not implemented. {self._address} {self}")
        self._adjust = adjust
