IALib
=====


Instrument Automation Library; A library of (mostly) standalone instrument drivers


A library of (mostly) standalone instrument drivers, mostly over GPIB, along with GPIB drivers for some GPIB interfaces.

Interfaces:

- UG01 USB to GPIB Controller by LQ Electronics Corp
- GPIB-ETHERNET (GPIB-LAN) Controller by Prologix LLC

Instruments:

- Rigol DG4000 series arbitrary waveform generators (DG4202, DG4162, DG4102, DG4062)
- Fluke 8840A multimeter
- GW Instek PSM-Series DC Supply (PSM-2010, PSM-3004, PSM-6003)
- HP (~~now Agilent~~ now Keysight) 34401A
- HP (~~now Agilent~~ now Keysight) 53131A (limited support)
- HP (now Keysight) 6655A DC power supply
- Keithley (now Tektronix) 7001 (Just opening and closing switches)
- Advantest R6581T


HP 6655A example (configure the supply for SCPI, not Compatibility language):

NI GPIB-USB-HS adapters work through the existing PyVISA interface; install
NI-VISA and NI-488.2. If the adapter is not controller-in-charge, open
`GPIB0::INTFC` and call `send_ifc()` before opening instruments. This assumes
the NI adapter is the system controller and no other application is using the
bus. See `examples/hp6655a_ni.py` for discovery and an optional identity-checked
12 V / 0.5 A test that turns output off afterward. Discovery sends no power
settings. Run it with `python -m examples.hp6655a_ni` from the repository root;
add `--exercise GPIB0::5::INSTR` only for the supply's actual address.

For supplies already in HP Compatibility mode, import
`HP6655ACompatibility` from the same driver module instead of `HP6655A`.
It supports `volt`, `curr`, `set_iv`, `v_meas`, `i_meas`, output writes, `ovp`,
and `error`. Output-state reads, OCP, reset, and protection clearing raise
`NotImplementedError`. It accepts legacy mnemonic-prefixed responses and skips
up to ten leading blank reads. Configure a finite interface timeout.
Use `--compatibility` with the NI example for discovery and testing:

```text
python -m examples.hp6655a_ni --compatibility
python -m examples.hp6655a_ni --compatibility --exercise GPIB0::5::INSTR
```

The example does not switch the instrument language. `SYST:LANG TMSL` selects
SCPI, but also recalls saved state 0, so do not use it just to probe a live load.
Compatibility mode was tested on two real HP 6655A supplies using NI GPIB-USB-HS
at addresses 5 and 6 with 12 V / 0.5 A set points. Final readings were
12.01 V / 0.0040 A and 12.02 V / 0.0034 A, with no reported errors and
output-off commands sent afterward. SCPI mode has hardware-free tests only.

```python
import pyvisa
from ialib.instruments.hp6655a import HP6655A

rm = pyvisa.ResourceManager()
with rm.open_resource("GPIB0::5::INSTR") as interface:  # Use your GPIB address
    supply = HP6655A(interface)
    supply.output = False
    supply.ovp = 15
    supply.ocp = True
    supply.set_iv(12, 0.5)  # Volts, amperes; current limit is written first
    supply.output = True
    try:
        print(supply.v_meas, supply.i_meas)
    finally:
        supply.output = False
rm.close()
```

The driver also works with any `InstrumentInterface`, including the Prologix
adapter. Construction sends no commands. `volt` and `curr` read the programmed
set points; `v_meas` and `i_meas` read measured values. `output` and `ocp` return
booleans. Setters check `SYST:ERR?` by default; pass `error_check=False` to disable
automatic checks and read `error` explicitly. Existing queued errors can also
cause a setter to raise. `set_iv` validates both values before writing, but its
two writes are not atomic. `reset()` disables output and clears status/errors.
`clear_protection()` clears protection trips and may restore an enabled output.

Commands and programmable limits follow the manufacturer’s
[664xA/665xA programming guide](https://www.keysight.com/us/en/assets/7018-09132/technical-overviews/5964-8269.pdf).
The nominal rating is 120 V / 4 A; maximum programmable values are 122.85 V,
4.095 A, and 132 V for OVP. Hardware-free driver tests:
`python -m unittest discover -s tests -p hp6655a_test.py`.

Example pyvisa:

```python
import pyvisa

import ialib.instruments.hp34401a as hp34401a

rm = pyvisa.ResourceManager()
ins_interface = rm.open_resource("GPIB0::26::INSTR")

ins = hp34401a.HP34401A(ins_interface)
ins.reset()
ins.mode = hp34401a.HP34401AFunction.VDC
print(f"{ins.data=}")
```

Example Prologix GPIB-ETHERNET:

```python
from ialib.interfaces.plx_gpib_ethernet import PlxGPIBEthDevice, plx_get_first
import ialib.instruments.hp34401a as hp34401a

ins = hp34401a.HP34401A(
    PlxGPIBEthDevice(
        host=plx_get_first(), address=11  # Find the first Prologix adaptor
    )
)
ins.reset()
ins.mode = hp34401a.HP34401AFunction.VDC
print(f"{ins.data=}")
```
