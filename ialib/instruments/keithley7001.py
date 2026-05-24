import time
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Union, cast

from ialib.instruments.types import InstrumentInterface

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Channel:
    card: int
    switch: int

    @classmethod
    def from_dict(cls, mapping: Dict[int, Union[int, List[int]]]) -> List['Channel']:
        """
        Helper to quickly create a list of Channels from a dictionary.
        
        Because Python dict keys must be unique, defining multiple switches on the 
        same card should use a list.
        
        Example: 
            Channel.from_dict({1: [1, 2, 4]}) -> [Channel(1,1), Channel(1,2), Channel(1,4)]
            Channel.from_dict({1: 1, 2: 4})   -> [Channel(1,1), Channel(2,4)]
        """
        channels = []
        for card_idx, switches in mapping.items():
            # If the user passed a single int instead of a list
            if isinstance(switches, int):
                channels.append(cls(card=card_idx, switch=switches))
            # If the user passed a list of ints
            else:
                for sw in switches:
                    channels.append(cls(card=card_idx, switch=sw))
        return channels


class Keithley7001:
    def __init__(self, ins: InstrumentInterface, *, settle_sec: float = 0.25):
        self.ins = ins
        if settle_sec < 0:
            raise ValueError(f"settle_sec must be >= 0, got {settle_sec}")
        self.settle_sec = settle_sec

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)

    def _read_data(self) -> str:
        return self.ins.read()

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

    def open(self, slot: Optional[int] = None, chan: Optional[int] = None) -> None:
        """Opens specified channel or all channels if none specified."""
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
        if self.settle_sec > 0:
            time.sleep(self.settle_sec)
        return None

    def close_sw(self, channel: Channel) -> None:
        """Closes a specific channel."""
        if channel.card not in [1, 2]:
            raise ValueError(
                f"Slot invalid must be 1 or 2! (Slot: {channel.card}, Chan: {channel.switch})"
            )
        self._write_data(f":CLOS (@{channel.card}!{channel.switch})")
        if self.settle_sec > 0:
            time.sleep(self.settle_sec)
        return None

    def setup_sweep(self, channels: List[Channel], continuous: bool = True) -> None:
        """
        Configures the instrument for a stepped sweep (scan) across a defined list of channels.
        
        Args:
            channels: A list of Channel dataclass objects to scan through.
            continuous: If True, the scan will loop back to the beginning indefinitely. 
                        Defaults to True.
        """
        if not channels:
            raise ValueError("Channel list cannot be empty!")

        # Convert the list of Channel objects to the SCPI string format (e.g. "1!1, 1!2, 1!4")
        scan_items = [f"{ch.card}!{ch.switch}" for ch in channels]
        scan_list_str = ", ".join(scan_items)

        # Returns the 7001 to a default configuration ideal for scanning 
        self._write_data(":SYSTem:PRESet")
        
        # Define the scan list using the formatted string
        self._write_data(f":SCAN (@{scan_list_str})")
        
        # Set the channel trigger source to BUS so it waits for software triggers (*TRG)
        self._write_data(":TRIGger:SOURce BUS")
        
        if continuous:
            # Tell the trigger layer to loop infinitely over the scan list
            self._write_data(":TRIGger:COUNt INFinite")
        else:
            # Automatically set the channel count to match the length of the scan list
            self._write_data(":TRIGger:COUNt:AUTO ON")

    def start_sweep(self) -> None:
        """
        Takes the instrument out of the idle state and arms the sweep.
        Must be called before the first `step_sweep()`.
        """
        self._write_data(":INITiate")

    def step_sweep(self, readback: bool = False) -> Optional[List[Channel]]:
        """
        Advances the sweep to the next channel in the scan list.
        
        Args:
            readback: If True, queries the instrument for the currently closed 
                      channels and returns a list of Channel dataclass objects.
                      
        Returns:
            A list of `Channel` instances if readback is True, otherwise None.
        """
        self._write_data("*TRG")
        
        # Wait for the relays to actuate and settle
        if self.settle_sec > 0:
            time.sleep(self.settle_sec)
            
        if readback:
            # Query the closed state. The unit returns a string like "(@1!2)" or "(@)"
            raw_response = self._query_data(":CLOS:STAT?").strip()
            
            # Clean off the parentheses and @ symbol
            cleaned = raw_response.strip("()@ \r\n")
            
            closed_channels = []
            if cleaned:
                # The response can be comma separated if multiple relays are closed e.g. "1!2, 1!3"
                for item in cleaned.split(","):
                    parts = item.strip().split("!")
                    if len(parts) >= 2:
                        card_idx = int(parts[0])
                        switch_idx = int(parts[1])
                        closed_channels.append(Channel(card=card_idx, switch=switch_idx))
                        
            return closed_channels
            
        return None


if __name__ == "__main__":
    import pyvisa

    rm = pyvisa.ResourceManager()
    ins_interface = cast(
        pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::26::INSTR")
    )

    ins = Keithley7001(ins_interface, settle_sec=0.1)
    
    # 1. Quickly build the list of channels using the dict helper.
    # We want card 1, channels 1 through 18.
    channel_mapping = {1: list(range(1, 19))}
    
    # Example of non-sequential channels:
    # channel_mapping = {1: [1, 2, 4, 7, 12]} 
    
    my_channels = Channel.from_dict(channel_mapping)
    
    # 2. Configure a continuous sweep using the Channel list
    ins.setup_sweep(my_channels)
    
    # 3. Arm the sweep
    ins.start_sweep()
    
    # 4. Step through 500 times.
    for i in range(500):
        # Step and read back the active channel
        active_chans = ins.step_sweep(readback=True)
        
        if active_chans:
            active_chan = active_chans[0]
            print(f"Step {i+1}/500: Closed Card={active_chan.card}, Switch={active_chan.switch}")
        else:
            print(f"Step {i+1}/500: No channels are currently closed.")
        
        # [Insert your measurement logic here]
        
    # Open all when finished
    ins.open()