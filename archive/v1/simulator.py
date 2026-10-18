#!/usr/bin/env python3
"""Decimal Pascaline reference model, with ordered animation events.

This is an arithmetic/state model; passing its tests does not demonstrate that
the accompanying physical carry mechanism works.

Wheel 0 is the units wheel, wheel 1 the tens wheel, etc. ``advance(wheel)`` is
one forward 36-degree detent of one selected wheel. A 9 -> 0 transition emits
``wheel_step``, then ``carry``, then advances the next wheel recursively. At the
highest wheel, ``carry.to_wheel`` is None and an ``overflow`` event follows.

``add(amount)`` is a complete operation made of such detents. Decimal places are
entered from low to high; the highest installed wheel receives all remaining
input. For a two-wheel model, +127 means seven units steps followed by twelve
tens steps. This preserves every actual carry event while avoiding +1 expansion
of the whole amount. There are no invisible/software-only input wheels.

Results report overflow for THIS operation: ``overflow_count`` counts complete
wraps through 10**digits; ``overflow`` is its Boolean form. The display contains
the remainder, never a hidden extra digit. ``total_overflow_count`` accumulates
wraps since construction/reset. ``reset(value)`` loads a starting state and
clears that history; its one ``reset`` event is not a mechanical carry event.

All events have a per-operation zero-based ``sequence`` and a string ``event``.
``wheel_step`` has wheel/from_digit/to_digit/source/angle_degrees fields;
``source`` is ``input`` or ``carry``. Carry and overflow events follow the
wheel_step that caused them, making the list directly replayable in order.

Version-one resource limits are explicit: 1..12 installed wheels and addends
0..9999. This bounds the event list even for a one-wheel model. Both limits are
constants so later versions can revisit the input budget deliberately.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from typing import Any


MAX_DIGITS = 12
MAX_ADDEND = 9999


def _integer(name: str, value: Any, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer (not bool)")
    if not lower <= value <= upper:
        raise ValueError(f"{name} must be in {lower}..{upper}")
    return value


@dataclass(frozen=True)
class OperationResult:
    """Snapshot of one operation; digit_values are ordered units first."""

    operation: str
    digits: int
    start: int
    amount: int
    value: int
    display: str
    digit_values: tuple[int, ...]
    overflow: bool
    overflow_count: int
    total_overflow_count: int
    events: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a detached, JSON-compatible mapping (arrays are lists)."""
        result = asdict(self)
        result["digit_values"] = list(self.digit_values)
        result["events"] = list(result["events"])
        return result


class Pascaline:
    """Extensible decimal counter; modifications occur only via methods."""

    def __init__(self, digits: int = 2, start: int = 0) -> None:
        self._digits = _integer("digits", digits, 1, MAX_DIGITS)
        self._modulus = 10**self._digits
        start = _integer("start", start, 0, self._modulus - 1)
        self._wheels = self._split(start)
        self._total_overflow_count = 0

    @property
    def digits(self) -> int:
        return self._digits

    @property
    def modulus(self) -> int:
        return self._modulus

    @property
    def value(self) -> int:
        return sum(digit * 10**wheel for wheel, digit in enumerate(self._wheels))

    @property
    def display(self) -> str:
        return "".join(str(digit) for digit in reversed(self._wheels))

    @property
    def digit_values(self) -> tuple[int, ...]:
        return tuple(self._wheels)

    @property
    def total_overflow_count(self) -> int:
        return self._total_overflow_count

    def _split(self, value: int) -> list[int]:
        return [(value // 10**wheel) % 10 for wheel in range(self.digits)]

    @staticmethod
    def _emit(events: list[dict[str, Any]], event: str, **fields: Any) -> None:
        events.append({"sequence": len(events), "event": event, **fields})

    def _step(self, wheel: int, events: list[dict[str, Any]], source: str) -> None:
        before = self._wheels[wheel]
        after = (before + 1) % 10
        self._wheels[wheel] = after
        self._emit(
            events, "wheel_step", wheel=wheel, from_digit=before,
            to_digit=after, source=source, angle_degrees=36,
        )
        if before != 9:
            return
        next_wheel = wheel + 1 if wheel + 1 < self.digits else None
        self._emit(events, "carry", from_wheel=wheel, to_wheel=next_wheel)
        if next_wheel is None:
            self._total_overflow_count += 1
            self._emit(events, "overflow", wheel=wheel, count=1)
        else:
            self._step(next_wheel, events, "carry")

    def _result(
        self, operation: str, start: int, amount: int, overflows_before: int,
        events: list[dict[str, Any]],
    ) -> OperationResult:
        overflows = self.total_overflow_count - overflows_before
        return OperationResult(
            operation=operation, digits=self.digits, start=start, amount=amount,
            value=self.value, display=self.display, digit_values=self.digit_values,
            overflow=overflows > 0, overflow_count=overflows,
            total_overflow_count=self.total_overflow_count, events=tuple(events),
        )

    def advance(self, wheel: int = 0) -> OperationResult:
        """Advance one selected installed wheel by one detent, with carry."""
        wheel = _integer("wheel", wheel, 0, self.digits - 1)
        start, overflows_before = self.value, self.total_overflow_count
        events: list[dict[str, Any]] = []
        self._step(wheel, events, "input")
        return self._result("advance", start, 10**wheel, overflows_before, events)

    def add(self, amount: int) -> OperationResult:
        """Add 0..9999; +0 returns an unchanged snapshot and no events."""
        amount = _integer("amount", amount, 0, MAX_ADDEND)
        start, overflows_before = self.value, self.total_overflow_count
        events: list[dict[str, Any]] = []
        remaining = amount
        for wheel in range(self.digits):
            if wheel == self.digits - 1:
                steps = remaining
            else:
                remaining, steps = divmod(remaining, 10)
            for _ in range(steps):
                self._step(wheel, events, "input")
        return self._result("add", start, amount, overflows_before, events)

    def reset(self, value: int = 0) -> OperationResult:
        """Load a state without dial motion; reset cumulative overflow to zero."""
        value = _integer("value", value, 0, self.modulus - 1)
        start = self.value
        self._wheels = self._split(value)
        self._total_overflow_count = 0
        events: list[dict[str, Any]] = []
        self._emit(events, "reset", from_value=start, to_value=value)
        return self._result("reset", start, 0, 0, events)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=2, help="installed wheels (1..12)")
    parser.add_argument("--start", type=int, default=0, help="initial displayed value")
    parser.add_argument("--add", type=int, default=0, help="nonnegative addend (0..9999)")
    parser.add_argument("--json", action="store_true", help="JSON output (also the default)")
    parser.add_argument("--compact", action="store_true", help="emit JSON on one line")
    args = parser.parse_args(argv)
    try:
        result = Pascaline(args.digits, args.start).add(args.add)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
