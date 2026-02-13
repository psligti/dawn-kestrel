"""Loggers for REACT-enhanced thinking traces.

This module provides logging implementations for displaying and exporting
structured thinking traces from the REACT framework.

Loggers:
- ConsoleLogger: Human-readable console output with REACT cycles
- JsonLogger: Structured JSON export for downstream processing
"""

import json

from dawn_kestrel.workflow.models import ThinkingFrame, ReactStep, RunLog


class ConsoleLogger:
    """Human-readable console logger for thinking traces.

    Formats REACT cycles and thinking steps for terminal display.
    Shows reasoning, actions, and observations in a structured way.
    """

    @staticmethod
    def log_frame(frame: ThinkingFrame) -> None:
        """Log a single thinking frame to console.

        Args:
            frame: ThinkingFrame to log
        """
        print(f"\n{'=' * 60}")
        print(f"== {frame.state.upper()} ==")
        print(f"{'=' * 60}")

        if frame.goals:
            print("\n📋 Goals:")
            for i, goal in enumerate(frame.goals, 1):
                print(f"  {i}. {goal}")

        if frame.checks:
            print("\n✓ Checks:")
            for check in frame.checks:
                print(f"  • {check}")

        if frame.risks:
            print("\n⚠️  Risks:")
            for risk in frame.risks:
                print(f"  • {risk}")

        if frame.steps:
            print("\n🤔 Steps:")
            for i, step in enumerate(frame.steps, 1):
                kind_emoji = {
                    "reason": "💭",
                    "act": "⚡",
                    "observe": "👁️",
                }.get(step.kind.value, "•")
                print(f"  {kind_emoji} [{i}] {step.kind.value.upper()}: {step.why}")
                if step.evidence:
                    print(f"      Evidence: {', '.join(step.evidence)}")
                if step.next:
                    print(f"      Next: {step.next}")
                if step.action_result:
                    print(f"      Result: {step.action_result}")

        if frame.react_cycles:
            print("\n🔄 REACT Cycles:")
            for i, cycle in enumerate(frame.react_cycles, 1):
                print(f"\n  ┌─ Cycle {i} ─────────────────────")
                print(f"  │ 💭 REASON: {cycle.reasoning}")
                print(f"  │ ⚡ ACTION:  {cycle.action}")
                print(f"  │ 👁️ OBSERVE: {cycle.observation}")
                if cycle.tools_used:
                    print(f"  │ 🔧 Tools:   {', '.join(cycle.tools_used)}")
                if cycle.evidence:
                    print(f"  │ 📎 Evidence: {', '.join(cycle.evidence)}")
                print("  └─────────────────────────────")

        if frame.decision:
            print(f"\n🎯 Decision: {frame.decision}")
            print(f"   Type: {frame.decision_type.value.upper()}")

        print(f"\n⏰ Timestamp: {frame.ts.strftime('%Y-%m-%d %H:%M:%S')}\n")

    @staticmethod
    def log_log(log: RunLog) -> None:
        """Log all frames in a RunLog.

        Args:
            log: RunLog to display
        """
        for frame in log.frames:
            ConsoleLogger.log_frame(frame)

        print(f"\n{'=' * 60}")
        print("📊 SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total frames: {log.frame_count}")
        if log.start_time:
            print(f"Started: {log.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if log.end_time:
            print(f"Ended: {log.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if log.start_time:
                duration = (log.end_time - log.start_time).total_seconds()
                print(f"Duration: {duration:.1f}s")
        print()


class JsonLogger:
    """Structured JSON logger for thinking traces.

    Exports thinking traces as JSON for downstream processing,
    analysis, or storage.
    """

    @staticmethod
    def log(log: RunLog, indent: int = 2) -> str:
        """Export a RunLog to JSON string.

        Args:
            log: RunLog to export
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation of the log
        """
        return log.to_json(indent=indent)

    @staticmethod
    def log_frame(frame: ThinkingFrame, indent: int = 2) -> str:
        """Export a single ThinkingFrame to JSON string.

        Args:
            frame: ThinkingFrame to export
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation of the frame
        """
        return json.dumps(frame.to_dict(), indent=indent)

    @staticmethod
    def log_react_cycle(cycle: ReactStep, indent: int = 2) -> str:
        """Export a REACT cycle to JSON string.

        Args:
            cycle: ReactStep to export
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation of the REACT cycle
        """
        return json.dumps(cycle.to_dict(), indent=indent)
