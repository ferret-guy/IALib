import unittest
from unittest.mock import Mock, call

from ialib.instruments.hp6655a import HP6655ACompatibility


class CompatibilityTest(unittest.TestCase):
    def test_writes_and_readbacks(self):
        interface = Mock()
        replies = {"ERR?": "ERR 0", "VSET?": "VSET 12.00",
                   "ISET?": "ISET 0.5000", "VOUT?": "VOUT 12.02",
                   "IOUT?": "IOUT 0.0034", "OVP?": "OVP 15"}
        interface.query.side_effect = lambda command: replies[command]
        supply = HP6655ACompatibility(interface)
        supply.set_iv(12, .5)
        supply.output = True
        supply.output = False
        supply.ovp = 15
        self.assertEqual(interface.write.call_args_list,
                         [call("ISET 0.5"), call("VSET 12"), call("OUT ON"),
                          call("OUT OFF"), call("OVP 15")])
        self.assertEqual((supply.volt, supply.curr, supply.v_meas,
                          supply.i_meas, supply.ovp), (12, .5, 12.02, .0034, 15))

    def test_blank_lines_and_error(self):
        interface = Mock()
        interface.query.return_value = "\n"
        interface.read.side_effect = ["\n", "ERR 8\r\n"]
        self.assertEqual(HP6655ACompatibility(interface).error.code, 8)

    def test_wrong_reply_is_rejected(self):
        interface = Mock()
        interface.query.return_value = "ISET 0.5"
        with self.assertRaises(ValueError):
            HP6655ACompatibility(interface).volt

    def test_unsupported_commands_do_not_write(self):
        interface = Mock()
        supply = HP6655ACompatibility(interface)
        for action in [supply.reset, supply.clear_protection,
                       lambda: setattr(supply, "ocp", True), lambda: supply.output]:
            with self.assertRaises(NotImplementedError):
                action()
        interface.write.assert_not_called()
