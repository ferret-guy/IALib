"""HP 6655A driver using the SCPI language (not Compatibility mode)."""

import math
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

    # Maximum programmable values, rather than nominal output ratings.
    MAX_VOLTAGE = 122.85
    MAX_CURRENT = 4.095
    MAX_OVP = 132.0

    def __init__(self, ins: InstrumentInterface, error_check: bool = True):
        self.ins = ins
        self.error_check = error_check

    @staticmethod
    def _validate(val: float, maximum: float) -> None:
        if not math.isfinite(val) or not 0 <= val <= maximum:
            raise ValueError(f"Value must be finite and between 0 and {maximum}")

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
        self._validate(val, self.MAX_VOLTAGE)
        self._write_data(f"VOLT {val}")

    @property
    def curr(self) -> float:
        """Current limit in amperes."""
        return float(self._query_data("CURR?"))

    @curr.setter
    def curr(self, val: float) -> None:
        self._validate(val, self.MAX_CURRENT)
        self._write_data(f"CURR {val}")

    def set_iv(self, v: float, i: float) -> None:
        """Set current limit, then voltage; does not enable the output.

        Both values are validated before writing. Updates are not atomic.
        """
        self._validate(v, self.MAX_VOLTAGE)
        self._validate(i, self.MAX_CURRENT)
        self.curr = i
        self.volt = v

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
        self._validate(val, self.MAX_OVP)
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
        # Clear old errors before checking the reset command.
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


class HP6655ACompatibility(HP6655A):
    """Legacy HP Compatibility mode, without changing saved language/settings.

    Supports set points, measured values, output writes, OVP, and errors.
    Output-state queries, OCP, reset, and protection clearing are unsupported.
    Legacy replies include a mnemonic prefix and may be preceded by blank lines.
    """

    _queries = {
        "VOLT?": "VSET?", "CURR?": "ISET?",
        "MEAS:VOLT?": "VOUT?", "MEAS:CURR?": "IOUT?",
        "VOLT:PROT?": "OVP?", "SYST:ERR?": "ERR?",
    }
    _writes = {"VOLT": "VSET", "CURR": "ISET",
               "OUTP": "OUT", "VOLT:PROT": "OVP"}

    def _query_data(self, dat: str) -> str:
        if dat not in self._queries:
            raise NotImplementedError(f"Compatibility mode does not support {dat}")
        command = self._queries[dat]
        response = self.ins.query(command).strip()
        for _ in range(10):
            if response:
                break
            response = self.ins.read().strip()
        prefix, separator, value = response.partition(" ")
        if prefix != command.rstrip("?") or not separator or not value.strip():
            raise ValueError(f"Unexpected reply to {command}: {response!r}")
        return value.strip()

    def _write_data(self, dat: str) -> None:
        command, separator, value = dat.partition(" ")
        if command not in self._writes or not separator:
            raise NotImplementedError(f"Compatibility mode does not support {dat}")
        self.ins.write(f"{self._writes[command]} {value}")
        if self.error_check:
            error = self.error
            if error is not None:
                raise RuntimeError(f"Error executing {dat!r}: {error.raw_str}")

    @property
    def error(self) -> Optional[HP6655AError]:
        """Read the legacy error code; no text is returned by the instrument."""
        code = int(self._query_data("SYST:ERR?"))
        if code == 0:
            return None
        return HP6655AError(code, "HP Compatibility error", f"ERR {code}")

    def reset(self) -> None:
        raise NotImplementedError("Legacy CLR recalls power-on settings; reset is unsupported")
