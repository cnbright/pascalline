"""Arithmetic and event-contract tests; these do not validate physical geometry."""

import contextlib
import io
import json
import unittest

from simulator import MAX_ADDEND, MAX_DIGITS, Pascaline, main


class PascalineTests(unittest.TestCase):
    def assert_replayable(self, result):
        wheels = [(result.start // 10**i) % 10 for i in range(result.digits)]
        overflows = 0
        for index, event in enumerate(result.events):
            self.assertEqual(event["sequence"], index)
            if event["event"] == "wheel_step":
                wheel = event["wheel"]
                self.assertEqual(wheels[wheel], event["from_digit"])
                self.assertEqual((wheels[wheel] + 1) % 10, event["to_digit"])
                wheels[wheel] = event["to_digit"]
                self.assertEqual(event["angle_degrees"], 36)
                if event["from_digit"] == 9:
                    carry = result.events[index + 1]
                    self.assertEqual(carry["event"], "carry")
                    self.assertEqual(carry["from_wheel"], wheel)
                    self.assertEqual(carry["to_wheel"], wheel + 1 if wheel + 1 < result.digits else None)
            elif event["event"] == "carry":
                following = result.events[index + 1]
                if event["to_wheel"] is None:
                    self.assertEqual(following["event"], "overflow")
                else:
                    self.assertEqual(following["event"], "wheel_step")
                    self.assertEqual(following["wheel"], event["to_wheel"])
                    self.assertEqual(following["source"], "carry")
            elif event["event"] == "overflow":
                overflows += event["count"]
            else:
                self.fail(f"Unexpected event {event}")
        self.assertEqual(tuple(wheels), result.digit_values)
        self.assertEqual(overflows, result.overflow_count)

    def test_all_two_digit_additions(self):
        for start in range(100):
            for amount in range(100):
                result = Pascaline(start=start).add(amount)
                expected_overflows, expected_value = divmod(start + amount, 100)
                self.assertEqual(result.value, expected_value, (start, amount))
                self.assertEqual(result.overflow_count, expected_overflows, (start, amount))
                self.assertEqual(result.overflow, bool(expected_overflows), (start, amount))
                self.assertEqual(result.display, f"{expected_value:02d}")
                self.assert_replayable(result)

    def test_chained_carry(self):
        result = Pascaline(digits=4, start=1999).advance()
        self.assertEqual(result.value, 2000)
        self.assertEqual([event["event"] for event in result.events],
                         ["wheel_step", "carry", "wheel_step", "carry", "wheel_step", "carry", "wheel_step"])
        self.assertFalse(result.overflow)
        self.assert_replayable(result)

    def test_chained_overflow(self):
        result = Pascaline(digits=4, start=9999).advance()
        self.assertEqual(result.display, "0000")
        self.assertEqual(result.overflow_count, 1)
        self.assertEqual(result.events[-2]["to_wheel"], None)
        self.assertEqual(result.events[-1]["event"], "overflow")
        self.assert_replayable(result)

    def test_selected_wheel_advance(self):
        model = Pascaline(start=95)
        result = model.advance(1)
        self.assertEqual(result.value, 5)
        self.assertEqual(result.amount, 10)
        self.assertTrue(result.overflow)
        self.assertEqual(result.digit_values, (5, 0))
        self.assert_replayable(result)

    def test_decimal_input_and_large_addend(self):
        result = Pascaline().add(127)
        input_wheels = [event["wheel"] for event in result.events
                        if event["event"] == "wheel_step" and event["source"] == "input"]
        self.assertEqual(input_wheels, [0] * 7 + [1] * 12)
        self.assertEqual((result.value, result.overflow_count), (27, 1))
        self.assert_replayable(result)
        maximum = Pascaline(start=99).add(MAX_ADDEND)
        self.assertEqual((maximum.value, maximum.overflow_count), (98, 100))
        self.assertLess(len(maximum.events), 1500)
        self.assert_replayable(maximum)

    def test_single_wheel_resource_bound(self):
        result = Pascaline(digits=1, start=9).add(MAX_ADDEND)
        self.assertEqual((result.value, result.overflow_count), (8, 1000))
        self.assertLess(len(result.events), 13000)
        self.assert_replayable(result)

    def test_extension_and_leading_zeroes(self):
        result = Pascaline(digits=6, start=9999).add(2)
        self.assertEqual(result.display, "010001")
        self.assertFalse(result.overflow)
        self.assert_replayable(result)
        result = Pascaline(digits=MAX_DIGITS, start=10**MAX_DIGITS - 1).advance()
        self.assertEqual(result.value, 0)
        self.assertTrue(result.overflow)
        self.assert_replayable(result)

    def test_zero_and_per_operation_overflow(self):
        model = Pascaline(start=99)
        first = model.add(1)
        self.assertEqual(first.total_overflow_count, 1)
        no_op = model.add(0)
        self.assertEqual(no_op.events, ())
        self.assertFalse(no_op.overflow)
        self.assertEqual(no_op.overflow_count, 0)
        self.assertEqual(no_op.total_overflow_count, 1)
        self.assertEqual(no_op.value, 0)
        next_op = model.add(9999)
        self.assertEqual(next_op.overflow_count, 99)
        self.assertEqual(next_op.total_overflow_count, 100)

    def test_reset_is_load_without_carry(self):
        model = Pascaline(start=99)
        model.advance()
        result = model.reset(42)
        self.assertEqual(result.value, 42)
        self.assertEqual(result.total_overflow_count, 0)
        self.assertFalse(result.overflow)
        self.assertEqual(result.events, ({"sequence": 0, "event": "reset", "from_value": 0, "to_value": 42},))
        self.assertEqual(model.reset().display, "00")

    def test_invalid_constructor_arguments(self):
        for digits in (0, -1, MAX_DIGITS + 1):
            with self.assertRaises(ValueError):
                Pascaline(digits=digits)
        for digits in (True, 2.0, "2", None):
            with self.assertRaises(TypeError):
                Pascaline(digits=digits)
        for start in (-1, 100, 9999):
            with self.assertRaises(ValueError):
                Pascaline(start=start)
        for start in (False, 1.2, "8", None):
            with self.assertRaises(TypeError):
                Pascaline(start=start)

    def test_invalid_operations_do_not_mutate(self):
        model = Pascaline(start=23)
        for method, arguments in (
            (model.add, (-1, MAX_ADDEND + 1, 1.1, True, "7", None)),
            (model.advance, (-1, 2, 0.5, False, "0", None)),
            (model.reset, (-1, 100, 0.5, False, "0", None)),
        ):
            for argument in arguments:
                with self.assertRaises((TypeError, ValueError)):
                    method(argument)
                self.assertEqual(model.value, 23)
                self.assertEqual(model.total_overflow_count, 0)

    def test_result_snapshot_and_json(self):
        model = Pascaline(start=8)
        result = model.add(7)
        detached = result.to_dict()
        detached["events"][0]["to_digit"] = -1
        self.assertEqual(result.events[0]["to_digit"], 9)
        model.add(3)
        self.assertEqual(result.value, 15)
        encoded = json.loads(json.dumps(result.to_dict()))
        self.assertEqual(encoded["digit_values"], [5, 1])
        self.assertEqual(encoded["display"], "15")

    def test_cli(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["--digits", "2", "--start", "8", "--add", "7", "--json"])
        self.assertEqual(status, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["value"], 15)
        self.assertEqual(sum(event["event"] == "carry" for event in result["events"]), 1)

    def test_cli_rejects_invalid_inputs(self):
        for arguments in (["--digits", "0"], ["--start", "100"], ["--start", "-1"],
                          ["--add", "-1"], ["--add", "1.2"], ["--add", "10000"]):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as context:
                    main(arguments)
            self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
