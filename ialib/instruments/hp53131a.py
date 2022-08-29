from dataclasses import dataclass
from typing import Union, Optional
from enum import Enum
import math
import logging
import socket

from ialib.interfaces.plx_gpib_ethernet import PlxGPIBEthDevice, plx_get_first

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HP53131AError:
    code: int
    text: str
    raw_str: str


class HP53131A(PlxGPIBEthDevice):
    on_off_lut = {True: "ON", False: "OFF"}
    on_off_inv = {"1": True, "0": False}

    def __init__(self, host: str, address: int = 3):
        super().__init__(host=host, address=address, timeout=2)
        self.connect()

    def _write_data(self, dat: str) -> None:
        self.write(dat)

    def _read_data(self) -> str:
        return self.read()

    def _query_data(self, dat: str, retry_limit: int = 10) -> str:
        self.write(dat)
        for _ in range(retry_limit - 1):
            try:
                return self.read()
            except socket.timeout:
                pass
        return self.read()

    def reset(self) -> None:
        self._write_data("*RST")
        self._write_data("*CLS")

    def abort(self) -> None:
        """Aborts measurement in progress"""
        self._write_data("ABOR")

    @property
    def data(self) -> float:
        """Triggers and reads measurement data from the instrument."""
        try:
            data = float(self._query_data("READ?"))
        except socket.timeout:
            data = math.nan
        if data == 9.91e37:
            return math.nan
        return data

    @property
    def error(self) -> Optional[HP53131AError]:
        """Pop the latest error from the error stack; None if there are no errors."""
        res = self._query_data("SYST:ERR?").strip()
        code, val = res.split(",")
        code = int(code.strip())
        val = val.strip('"')
        if code == 0:
            return None
        return HP53131AError(code=code, text=val, raw_str=res)


if __name__ == "__main__":
    import time
    from quantiphy import Quantity

    logging.basicConfig()
    logger.level = logging.DEBUG

    ins = HP53131A(host=plx_get_first(), address=3)
    ins.reset()
    print(ins.data)
    print(ins.error)
