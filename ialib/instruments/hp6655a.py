"""HP 6655A SCPI driver."""

from dataclasses import dataclass
from typing import Optional

from ialib.instruments.types import InstrumentInterface


@dataclass(frozen=True)
class HP6655AError:
    code: int
    text: str
    raw_str: str


class HP6655A:
    """Single-output HP 6655A supply, nominally 120 V / 4 A.

    Construction performs no I/O. Setters check the instrument error queue
    unless error_check=False. The caller owns the interface and its timeouts.
    """

    def __init__(self, ins: InstrumentInterface, error_check: bool = True):
        self.ins = ins
        self.error_check = error_check

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)
        if self.error_check:
            err = self.error
            if err is not None:
                raise RuntimeError(f"Error executing {dat!r}: {err.raw_str}")

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

    @property
    def volt(self) -> float:
        """Voltage set point in volts."""
        return float(self._query_data("VOLT?"))

    @volt.setter
    def volt(self, val: float) -> None:
        self._write_data(f"VOLT {val}")

    @property
    def curr(self) -> float:
        """Current limit in amperes."""
        return float(self._query_data("CURR?"))

    @curr.setter
    def curr(self, val: float) -> None:
        self._write_data(f"CURR {val}")

    @property
    def v_meas(self) -> float:
        """Measured voltage at the sense terminals in volts."""
        return float(self._query_data("MEAS:VOLT?"))

    @property
    def i_meas(self) -> float:
        """Measured output current in amperes."""
        return float(self._query_data("MEAS:CURR?"))

    @property
    def output(self) -> bool:
        """Whether the output is enabled."""
        return bool(int(self._query_data("OUTP?").strip()))

    @output.setter
    def output(self, val: bool) -> None:
        self._write_data(f"OUTP {'ON' if val else 'OFF'}")

    @property
    def ovp(self) -> float:
        """Overvoltage protection threshold in volts."""
        return float(self._query_data("VOLT:PROT?"))

    @ovp.setter
    def ovp(self, val: float) -> None:
        self._write_data(f"VOLT:PROT {val}")

    @property
    def ocp(self) -> bool:
        """Whether overcurrent protection is enabled."""
        return bool(int(self._query_data("CURR:PROT:STAT?").strip()))

    @ocp.setter
    def ocp(self, val: bool) -> None:
        self._write_data(f"CURR:PROT:STAT {'ON' if val else 'OFF'}")

    def clear_protection(self) -> None:
        """Clear protection trips; may restore the previously enabled output."""
        self._write_data("OUTP:PROT:CLE")

    def reset(self) -> None:
        """Reset the supply (disabling output), then clear status and errors."""
        self.ins.write("*RST")
        self._write_data("*CLS")

    @property
    def error(self) -> Optional[HP6655AError]:
        """Pop one error from the queue, or return None for no error."""
        res = self._query_data("SYST:ERR?").strip()
        raw_code, text = res.split(",", 1)
        code = int(raw_code.strip())
        if code == 0:
            return None
        return HP6655AError(code, text.strip().strip('"'), res)
