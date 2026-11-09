import unittest
from unittest.mock import Mock, patch

from examples.hp6655a_ni import exercise


class NIExerciseTest(unittest.TestCase):
    def test_unidentified_device_never_receives_power_commands(self):
        for identity in ["\n", "HP,34401A,0,1", "UNKNOWN,6655A,0,1"]:
            interface = Mock()
            interface.query.return_value = identity
            with self.assertRaises(RuntimeError):
                exercise(interface)
            interface.write.assert_not_called()

    @patch("examples.hp6655a_ni.time.sleep")
    def test_bounded_test_and_output_off_on_failure(self, sleep):
        interface = Mock()
        responses = {"*IDN?": "HEWLETT-PACKARD,6655A,0,1",
                     "SYST:ERR?": '0,"No error"',
                     "VOLT?": "12", "CURR?": "0.5"}
        interface.query.side_effect = lambda command: responses[command]
        # Measurement fails; output must still be turned off.
        with self.assertRaises(KeyError):
            exercise(interface)
        writes = [item.args[0] for item in interface.write.call_args_list]
        self.assertEqual(writes, ["OUTP OFF", "CURR 0.5", "VOLT 12.0",
                                  "OUTP ON", "OUTP OFF"])

    def test_excessive_readback_prevents_enable(self):
        interface = Mock()
        responses = {"*IDN?": "HEWLETT-PACKARD,6655A,0,1",
                     "SYST:ERR?": '0,"No error"',
                     "VOLT?": "12.1", "CURR?": "0.5"}
        interface.query.side_effect = lambda command: responses[command]
        with self.assertRaises(RuntimeError):
            exercise(interface)
        self.assertNotIn("OUTP ON", [item.args[0] for item in interface.write.call_args_list])
        interface.write.assert_called_with("OUTP OFF")
