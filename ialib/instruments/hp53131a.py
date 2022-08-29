import math
import socket
import logging
from typing import Optional, cast
from dataclasses import dataclass

from ialib.instruments.types import InstrumentInterface
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

    def __init__(self, ins: InstrumentInterface):
        self.ins = ins

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)

    def _read_data(self) -> str:
        return self.ins.read()

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

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
        raw_code, val = res.split(",")
        code = int(raw_code.strip())
        val = val.strip('"')
        if code == 0:
            return None
        return HP53131AError(code=code, text=val, raw_str=res)


if __name__ == "__main__":
    import pyvisa

    logging.basicConfig()
    logger.level = logging.DEBUG

    rm = pyvisa.ResourceManager()
    ins_interface = cast(
        pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::3::INSTR")
    )

    ins = HP53131A(ins_interface)
    ins.reset()
    print(ins.data)
    print(ins.error)
