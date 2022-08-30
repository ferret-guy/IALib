import logging
import warnings
from enum import Enum
from typing import Optional, cast
from dataclasses import dataclass

from ialib.instruments.types import InstrumentInterface

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GWPSMPSUError:
    code: int
    text: str
    raw_str: str


class GWPSMPSURange(Enum):
    """GWPSMPSU Input Enum"""

    LOW = "LOW"
    HIGH = "HIGH"


class GWPSMPSU:
    on_off_lut: dict[bool, str] = {True: "ON", False: "OFF"}
    on_off_inv: dict[str, bool] = {"1": True, "0": False}

    # Range map
    range_map: dict[str, dict[str, GWPSMPSURange]] = {
        "PSM-20d10": {
            "P08V": GWPSMPSURange.LOW,
            "P20V": GWPSMPSURange.HIGH,
        },
        "PSM-3004": {
            "P15V": GWPSMPSURange.LOW,
            "P30V": GWPSMPSURange.HIGH,
        },
        "PSM-6003": {
            "P30V": GWPSMPSURange.LOW,
            "P60V": GWPSMPSURange.HIGH,
        },
    }

    curr_range_map: Optional[dict[str, GWPSMPSURange]]

    def __init__(self, ins: InstrumentInterface, error_check=True):
        """
        Driver for GW Instek PSM-Series DC Supply (PSM-2010, PSM-3004, PSM-6003)

        If error_check is False commands will not be checked for errors after being run.
        """
        self.ins = ins
        try:
            self.model = self._query_data("*IDN?").split(",")[1]
            self.curr_range_map = self.range_map[self.model]
        except (IndexError, KeyError):
            self.model = "Unknown"
            self.curr_range_map = None

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)

    def _read_data(self) -> str:
        return self.ins.read()

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

    def set_iv(self, v: float, i: float):
        self._write_data(f":APPLY {v},{i}")

    @property
    def curr(self):
        """Current set point"""
        self._write_data(":CURR?")
        return float(self._read_data())

    @curr.setter
    def curr(self, val: float):
        """Current set point"""
        self._write_data(f":CURR {val}")
        if (e := self.error) is not None:
            raise RuntimeError(f"Exception setting current {e}")

    @property
    def volt(self):
        """Volt set point"""
        self._write_data(":VOLT?")
        return float(self._read_data())

    @volt.setter
    def volt(self, val: float):
        """Volt set point"""
        self._write_data(f":VOLT {val}")
        if (e := self.error) is not None:
            raise RuntimeError(f"Exception setting volt {e}")

    @property
    def range(self):
        """Range set"""
        rang_res = self._query_data(":VOLT:RANG?").strip()
        if self.curr_range_map is None:
            warnings.warn(
                f"Unknown instrument model, cannot interpret range {rang_res}, returning low"
            )
            return GWPSMPSURange.LOW
        return self.curr_range_map[rang_res]

    @range.setter
    def range(self, val: GWPSMPSURange):
        """Range set"""
        self._write_data(f":VOLT:RANG {val.value}")
        if (e := self.error) is not None:
            raise RuntimeError(f"Exception setting range {e}")

    @property
    def v_meas(self):
        self._write_data(":MEAS?")
        return float(self._read_data())

    @property
    def i_meas(self):
        self._write_data(":MEAS:CURR?")
        return float(self._read_data())

    @property
    def output(self):
        self._write_data(":OUTP:STAT?")
        return self._read_data()

    @output.setter
    def output(self, val):
        if val:
            self._write_data(":OUTP ON")
        else:
            self._write_data(":OUTP OFF")

        if (e := self.error) is not None:
            raise RuntimeError(f"Exception setting output {e}")

    def beep(self):
        """The instrument returns a single beep immediately."""
        self._write_data("SYST:BEEP")
        if (e := self.error) is not None:
            raise RuntimeError(f"Exception setting beep {e}")

    @property
    def beeper(self) -> bool:
        """Switches the front panel control beeper on or off."""
        res = self._query_data("SYST:BEEP:STAT?")
        return self.on_off_inv[res.strip()]

    @beeper.setter
    def beeper(self, val: bool) -> None:
        """Switches the front panel control beeper on or off."""
        self._write_data(f"SYST:BEEP:STAT {self.on_off_lut[val]}")
        if (e := self.error) is not None:
            raise RuntimeError(f"Exception setting beeper {e}")

    def reset(self) -> None:
        self._write_data("*RST")
        self._write_data("*CLS")

    @property
    def error(self) -> Optional[GWPSMPSUError]:
        """Pop the latest error from the error stack; None if there are no errors."""
        res = self._query_data("SYST:ERR?").strip()
        raw_code, val = res.split(",")
        code = int(raw_code.strip())
        val = val.strip('"')
        if code == 0:
            return None
        return GWPSMPSUError(code=code, text=val, raw_str=res)


if __name__ == "__main__":
    import pyvisa

    rm = pyvisa.ResourceManager()
    ins_interface = cast(
        pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::7::INSTR")
    )

    ins = GWPSMPSU(ins_interface)

    ins.output = True
    print(ins.output)

    # ins.output = False
