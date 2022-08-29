import unittest
from typing import cast

import pyvisa

import ialib.instruments.hp34401a as dimm


class HP34401ATest(unittest.TestCase):
    ins: dimm.HP34401A

    @classmethod
    def setUpClass(cls) -> None:
        rm = pyvisa.ResourceManager()
        ins_interface = cast(
            pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::25::INSTR")
        )
        cls.ins = dimm.HP34401A(ins_interface)
        cls.ins.reset()
        cls.ins.beeper = False

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self) -> None:
        self.reset_errors()

    @unittest.expectedFailure
    def test_fail(self):
        self.ins._write_data("test_fake_val")
        self.tearDown()

    def tearDown(self) -> None:
        self.assertIsNone(self.ins.error)

    def test_beep(self):
        for b in [True, False]:
            with self.subTest(beeper=b):
                self.ins.beeper = b
                self.ins.beep()

    def test_func(self):
        for f in dimm.HP34401AFunction:
            with self.subTest(function=f.name):
                self.ins.mode = f
                self.assertEqual(self.ins.mode, f)

    def test_read(self):
        # todo
        pass

    def test_null(self):
        self.ins.mode = dimm.HP34401AFunction.VDC
        # Assume ~20VDC is fed in

        # Measure voltage
        ofst = self.ins.data

        # Turn on null
        self.ins.null = True

        # Assert that the measured offset is almost the null reg value
        self.assertAlmostEqual(self.ins.null_ofst, ofst, 3)
        # Assert that the instrument measures near zero
        self.assertAlmostEqual(self.ins.data, 0, 3)

        # Assert that the offset reg can actually be changed
        self.ins.null_ofst -= 10
        self.assertAlmostEqual(self.ins.data, 10, 3)

    def test_disp(self):
        for b in [False, True]:
            self.ins.display = b
            self.assertEqual(self.ins.display, b)

        test_msg = "TEST"
        self.ins.display_text = "TEST"
        self.assertEqual(self.ins.display_text, "TEST")

    def reset_errors(self):
        """Flush all errors in the DMM"""
        while True:
            if self.ins.error is None:
                return

    def test_term(self):
        self.reset_errors()
        # Check if this throws an error
        # TODO: Manual switch op
        self.ins.input
        self.assertIsNone(self.ins.error)

    def test_range(self):
        self.reset_errors()
        self.ins.mode = dimm.HP34401AFunction.VDC
        self.ins.range = 184
        self.assertEqual(self.ins.range, 1000.0)
        self.assertIsNone(self.ins.error)

        self.ins.range = float("inf")
        self.assertEqual(self.ins.range, 1000.0)
        self.assertIsNone(self.ins.error)

        for f in dimm.HP34401AFunction:
            with self.subTest(function=f.name):
                # Just test for errors
                # TODO: Check results for every function
                self.ins.mode = f
                self.ins.range = 1.8
                self.assertIsNone(self.ins.error)

                self.ins.range = float("inf")
                self.assertIsNone(self.ins.error)

    def test_auto_range(self):
        for f in [
            # Not every function has auto range
            dimm.HP34401AFunction.VDC,
            dimm.HP34401AFunction.VAC,
            dimm.HP34401AFunction.IDC,
            dimm.HP34401AFunction.IAC,
            dimm.HP34401AFunction.OHM2W,
            dimm.HP34401AFunction.OHM4W,
            # Times out unless a signal is actually present
            # dimm.HP34401AFunction.PERIOD,
            # dimm.HP34401AFunction.FREQ,
        ]:
            with self.subTest(function=f.name):
                # Just test for errors
                # TODO: Check results for every function
                self.ins.mode = f
                for b in [True, False]:
                    with self.subTest(auto_range=b):
                        self.ins.auto_range = b
                        self.assertEqual(self.ins.auto_range, b)

    def test_nplc(self):
        self.ins.mode = dimm.HP34401AFunction.VDC
        for d in [0.02, 0.2, 1, 10, 100]:
            with self.subTest(digits=d):
                self.ins.nplc = d
                self.assertEqual(self.ins.nplc, d)

        # Test correct insturment rounding
        for d in [10.1, 12, 14, 18.4, 22, 50, 66, 99]:
            with self.subTest(digits=d):
                self.ins.nplc = d
                self.assertEqual(self.ins.nplc, 100)

    def test_azero(self):
        for b in [True, False]:
            with self.subTest(azero=b):
                self.ins.azero = b


if __name__ == "__main__":
    unittest.main()
