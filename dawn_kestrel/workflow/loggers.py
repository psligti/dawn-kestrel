"""Loggers for REACT-enhanced thinking traces.

This module provides logging implementations for displaying and exporting
structured thinking traces from the REACT framework.

Loggers:
- ConsoleLogger: Human-readable console output with REACT cycles
- JsonLogger: Structured JSON export for downstream processing
"""

import json
from datetime import datetime
from typing import Any, cast


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        data = cast(dict[str, Any], obj)
        return data.get(key, default)
    return getattr(obj, key, default)


def _as_jsonable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        data = cast(dict[str, Any], obj)
        return {k: _as_jsonable(v) for k, v in data.items()}
    if isinstance(obj, list):
        items = cast(list[Any], obj)
        return [_as_jsonable(item) for item in items]
    if hasattr(obj, "to_dict"):
        return _as_jsonable(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return _as_jsonable(vars(obj))
    return obj


class ConsoleLogger:
    """Human-readable console logger for thinking traces.

    Formats REACT cycles and thinking steps for terminal display.
    Shows reasoning, actions, and observations in a structured way.
    """

    @staticmethod
    def log_frame(frame: Any) -> None:
        """Log a single thinking frame to console.

        Args:
            frame: ThinkingFrame to log
        """
        print(f"\n{'=' * 60}")
        state = str(_get(frame, "state", "unknown"))
        print(f"== {state.upper()} ==")
        print(f"{'=' * 60}")

        goals = _get(frame, "goals", [])
        if goals:
            print("\n📋 Goals:")
            for i, goal in enumerate(goals, 1):
                print(f"  {i}. {goal}")

        checks = _get(frame, "checks", [])
        if checks:
            print("\n✓ Checks:")
            for check in checks:
                print(f"  • {check}")

        risks = _get(frame, "risks", [])
        if risks:
            print("\n⚠️  Risks:")
            for risk in risks:
                print(f"  • {risk}")

        steps = _get(frame, "steps", [])
        if steps:
            print("\n🤔 Steps:")
            for i, step in enumerate(steps, 1):
                kind = _get(step, "kind", "reason")
                kind_value = _get(kind, "value", kind)
                kind_emoji = {
                    "reason": "💭",
                    "act": "⚡",
                    "observe": "👁️",
                }.get(str(kind_value), "•")
                why = str(_get(step, "why", ""))
                print(f"  {kind_emoji} [{i}] {str(kind_value).upper()}: {why}")
                evidence = _get(step, "evidence", [])
                if evidence:
                    print(f"      Evidence: {', '.join(evidence)}")
                next_action = _get(step, "next", "")
                if next_action:
                    print(f"      Next: {next_action}")
                action_result = _get(step, "action_result", None)
                if action_result:
                    print(f"      Result: {action_result}")

        react_cycles = _get(frame, "react_cycles", [])
        if react_cycles:
            print("\n🔄 REACT Cycles:")
            for i, cycle in enumerate(react_cycles, 1):
                print(f"\n  ┌─ Cycle {i} ─────────────────────")
                print(f"  │ 💭 REASON: {_get(cycle, 'reasoning', '')}")
                print(f"  │ ⚡ ACTION:  {_get(cycle, 'action', '')}")
                print(f"  │ 👁️ OBSERVE: {_get(cycle, 'observation', '')}")
                tools_used = _get(cycle, "tools_used", [])
                if tools_used:
                    print(f"  │ 🔧 Tools:   {', '.join(tools_used)}")
                evidence = _get(cycle, "evidence", [])
                if evidence:
                    print(f"  │ 📎 Evidence: {', '.join(evidence)}")
                print("  └─────────────────────────────")

        decision = _get(frame, "decision", "")
        if decision:
            decision_type = _get(frame, "decision_type", "transition")
            decision_value = _get(decision_type, "value", decision_type)
            print(f"\n🎯 Decision: {decision}")
            print(f"   Type: {str(decision_value).upper()}")

        ts = _get(frame, "ts", None)
        if isinstance(ts, datetime):
            ts_render = ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_render = str(ts) if ts is not None else "unknown"
        print(f"\n⏰ Timestamp: {ts_render}\n")

    @staticmethod
    def log_log(log: Any) -> None:
        """Log all frames in a RunLog.

        Args:
            log: RunLog to display
        """
        frames = _get(log, "frames", [])
        for frame in frames:
            ConsoleLogger.log_frame(frame)

        print(f"\n{'=' * 60}")
        print("📊 SUMMARY")
        print(f"{'=' * 60}")
        frame_count = _get(log, "frame_count", len(frames))
        print(f"Total frames: {frame_count}")
        start_time = _get(log, "start_time", None)
        end_time = _get(log, "end_time", None)
        if isinstance(start_time, datetime):
            print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if isinstance(end_time, datetime):
            print(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if isinstance(start_time, datetime):
                duration = (end_time - start_time).total_seconds()
                print(f"Duration: {duration:.1f}s")
        print()


class JsonLogger:
    """Structured JSON logger for thinking traces.

    Exports thinking traces as JSON for downstream processing,
    analysis, or storage.
    """

    @staticmethod
    def log(log: Any, indent: int = 2) -> str:
        """Export a RunLog to JSON string.

        Args:
            log: RunLog to export
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation of the log
        """
        if hasattr(log, "to_json"):
            return log.to_json(indent=indent)
        return json.dumps(_as_jsonable(log), indent=indent)

    @staticmethod
    def log_frame(frame: Any, indent: int = 2) -> str:
        """Export a single ThinkingFrame to JSON string.

        Args:
            frame: ThinkingFrame to export
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation of the frame
        """
        if hasattr(frame, "to_dict"):
            return json.dumps(frame.to_dict(), indent=indent)
        return json.dumps(_as_jsonable(frame), indent=indent)

    @staticmethod
    def log_react_cycle(cycle: Any, indent: int = 2) -> str:
        """Export a REACT cycle to JSON string.

        Args:
            cycle: ReactStep to export
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation of the REACT cycle
        """
        if hasattr(cycle, "to_dict"):
            return json.dumps(cycle.to_dict(), indent=indent)
        return json.dumps(_as_jsonable(cycle), indent=indent)
