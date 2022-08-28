import socket
import logging

from plx_gpib_ethernet import PlxGPIBEthDevice, plx_get_first

logger = logging.getLogger(__name__)


class GWPSMPSU(PlxGPIBEthDevice):
    def __init__(self, host: str, address: int = 11):
        super().__init__(host=host, address=address)

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

    @property
    def volt(self):
        """Volt set point"""
        self._write_data(":VOLT?")
        return float(self._read_data())

    @volt.setter
    def volt(self, val: float):
        """Volt set point"""
        self._write_data(f":VOLT {val}")

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


if __name__ == "__main__":
    import numpy as np

    ins = GWPSMPSU(host=plx_get_first(), address=7)

    ins.output = True
    print(ins.output)

    # ins.output = False
