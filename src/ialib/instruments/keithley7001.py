from typing import Optional
import logging
import socket
import time

from plx_gpib_ethernet import PlxGPIBEthDevice, plx_get_first

logger = logging.getLogger(__name__)


class Keithley7001(PlxGPIBEthDevice):
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

    def open(self, slot: Optional[int] = None, chan: Optional[int] = None) -> None:
        if slot is None and chan is None:
            # Open all
            return self._write_data(":open all")
        if slot is None or chan is None:
            raise ValueError(f"Slot or chan not provided! (Slot: {slot}, Chan: {chan})")
        if slot not in [1, 2]:
            raise ValueError(
                f"Slot invalid must be 1 or 2! (Slot: {slot}, Chan: {chan})"
            )
        self._write_data(f":OPEN (@{slot}!{chan})")
        time.sleep(0.25)
        return None

    def close_sw(self, slot: int, chan: int) -> None:
        if slot not in [1, 2]:
            raise ValueError(
                f"Slot invalid must be 1 or 2! (Slot: {slot}, Chan: {chan})"
            )
        self._write_data(f":CLOS (@{slot}!{chan})")
        time.sleep(0.25)
        return None


if __name__ == "__main__":
    ins = Keithley7001(host=plx_get_first(), address=9)
    ins.open()
    ins.close_sw(slot=1, chan=2)
