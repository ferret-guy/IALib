from dataclasses import dataclass
from typing import Union, Optional
from enum import Enum
import math
import logging

import pyvisa

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class R6581TError:
    code: int
    text: str
    raw_str: str


class R6581TFunction(Enum):
    """R6581T Function Enum"""

    VDC = "VOLT:DC"
    IDC = "CURR:DC"
    IAC = "CURR:AC"
    OHM2W = "RES"
    OHM4W = "FRES"


class R6581TFilter(Enum):
    """R6581T Filter Enum"""

    NONE = "NONE"
    SMOOTHING = "SMO"
    AVERAGE = "AVER"


class R6581TInput(Enum):
    """R6581T Input Enum"""

    FRONT = "FRON"
    REAR = "REAR"


R6581T_MAX_DIGITS = 8
R6581T_MIN_DIGITS = 4


class R6581T:
    on_off_lut: dict[bool, str] = {True: "ON", False: "OFF"}
    on_off_inv: dict[str, bool] = {"1": True, "0": False}

    def __init__(self, host: str, address: int = 24):
        rm = pyvisa.ResourceManager(r"C:\Windows\System32\visa64.dll")
        self.ins = rm.open_resource(f"{host}::{address}::INSTR")
        self._line_freq: Optional[int] = None

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)

    def _read_data(self) -> str:
        return self.ins.read()

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

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
    def mode(self) -> R6581TFunction:
        return R6581TFunction(self._query_data("CONF?").strip().strip('"').strip())

    @mode.setter
    def mode(self, val: R6581TFunction) -> None:
        self._write_data(f":CONF:{val.value}")

    @property
    def null(self) -> bool:
        """Status of the NULL function"""
        res = self._query_data(":CALC:NULL:STATE?")
        return self.on_off_inv[res.strip()]

    @null.setter
    def null(self, val: bool) -> None:
        """Status of the NULL function"""
        self._write_data(f":CALC:NULL:STAT {self.on_off_lut[val]}")

    @property
    def null_ofst(self) -> float:
        """Readback the null offset (nan if not in null mode)."""
        if self.null is True:
            return float(self._query_data(":CALC:NULL:DATA?"))
        return math.nan

    @property
    def filter(self) -> R6581TFilter:
        """Get filter status, R6581TFilter.NONE is not enabled."""
        if self.filter_en is False:
            return R6581TFilter.NONE
        return R6581TFilter(self._query_data(":CALC:DFIL?").strip().strip('"').strip())

    @filter.setter
    def filter(self, val: Union[R6581TFilter, None]) -> None:
        """Set filter status, disables if set to R6581TFilter.NONE, enables otherwise."""
        if val is None:
            val = R6581TFilter.NONE
        if val is R6581TFilter.NONE:
            self.filter_en = False
        self._write_data(f":CALC:DFIL {val.value}")
        self.filter_en = True

    @property
    def filter_en(self) -> bool:
        """Filter enable status, changed by R6581T.filter."""
        res = self._query_data(":CALC:DFIL:STATE?")
        return self.on_off_inv[res.strip()]

    @filter_en.setter
    def filter_en(self, val: bool) -> None:
        """Filter enable status, changed by R6581T.filter."""
        self._write_data(f":CALC:DFIL:STATE {self.on_off_lut[val]}")

    @property
    def filter_len(self) -> Optional[int]:
        """Filter len; -1 if R6581TFilter.NONE; must set AFTER setting the filter mode."""
        filt_mode = self.filter
        if filt_mode is R6581TFilter.NONE:
            return None
        elif filt_mode is R6581TFilter.AVERAGE:
            return int(self._query_data("CALC:DFIL:AVER?").strip().strip('"').strip())
        elif filt_mode is R6581TFilter.SMOOTHING:
            return int(self._query_data("CALC:DFIL:SMO?").strip().strip('"').strip())
        else:
            raise ValueError(f"{filt_mode} is not supported.")

    @filter_len.setter
    def filter_len(self, val: Optional[int]) -> None:
        """Filter len; -1 if R6581TFilter.NONE; must set AFTER setting the filter mode."""
        if val is None:
            self.filter = R6581TFilter.NONE
        elif not 2 <= val <= 100:
            raise ValueError(f"Average of {val} is not in the range 2-100!")
        filt_mode = self.filter
        if filt_mode is R6581TFilter.NONE:
            pass
        elif filt_mode is R6581TFilter.AVERAGE:
            self._write_data(f"CALC:DFIL:AVER {val}")
        elif filt_mode is R6581TFilter.SMOOTHING:
            self._write_data(f"CALC:DFIL:SMO {val}")
        else:
            raise ValueError(f"{filt_mode} is not supported.")

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
    def guard(self) -> bool:
        """Guard enable status; True is short; False is open (floating)."""
        res = self._query_data(":INP:GUARD?")
        if "FLO" in res:
            return False
        if "LOW" in res:
            return True
        raise ValueError(f"{res} is not a valid guard value!")

    @guard.setter
    def guard(self, val: bool) -> None:
        """Guard enable status; True is short; False is open (floating)."""
        if val:
            self._write_data(":INP:GUARD LOW")
        else:
            self._write_data(":INP:GUARD FLO")

    @property
    def input(self) -> R6581TInput:
        """R6581T input terminal selection front or rear."""
        return R6581TInput(self._query_data(":INP:TERM?").strip().strip('"').strip())

    @input.setter
    def input(self, val: R6581TInput) -> None:
        """R6581T input terminal selection front or rear."""
        self._write_data(f":INP:TERM {val.value}")

    @property
    def error(self) -> Optional[R6581TError]:
        """Pop the latest error from the error stack; None if there are no errors."""
        res = self._query_data("SYST:ERR?").strip()
        code, val = res.split(",")
        code = int(code.strip())
        val = val.strip('"')
        if code == 0:
            return None
        return R6581TError(code=code, text=val, raw_str=res)

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
    def digits(self) -> int:
        """Auto range state."""
        curr_mode = self.mode
        return int(self._query_data(f":{curr_mode.value}:DIG?").split(".")[0])

    @digits.setter
    def digits(self, val: int) -> None:
        """Auto range state."""
        curr_mode = self.mode
        if not R6581T_MIN_DIGITS <= val <= R6581T_MAX_DIGITS:
            raise ValueError(f"Number of digits must be between 4 and 8 not {val}!")
        self._write_data(f":{curr_mode.value}:DIG {val}.00")

    @property
    def nplc(self) -> float:
        """Number of power line cycles state."""
        curr_mode = self.mode
        return float(self._query_data(f":{curr_mode.value}:NPLC?").strip())

    @nplc.setter
    def nplc(self, val: float) -> None:
        """Number of power line cycles state."""
        curr_mode = self.mode
        if not 1e-6 * self.line_freq <= val <= 100:
            raise ValueError(f"Number of digits must be between 4 and 8 not {val}!")
        self._write_data(f":{curr_mode.value}:NPLC {val:+.5E}")

    @property
    def int_time(self) -> float:
        """Integration time state."""
        curr_mode = self.mode
        return float(self._query_data(f":{curr_mode.value}:APER?").strip())

    @int_time.setter
    def int_time(self, val: float) -> None:
        """Integration time state."""
        curr_mode = self.mode
        if not 1e-6 <= val <= (1 / self.line_freq) * 100:
            raise ValueError(f"Integration time must be between 4 and 8 not {val}!")
        self._write_data(f":{curr_mode.value}:APER {val:+.5E}")

    @property
    def line_freq(self) -> int:
        """Get the detected line freq."""
        if self._line_freq is None:
            self._line_freq = int(self._query_data(":LFRE?").strip()[:-2])
        return self._line_freq

    @property
    def internal_temp(self) -> float:
        """Get the internal temp (in C)."""
        return float(self._query_data(":ITEM?").strip())

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
    import time
    from quantiphy import Quantity

    logging.basicConfig()
    logger.level = logging.DEBUG

    ins = R6581T(host="GPIB0", address=24)
    ins.reset()
    ins.mode = R6581TFunction.VDC
    ins.digits = 8
    ins.nplc = 100
    print(f"{ins.nplc=}; {Quantity(ins.int_time, 's')}")
    print(f"{ins.data=}")
    print(f"{ins.data=}")
    print(f"{ins.range=}")
    print(f"{ins.digits=}")
