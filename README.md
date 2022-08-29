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
- Keithley (now Tektronix) 7001 (Just opening and closing switches)
- Advantest R6581T


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
