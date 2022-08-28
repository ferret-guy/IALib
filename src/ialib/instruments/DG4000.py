from typing import Union, Collection, cast
from dataclasses import dataclass
from enum import Enum
import math

import pyvisa


class RigolDG4000:
    """
    Driver for the Rigol DG4000 series arbitrary waveform generator.

    This driver works for all four models (DG4202, DG4162, DG4102, DG4062).

    VERY loosely from  https://github.com/nanoelectronics-new/qcodes/blob/master/instrument_drivers/rigol/DG4000.py
    """

    def __init__(self, address: str) -> None:
        self.ins_handle = cast(
            pyvisa.resources.MessageBasedResource,
            pyvisa.ResourceManager().open_resource(address),
        )
        self.chan_1 = self.Channel(self, 1)
        self.chan_2 = self.Channel(self, 2)

        self.model = self.get_idn().model

        models = ["DG4202", "DG4162", "DG4102", "DG4062"]

        if self.model in models:
            i = models.index(self.model)

            self.max_sine_freq = [200e6, 160e6, 100e6, 60e6][i]
            self.max_square_freq = [60e6, 50e6, 40e6, 25e6][i]
            self.max_ramp_freq = [5e6, 4e6, 3e6, 1e6][i]
            self.max_pulse_freq = [50e6, 40e6, 25e6, 15e6][i]
            self.max_harmonic_freq = [100e6, 80e6, 50e6, 30e6][i]
            self.max_arb_freq = [50e6, 40e6, 25e6, 15e6][i]
        else:
            raise KeyError(f"Model {self.model} is not recognized")

    on_off_lut = {True: "ON", False: "OFF"}
    on_off_inv = {v: k for k, v in on_off_lut.items()}

    def get_idn(self) -> "RigolDG4000.IDNData":
        """
        Query the ID character string of the instrument.

        :return: IDN string
        """
        res = tuple(i.strip() for i in self.ins_handle.query("*IDN?").split(","))
        if len(res) != 4:
            raise ValueError(
                f"Invalid IDN response, got '{res}', expected '<vendor>,<model>,<serial>,<firmware>'"
            )
        return self.IDNData(*res)

    def shutdown(self) -> None:
        """
        Shut down the instrument.

        :return: None
        """
        self.ins_handle.write("SYST:SHUTDOWN")

    def restart(self) -> None:
        """
        Restart the instrument.

        :return: None
        """
        self.ins_handle.write("SYST:RESTART")

    def align_phase(self) -> None:
        """
        Execute align phase.

        :return: None
        """
        self.ins_handle.write("PHAS:INIT")

    @property
    def scpi_version(self) -> str:
        """
        Query and return the SCPI version information.

        :return: SCPI version information
        """
        return self.ins_handle.query("SYST:VERS?").strip()

    def reset(self) -> None:
        """
        Restore the instrument to its default states.

        :return: None
        """
        self.ins_handle.write("*RST")

    def beep(self) -> None:
        """
        The beeper generates a beep immediately.

        :return: None
        """
        self.ins_handle.write("SYST:BEEP")

    @property
    def beeper_enabled(self) -> bool:
        """
        Query the status of the beeper.

        :return: True if enabled false otherwise
        """
        return self.on_off_inv[self.ins_handle.query("SYST:BEEP:STAT?").strip()]

    @beeper_enabled.setter
    def beeper_enabled(self, val: bool) -> None:
        """
        Enable or disable the beeper.

        :param val: Beeper enable state
        :return: None
        """
        on_off_val = self.on_off_lut[val]
        self.ins_handle.write(f"SYST:BEEP:STAT {on_off_val}")

    def copy_config_to_ch1(self) -> None:
        """
        Copy the configuration state of CH2 to CH1

        :return: None
        """
        self.ins_handle.write("SYST:CSC CH2,CH1")

    def copy_config_to_ch2(self) -> None:
        """
        Copy the configuration state of CH1 to CH2

        :return: None
        """
        self.ins_handle.write("SYST:CSC CH1,CH2")

    def copy_waveform_to_ch1(self) -> None:
        """
        Copy the arbitrary waveform data of CH1 to CH2

        :return: None
        """
        self.ins_handle.write("SYST:CWC CH2,CH1")

    def copy_waveform_to_ch2(self) -> None:
        """
        Copy the arbitrary waveform data of CH1 to CH2

        :return: None
        """
        self.ins_handle.write("SYST:CWC CH1,CH2")

    def get_error(self) -> str:
        return self.ins_handle.query("SYST:ERR?")

    @property
    def keyboard_locked(self) -> bool:
        return self.on_off_inv[self.ins_handle.query("SYST:KLOCK?").strip()]

    @keyboard_locked.setter
    def keyboard_locked(self, val: bool) -> None:
        on_off_val = self.on_off_lut[val]
        self.ins_handle.write(f"SYST:KLOCK {on_off_val}")

    @property
    def reference_clock(self) -> "RigolDG4000.Clk":
        return self.Clk(self.ins_handle.query("SYST:ROSC:SOUR?").strip())

    @reference_clock.setter
    def reference_clock(self, val: "RigolDG4000.Clk") -> None:
        self.ins_handle.write(f"SYST:ROSC:SOUR {val.value}")

    def upload_data(self, data: Collection[float]) -> None:
        """
        Upload data to the AWG memory.

        :arg Collection[float] data: Collection datapoints as floats
        """
        if 1 <= len(data) <= 16384:
            # Convert the input to a comma-separated string
            string = ",".join(format(f, ".9f") for f in data)

            self.ins_handle.write(f"DATA VOLATILE,{string}")
        else:
            raise Exception(
                f"Data length of {len(data)} is not in the range of 1 to 16384"
            )

    def __getitem__(self, item: int) -> "RigolDG4000.Channel":
        """Used to select the channel"""
        if item == 1:
            return self.chan_1
        elif item == 2:
            return self.chan_2
        else:
            raise ValueError(f"Channel {item} is not a valid channel! (1 or 2)")

    class Function(Enum):
        """Waveform Function."""

        # Freq, amp, off, phase
        Cust = "CUST"
        Harm = "HARM"
        Ramp = "RAMP"
        Sine = "SIN"
        Square = "SQU"
        User = "USER"
        # Freq, amp, off, delay
        Pulse = "PULS"
        # amp, offset
        Noise = "NOIS"

    class Pol(Enum):
        """Channel output polarity."""

        Norm = "NORMAL"
        Inv = "INVERTED"

    class Clk(Enum):
        """Input Clk selection."""

        Int = "INT"
        Ext = "EXT"

    @dataclass(frozen=True)
    class IDNData:
        vendor: str
        model: str
        serial: str
        firmware: str

    class Channel:
        """Single channel of waveform gen."""

        def __init__(self, parent: "RigolDG4000", chan_num: int):
            self.parent = parent
            # Copy parent consts
            self.on_off_lut = parent.on_off_lut
            self.on_off_inv = parent.on_off_inv
            self.ins_handle = parent.ins_handle
            self.Function = parent.Function
            self.Pol = parent.Pol

            self.chan_num = chan_num

        @property
        def enabled(self) -> bool:
            """
            Get enable or disable the output of channel at the front panel

            :return: If the channel is enabled
            """
            return self.on_off_inv[
                self.ins_handle.query(f"OUTP{self.chan_num}:STAT?").strip()
            ]

        @enabled.setter
        def enabled(self, val: bool) -> None:
            """
            Enable or disable the output of channel at the front panel

            :param val: True to enable false to disable
            :return: None
            """
            on_off_val = self.on_off_lut[val]
            self.ins_handle.write(f"OUTP{self.chan_num}:STAT {on_off_val}")

        @property
        def sync_enabled(self) -> bool:
            """
            Get enable or disable status of the sync signal.

            :return: True if enabled false otherwise
            """
            return self.on_off_inv[
                self.ins_handle.query(f"OUTP{self.chan_num}:SYNC?").strip()
            ]

        @sync_enabled.setter
        def sync_enabled(self, val: bool) -> None:
            """
            Enable or disable the sync signal

            :param val: True o enable false to disable
            :return: None
            """
            on_off_val = self.on_off_lut[val]
            self.ins_handle.write(f"OUTP{self.chan_num}:SYNC {on_off_val}")

        @property
        def polarity(self) -> "RigolDG4000.Pol":
            """
            Get the polarity of the output signal.

            :return: RigolDG4000.Pol object
            """
            return self.Pol(self.ins_handle.query(f"OUTP{self.chan_num}:POL?").strip())

        @polarity.setter
        def polarity(self, val: "RigolDG4000.Pol") -> None:
            """
            Set the polarity of the output signal.

            :param val: RigolDG4000.Pol
            :return: None
            """
            self.ins_handle.write(f"OUTP{self.chan_num}:POL {val.value}")

        @property
        def phase(self) -> float:
            return float(self.ins_handle.query(f"SOUR{self.chan_num}:PHAS?").strip())

        @phase.setter
        def phase(self, val: float) -> None:
            if not 0 <= val <= 360:
                raise ValueError(f"phase of {val} is outside (0-360)")
            self.ins_handle.write(f"SOUR{self.chan_num}:PHAS {val}")

        @property
        def sync_polarity(self) -> "RigolDG4000.Pol":
            return self.Pol(
                self.ins_handle.query(f"OUTP{self.chan_num}:SYNC:POL?").strip()
            )

        @sync_polarity.setter
        def sync_polarity(self, val: "RigolDG4000.Pol") -> None:
            self.ins_handle.write(f"OUTP{self.chan_num}:SYNC:POL {val.value}")

        @property
        def function(self) -> "RigolDG4000.Function":
            get_str = (
                self.ins_handle.query(f"SOUR{self.chan_num}:APPL?")
                .strip()
                .strip('"')
                .split(",")
            )
            return self.Function(get_str[0])

        @function.setter
        def function(self, val: "RigolDG4000.Function") -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:APPL:{val.value}")

        @property
        def configuration(self) -> dict:
            get_str = (
                self.ins_handle.query(f"SOUR{self.chan_num}:APPL?")
                .strip()
                .strip('"')
                .split(",")
            )
            func = self.Function(get_str[0])
            if func in [
                self.Function.Cust,
                self.Function.Harm,
                self.Function.Ramp,
                self.Function.Sine,
                self.Function.Square,
                self.Function.User,
            ]:
                return {
                    "Function": func,
                    "Freq": float(get_str[1]),
                    "Amp": float(get_str[2]),
                    "Off": float(get_str[3]),
                    "Phase": float(get_str[4]),
                }
            elif func == self.Function.Pulse:
                return {
                    "Function": func,
                    "Freq": float(get_str[1]),
                    "Amp": float(get_str[2]),
                    "Off": float(get_str[3]),
                    "Delay": float(get_str[4]),
                }
            elif func == self.Function.Noise:
                return {
                    "Function": func,
                    "Amp": float(get_str[1]),
                    "Off": float(get_str[2]),
                }
            else:
                raise ValueError(f"Function {func} is not supported!")

        @configuration.setter
        def configuration(self, val: Union[dict, "RigolDG4000.Function"]) -> None:
            """
            Requires all the keys for the specified function, or no keys:
            - Function, Freq, Amp, Off, Phase for Cust, Harm, Ramp, Sine, Square, and User
            - Function, Freq, Amp, Off, Delay for Pulse
            - Function, Amp, Off for Noise

            TODO: Make object
            """
            if isinstance(val, self.Function):
                self.ins_handle.write(f"SOUR{self.chan_num}:APPL:{val.value}")
            elif val["Function"] in [
                self.Function.Cust,
                self.Function.Harm,
                self.Function.Ramp,
                self.Function.Sine,
                self.Function.Square,
                self.Function.User,
            ]:
                self.ins_handle.write(
                    f"SOUR{self.chan_num}:APPL:{val['Function'].value}"
                    f" {val['Freq']:.6e},{val['Amp']:.6e},{val['Off']:.6e},{val['Phase']:.6e}"
                )
            elif val["Function"] == self.Function.Pulse:
                self.ins_handle.write(
                    f"SOUR{self.chan_num}:APPL:{val['Function'].value}"
                    f" {val['Freq']:.6e},{val['Amp']:.6e},{val['Off']:.6e},{val['Delay']:.6e}"
                )
            elif val["Function"] == self.Function.Noise:
                self.ins_handle.write(
                    f"SOUR{self.chan_num}:APPL:{val['Function'].value}"
                    f" {val['Amp']:.6e},{val['Off']:.6e}"
                )

        @property
        def frequency_center(self) -> float:
            return float(
                self.ins_handle.query(f"SOUR{self.chan_num}:FREQ:CENT?").strip()
            )

        @frequency_center.setter
        def frequency_center(self, val: float) -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:FREQ:CENT {val}")

        @property
        def frequency(self) -> float:
            return float(self.ins_handle.query(f"SOUR{self.chan_num}:FREQ?").strip())

        @frequency.setter
        def frequency(self, val: float) -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:FREQ {val}")

        @property
        def amplitude(self) -> float:
            return float(self.ins_handle.query(f"SOUR{self.chan_num}:VOLT?").strip())

        @amplitude.setter
        def amplitude(self, val: float) -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:VOLT {val}")

        @property
        def offset(self) -> float:
            return float(
                self.ins_handle.query(f"SOUR{self.chan_num}:VOLT:OFFS?").strip()
            )

        @offset.setter
        def offset(self, val: float) -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:VOLT:OFFS {val}")

        @property
        def sweep_start(self) -> float:
            return float(
                self.ins_handle.query(f"SOUR{self.chan_num}:FREQ:STAR?").strip()
            )

        @sweep_start.setter
        def sweep_start(self, val: float) -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:FREQ:STAR {val}")

        @property
        def sweep_stop(self) -> float:
            return float(
                self.ins_handle.query(f"SOUR{self.chan_num}:FREQ:STOP?").strip()
            )

        @sweep_stop.setter
        def sweep_stop(self, val: float) -> None:
            self.ins_handle.write(f"SOUR{self.chan_num}:FREQ:STOP {val}")

        @property
        def ramp_symmetry(self) -> float:
            return float(
                self.ins_handle.query(f"SOUR{self.chan_num}:FUNC:RAMP:SYMM?").strip()
            )

        @ramp_symmetry.setter
        def ramp_symmetry(self, val: float) -> None:
            if not 0 <= val <= 100:
                raise ValueError(f"ramp_symmetry must be from 0-100%! not {val}")
            self.ins_handle.write(f"SOUR{self.chan_num}:FUNC:RAMP:SYMM {val}")

        @property
        def square_duty_cycle(self) -> float:
            return float(
                self.ins_handle.query(f"SOUR{self.chan_num}:FUNC:SQU:DCYC?").strip()
            )

        @square_duty_cycle.setter
        def square_duty_cycle(self, val: float) -> None:
            if not 20 <= val <= 80:
                raise ValueError(f"square_duty_cycle must be from 20-80%! not {val}")
            self.ins_handle.write(f"SOUR{self.chan_num}:FUNC:SQU:DCYC {val}")

        @property
        def output_impedance(self) -> float:
            res = self.ins_handle.query(f"OUTP{self.chan_num}:IMP?").strip()
            try:
                return float(res)
            except ValueError:
                if "MIN" in res:
                    return 0
                if "MAX" in res:
                    return 10001
                if "INF" in res:
                    return math.inf
                return float(res)

        @output_impedance.setter
        def output_impedance(self, val: float) -> None:
            if val < 1:
                set_val = "MIN"
            elif math.isinf(val):
                set_val = "INF"
            elif val > 10000:
                set_val = "MAX"
            else:
                set_val = str(val)
            self.ins_handle.write(f"OUTP{self.chan_num}:IMP {set_val}")


if __name__ == "__main__":
    ins = RigolDG4000("TCPIP0::192.168.5.239::INSTR")

    # ins.upload_data([0, 0])

    for i in [1, 2]:
        ins[i].function = ins.Function.Ramp
        ins[i].frequency = 158e3
        ins[i].output_impedance = math.inf
        ins[i].amplitude = 15.7
        ins[i].ramp_symmetry = 10

    ins[1].enabled = True
    ins[2].enabled = True

    ins.align_phase()

    print(f"{ins.model=}")
    print(f"{ins[1].frequency=}")
    print(ins.get_error())
