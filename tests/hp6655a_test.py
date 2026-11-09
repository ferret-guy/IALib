import unittest
from unittest.mock import Mock, call

from ialib.instruments.hp6655a import HP6655A


class HP6655ATest(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()
        self.interface.query.return_value = '0,"No error"\n'
        self.supply = HP6655A(self.interface)

    def test_no_io_on_construction(self):
        self.assertEqual(self.interface.mock_calls, [])

    def test_set_iv(self):
        self.supply.set_iv(12, 0.5)
        self.assertEqual(self.interface.write.call_args_list,
                         [call("CURR 0.5"), call("VOLT 12")])
        self.assertEqual(self.interface.query.call_args_list,
                         [call("SYST:ERR?"), call("SYST:ERR?")])

    def test_invalid_values_do_not_write(self):
        for attr, limit in [("volt", 122.85), ("curr", 4.095), ("ovp", 132)]:
            for value in [-1, limit + 1, float("nan"), float("inf")]:
                with self.subTest(attr=attr, value=value):
                    with self.assertRaises(ValueError):
                        setattr(self.supply, attr, value)
        for v, i in [(12, 5), (123, 1)]:
            with self.assertRaises(ValueError):
                self.supply.set_iv(v, i)
        self.interface.write.assert_not_called()

    def test_programmable_limits(self):
        for attr, value in [("volt", 122.85), ("curr", 4.095), ("ovp", 132)]:
            setattr(self.supply, attr, 0)
            setattr(self.supply, attr, value)
        self.assertEqual(self.interface.write.call_count, 6)

    def test_numeric_queries(self):
        for attr, command in [("volt", "VOLT?"), ("curr", "CURR?"),
                              ("v_meas", "MEAS:VOLT?"),
                              ("i_meas", "MEAS:CURR?"), ("ovp", "VOLT:PROT?")]:
            self.interface.query.return_value = "+1.250E+00\n"
            self.assertEqual(getattr(self.supply, attr), 1.25)
            self.interface.query.assert_called_with(command)

    def test_boolean_controls(self):
        for attr, command in [("output", "OUTP"), ("ocp", "CURR:PROT:STAT")]:
            for enabled in [False, True]:
                self.interface.query.return_value = '0,"No error"'
                setattr(self.supply, attr, enabled)
                self.interface.write.assert_called_with(
                    f"{command} {'ON' if enabled else 'OFF'}")
                self.interface.query.return_value = f"{int(enabled)}\n"
                self.assertIs(getattr(self.supply, attr), enabled)
                self.interface.query.assert_called_with(f"{command}?")

    def test_errors(self):
        self.interface.query.return_value = '-222,"Data out of range, check value"\n'
        error = self.supply.error
        self.assertEqual(error.code, -222)
        self.assertEqual(error.text, "Data out of range, check value")
        with self.assertRaisesRegex(RuntimeError, "-222"):
            self.supply.volt = 12

    def test_disable_error_check(self):
        HP6655A(self.interface, error_check=False).output = False
        self.interface.query.assert_not_called()

    def test_reset_and_protection(self):
        self.supply.reset()
        self.assertEqual(self.interface.write.call_args_list,
                         [call("*RST"), call("*CLS")])
        self.assertIsNone(self.supply.error)
        self.supply.clear_protection()
        self.interface.write.assert_called_with("OUTP:PROT:CLE")


if __name__ == "__main__":
    unittest.main()
