from enum import Enum
from typing import Optional
import math
import logging
import socket

from plx_gpib_ethernet import PlxGPIBEthDevice, plx_get_first

logger = logging.getLogger(__name__)


class Fluke8840ARange(Enum):
    """Fluke8840A Range Enum"""

    AUTO = "R0"
    V200mv = "R1"
    R200Ohm = "R1"
    V2V = "R2"
    R2kOhm = "R2"
    V20V = "R3"
    R20kOhm = "R3"
    V200V = "R4"
    R200kOhm = "R4"
    V1000V = "R5"
    R2MOhm = "R5"
    R20MOhm = "R6"
    OFF = "R7"


class Fluke8840AFunction(Enum):
    """Fluke8840A Function Enum"""

    VDC = "F1"
    VAC = "F2"
    OHM2W = "F3"
    OHM4W = "F4"
    MADC = "F5"
    MAAC = "F6"


class Fluke8840ARate(Enum):
    """Fluke8840A Rate Enum"""

    SLOW = "S0"
    MEDIUM = "S1"
    FAST = "S2"


class Fluke8840A(PlxGPIBEthDevice):
    def __init__(self, host: str, address: int = 11):
        super().__init__(host=host, address=address)
        self.connect()
        self._range: Optional[Fluke8840ARange] = None
        self._function: Optional[Fluke8840AFunction] = None
        self._rate: Optional[Fluke8840ARate] = None
        self._offset: Optional[bool] = None
        self._blank: Optional[bool] = None

    def _write_data(self, dat: str) -> None:
        self.write(dat)

    def _read_data(self) -> str:
        return self.read()

    def _query_data(self, dat: str, retry_limit: int = 10) -> str:
        for _ in range(retry_limit - 1):
            try:
                return self.query(dat)
            except socket.timeout:
                pass
        return self.query(dat)

    def reset(self) -> None:
        self._write_data("*")

    @property
    def range(self) -> Optional[Fluke8840ARange]:
        return self._range

    @range.setter
    def range(self, range_set: Fluke8840ARange) -> None:
        self._range = range_set
        self._write_data(range_set.value)

    @property
    def function(self) -> Optional[Fluke8840AFunction]:
        return self._function

    @function.setter
    def function(self, function: Fluke8840AFunction) -> None:
        self._function = function
        self._write_data(function.value)

    @property
    def rate(self) -> Optional[Fluke8840ARate]:
        return self._rate

    @rate.setter
    def rate(self, rate: Fluke8840ARate) -> None:
        self._rate = rate
        self._write_data(rate.value)

    @property
    def offset(self) -> Optional[bool]:
        return self._offset

    @offset.setter
    def offset(self, offset: bool) -> None:
        self._offset = offset
        if offset:
            self._write_data("B1")
        else:
            self._write_data("B0")

    @property
    def blank(self) -> Optional[bool]:
        return self._blank

    @blank.setter
    def blank(self, blank: bool) -> None:
        self._blank = blank
        if blank:
            self._write_data("D1")
        else:
            self._write_data("D0")

    @property
    def data(self) -> float:
        val = self._query_data("?")
        if val is None:
            return math.nan
        val_f = float(val.split()[-1])
        if val_f == 9.99999e9:
            return math.inf
        return val_f


if __name__ == "__main__":
    ins = Fluke8840A(host=plx_get_first(), address=11)
    for _ in range(10):
        print(ins.data)
