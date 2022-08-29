import math
import logging
from enum import Enum
from typing import Optional, cast
from dataclasses import dataclass

from ialib.instruments.types import InstrumentInterface

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HP34401AError:
    code: int
    text: str
    raw_str: str


class HP34401AFunction(Enum):
    """HP34401A Function Enum"""

    VDC = "VOLT"
    VAC = "VOLT:AC"
    IDC = "CURR"
    IAC = "CURR:AC"
    OHM2W = "RES"
    OHM4W = "FRES"
    FREQ = "FREQ"
    PERIOD = "PER"
    CONT = "CONT"  # Continuity
    DIODE = "DIOD"


class HP34401AInput(Enum):
    """HP34401A Input Enum"""

    FRONT = "FRON"
    REAR = "REAR"


HP34401A_MAX_DIGITS = 6
HP34401A_MIN_DIGITS = 4


class HP34401A:
    on_off_lut: dict[bool, str] = {True: "ON", False: "OFF"}
    on_off_inv: dict[str, bool] = {"1": True, "0": False}

    def __init__(self, ins: InstrumentInterface):
        self.ins = ins

    def _write_data(self, dat: str) -> None:
        logger.debug(f"Write: {dat}")
        # Mypy does not pickup this method
        self.ins.write(dat)  # type: ignore

    def _read_data(self) -> str:
        # Mypy does not pickup this method
        dat = self.ins.read()  # type: ignore
        logger.debug(f"Read: {dat}")
        return dat

    def _query_data(self, dat: str) -> str:
        logger.debug(f"Query Send: {dat}")
        # Mypy does not pickup this method
        ret = self.ins.query(dat)  # type: ignore
        logger.debug(f"Query Get: {ret}")
        return ret

    def reset(self) -> None:
        self._write_data("*RST")
        self._write_data("*CLS")

    def beep(self):
        """The instrument returns a single beep immediately."""
        self._write_data("SYST:BEEP")

    @property
    def beeper(self) -> bool:
        """Switches the front panel control beeper on or off."""
        res = self._query_data("SYST:BEEP:STAT?")
        return self.on_off_inv[res.strip()]

    @beeper.setter
    def beeper(self, val: bool) -> None:
        """Switches the front panel control beeper on or off."""
        self._write_data(f"SYST:BEEP:STAT {self.on_off_lut[val]}")

    @property
    def data(self) -> float:
        """Reads measurement data from the instrument."""
        val = self._query_data("READ?")
        if '"' in val:
            logger.debug("data Re-Read")
            val = self._query_data("READ?")
        if val is None:
            return math.nan
        val_f = float(val.split()[-1])
        if val_f == 9.9e37:
            return math.inf
        return val_f

    @property
    def mode(self) -> HP34401AFunction:
        return HP34401AFunction(
            self._query_data("CONF?").strip().strip('"').strip().split(" ")[0]
        )

    @mode.setter
    def mode(self, val: HP34401AFunction) -> None:
        self._write_data(f":CONF:{val.value}")

    @property
    def null(self) -> bool:
        """Status of the NULL function"""
        res = self._query_data(":CALC:STAT?")
        return self.on_off_inv[res.strip()]

    @null.setter
    def null(self, val: bool) -> None:
        """Status of the NULL function"""
        if val:
            # If enabling null, make a reading
            self._write_data(f"CALC:FUNC NULL")
            self._write_data(f"CALC:STAT ON")
            # Trigger a reading to activate NULL
            self.data
        else:
            self._write_data(f"CALC:STAT OFF")

    @property
    def null_ofst(self) -> float:
        """Readback the null offset (nan if not in null mode)."""
        return float(self._query_data("CALC:NULL:OFFS?"))

    @null_ofst.setter
    def null_ofst(self, val: float) -> None:
        """Set the null offset."""
        self._write_data(f"CALC:NULL:OFFS {val:.8E}")

    @property
    def display(self) -> bool:
        """Display enable status."""
        res = self._query_data(":DISP?")
        return self.on_off_inv[res.strip()]

    @display.setter
    def display(self, val: bool) -> None:
        """Display enable status."""
        self._write_data(f":DISP {self.on_off_lut[val]}")

    @property
    def display_text(self) -> str:
        """Display enable status."""
        res = self._query_data(":DISP:TEXT?")
        return res.strip().strip('"')

    @display_text.setter
    def display_text(self, val: str) -> None:
        """Display enable status."""
        self._write_data(f':DISP:TEXT "{val}"')

    @property
    def input(self) -> HP34401AInput:
        """HP34401A input terminal selection front or rear."""
        return HP34401AInput(self._query_data(":ROUT:TERM?").strip().strip('"').strip())

    @property
    def error(self) -> Optional[HP34401AError]:
        """Pop the latest error from the error stack; None if there are no errors."""
        res = self._query_data("SYST:ERR?").strip()
        raw_code, val = res.split(",")
        code = int(raw_code.strip())
        val = val.strip('"')
        if code == 0:
            return None
        return HP34401AError(code=code, text=val, raw_str=res)

    @property
    def range(self) -> float:
        """Get the range of the system (returned as the maxvalue it can read)."""
        curr_mode = self.mode
        return float(self._query_data(f":{curr_mode.value}:RANG?"))

    @range.setter
    def range(self, val: float) -> None:
        """
        Set the range of the system; the value you pass is guaranteed to be in range
        (as long as its in the system range).

        NOTE: This command clears the error queue in order to tell if you commanded an invalid error.

        :param float val: Range to set the instrument to
        :raises ValueError: If the commanded range is out of range
        :return: None
        """
        self._write_data("*CLS")
        if val < 0:
            raise ValueError("Range must be positive!")
        curr_mode = self.mode
        if math.isinf(val):
            self._write_data(f":{curr_mode.value}:RANG MAX")
        else:
            self._write_data(f":{curr_mode.value}:RANG {val:.2E}")
        err = self.error
        if err is not None and err.code == -222:
            raise ValueError(f"Range {val} is out of range! ({err.raw_str})")

    @property
    def auto_range(self) -> bool:
        """Auto range state."""
        curr_mode = self.mode
        res = self._query_data(f":{curr_mode.value}:RANG:AUTO?")
        return self.on_off_inv[res.strip()]

    @auto_range.setter
    def auto_range(self, val: bool) -> None:
        """Auto range state."""
        curr_mode = self.mode
        self._write_data(f":{curr_mode.value}:RANG:AUTO {self.on_off_lut[val]}")

    @property
    def nplc(self) -> float:
        """Number of power line cycles state."""
        curr_mode = self.mode
        return float(self._query_data(f":{curr_mode.value}:NPLC?").strip())

    @nplc.setter
    def nplc(self, val: float) -> None:
        """Number of power line cycles state."""
        curr_mode = self.mode
        self._write_data(f":{curr_mode.value}:NPLC {val:+.5E}")

    @property
    def azero(self) -> bool:
        """Status of the auto zero function."""
        res = self._query_data(":ZERO:AUTO?")
        return self.on_off_inv[res.strip()]

    @azero.setter
    def azero(self, val: bool) -> None:
        """Status of the auto zero function."""
        self._write_data(f":ZERO:AUTO {self.on_off_lut[val]}")


if __name__ == "__main__":
    import pyvisa

    logging.basicConfig()
    logger.level = logging.DEBUG

    rm = pyvisa.ResourceManager()
    ins_interface = cast(
        pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::26::INSTR")
    )

    ins = HP34401A(ins_interface)
    ins.reset()
    ins.mode = HP34401AFunction.VDC
    ins.nplc = 100
    print(f"{ins.data=}")
    print(f"{ins.data=}")
    print(f"{ins.range=}")
