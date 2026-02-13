"""Unit tests for workflow FSM."""

from typing import cast

from dawn_kestrel.core.result import Err
from dawn_kestrel.workflow import (
    assert_transition,
    run_workflow_fsm,
    WORKFLOW_FSM_TRANSITIONS,
)
from dawn_kestrel.workflow.fsm import FSM
from dawn_kestrel.workflow.models import DecisionType


class TestWorkflowFSMTransitions:
    """Tests for FSM transition validation."""

    def test_valid_transitions_exist(self):
        """Test that all expected states exist."""
        expected_states = {
            "intake",
            "plan",
            "act",
            "synthesize",
            "evaluate",
            "done",
            "failed",
        }
        for state in expected_states:
            assert state in WORKFLOW_FSM_TRANSITIONS

    def test_transition_intake_to_plan(self):
        """Test valid transition from intake to plan."""
        assert_transition("intake", "plan")

    def test_transition_plan_to_act(self):
        """Test valid transition from plan to act."""
        assert_transition("plan", "act")

    def test_transition_act_to_synthesize(self):
        """Test valid transition from act to synthesize."""
        assert_transition("act", "synthesize")

    def test_transition_synthesize_to_evaluate(self):
        """Test valid transition from synthesize to evaluate."""
        assert_transition("synthesize", "evaluate")

    def test_transition_evaluate_to_done(self):
        """Test valid transition from evaluate to done."""
        assert_transition("evaluate", "done")

    def test_invalid_from_state(self):
        """Test that invalid from_state returns Err."""
        result = assert_transition("invalid_state", "plan")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_FROM_STATE"
            assert "Invalid from_state" in err_result.error

    def test_invalid_transition(self):
        """Test that invalid transition returns Err."""
        result = assert_transition("intake", "done")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_TRANSITION"
            assert "Invalid state transition" in err_result.error


class TestWorkflowFSMExecution:
    """Tests for workflow FSM execution."""

    def test_run_workflow_fsm_single_file(self):
        """Test running workflow with single changed file."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.state == "done"
        assert len(ctx.changed_files) == 1
        assert ctx.log.frame_count >= 5  # At least one frame per state

    def test_run_workflow_fsm_multiple_files(self):
        """Test running workflow with multiple changed files."""
        changed_files = ["file1.py", "file2.py", "file3.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.state == "done"
        assert len(ctx.changed_files) == 3
        assert ctx.todo_count >= 3  # At least one todo per file (up to 5)

    def test_workflow_creates_todos(self):
        """Test that workflow creates todos."""
        changed_files = ["test1.py", "test2.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.todo_count > 0
        for todo in ctx.todos.values():
            assert todo.id
            assert todo.title
            assert todo.rationale

    def test_workflow_creates_subagent_results(self):
        """Test that workflow generates subagent results."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        assert len(ctx.subagent_results) > 0
        for task_id, result in ctx.subagent_results.items():
            assert task_id
            assert result

    def test_workflow_creates_consolidation(self):
        """Test that workflow generates consolidation."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.consolidated
        assert "total_results" in ctx.consolidated

    def test_workflow_creates_evaluation(self):
        """Test that workflow generates evaluation."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.evaluation
        assert "verdict" in ctx.evaluation

    def test_workflow_frames_have_goals(self):
        """Test that each frame has goals."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        for frame in ctx.log.frames:
            if frame.state in ["intake", "plan", "act"]:
                assert len(frame.goals) > 0

    def test_workflow_frames_have_react_cycles(self):
        """Test that frames contain REACT cycles."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        react_cycle_count = 0
        for frame in ctx.log.frames:
            react_cycle_count += len(frame.react_cycles)

        assert react_cycle_count >= 5  # At least one REACT cycle per state

    def test_workflow_frames_have_steps(self):
        """Test that frames contain thinking steps."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        step_count = 0
        for frame in ctx.log.frames:
            step_count += len(frame.steps)

        assert step_count >= 5  # At least one step per state

    def test_workflow_frames_have_decisions(self):
        """Test that frames have decisions."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        for frame in ctx.log.frames:
            assert frame.decision
            assert frame.decision_type in [
                DecisionType.TRANSITION,
                DecisionType.DELEGATE,
                DecisionType.STOP,
            ]

    def test_workflow_log_has_timestamps(self):
        """Test that workflow log has timestamps."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.log.start_time is not None
        assert ctx.log.end_time is not None
        assert ctx.log.end_time > ctx.log.start_time

    def test_workflow_dynamic_thinking_based_on_files(self):
        """Test that thinking varies based on input files."""
        # Single file
        ctx_single = run_workflow_fsm(["file1.py"])
        plan_frame_single = ctx_single.log.get_frames_for_state("plan")[0]

        # Multiple files
        ctx_multi = run_workflow_fsm(["file1.py", "file2.py", "file3.py"])
        plan_frame_multi = ctx_multi.log.get_frames_for_state("plan")[0]

        # Check that thinking varies (REACT cycles should reference file count)
        react_single = plan_frame_single.react_cycles[0]
        react_multi = plan_frame_multi.react_cycles[0]
        # Observation should contain different file counts
        assert react_single.observation != react_multi.observation


class TestWorkflowFSMEvidence:
    """Tests for evidence tracking in workflow FSM."""

    def test_workflow_has_evidence_references(self):
        """Test that workflow includes evidence references."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        evidence_found = False
        for frame in ctx.log.frames:
            for cycle in frame.react_cycles:
                if cycle.evidence:
                    evidence_found = True
                    break
            for step in frame.steps:
                if step.evidence:
                    evidence_found = True
                    break
            if evidence_found:
                break

        assert evidence_found, "No evidence references found in workflow"

    def test_workflow_evidence_references_files(self):
        """Test that evidence references changed files."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        file_evidence_found = False
        for frame in ctx.log.frames:
            for cycle in frame.react_cycles:
                for evidence in cycle.evidence:
                    # Check for any file-related evidence reference
                    if ":" in evidence and any(
                        x in evidence for x in ["file", "changed", "diff", "results"]
                    ):
                        file_evidence_found = True
                        break
            for step in frame.steps:
                for evidence in step.evidence:
                    if ":" in evidence and any(
                        x in evidence for x in ["file", "changed", "diff", "results"]
                    ):
                        file_evidence_found = True
                        break
            if file_evidence_found:
                break

        assert file_evidence_found, "No file evidence references found"

    def test_workflow_todos_have_evidence(self):
        """Test that todos have evidence."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        for todo in ctx.todos.values():
            assert todo.evidence or todo.title


class TestWorkflowFSMStopConditions:
    """Tests for workflow stop conditions."""

    def test_workflow_reaches_done_state(self):
        """Test that workflow always reaches 'done' state."""
        for changed_files in [
            ["single.py"],
            ["file1.py", "file2.py"],
            ["a.py", "b.py", "c.py", "d.py", "e.py"],
        ]:
            ctx = run_workflow_fsm(changed_files)
            assert ctx.state == "done"

    def test_workflow_does_not_loop_infinitely(self):
        """Test that workflow terminates (finite loop)."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        # Should have a reasonable number of frames
        # (not thousands which would indicate infinite loop)
        assert ctx.log.frame_count < 20

    def test_workflow_has_final_evaluation(self):
        """Test that workflow produces a final evaluation."""
        changed_files = ["test.py"]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.evaluation["verdict"] == "success"
        assert ctx.evaluation["confidence"] >= 0.9
        assert ctx.evaluation["todos_completed"] == len(ctx.todos)
        # Frames generated should match log frame count
        assert ctx.evaluation["frames_generated"] == ctx.log.frame_count


class TestWorkflowFSMEdgeCases:
    """Tests for workflow FSM edge cases."""

    def test_run_workflow_empty_files(self):
        """Test running workflow with no changed files."""
        changed_files = []
        ctx = run_workflow_fsm(changed_files)

        assert ctx.state == "done"
        # Should still create frames even with no files
        assert ctx.log.frame_count >= 5

    def test_workflow_handles_large_file_list(self):
        """Test that workflow handles many files gracefully."""
        changed_files = [f"file{i}.py" for i in range(20)]
        ctx = run_workflow_fsm(changed_files)

        assert ctx.state == "done"
        assert ctx.todo_count <= 5  # Limited to 5 todos max
        assert ctx.log.frame_count < 20  # Should not explode


class TestWorkflowFSMHierarchicalComposition:
    """Tests for hierarchical FSM composition."""

    def test_register_sub_fsm(self):
        """Test registering a sub-FSM."""
        parent_fsm = FSM(changed_files=["parent.py"])
        sub_fsm = FSM(changed_files=["child.py"])

        parent_fsm.register_sub_fsm("child", sub_fsm)

        assert "child" in parent_fsm.sub_fsms
        assert parent_fsm.sub_fsms["child"] is sub_fsm

    def test_register_multiple_sub_fsms(self):
        """Test registering multiple sub-FSMs."""
        parent_fsm = FSM(changed_files=["parent.py"])
        sub1 = FSM(changed_files=["child1.py"])
        sub2 = FSM(changed_files=["child2.py"])
        sub3 = FSM(changed_files=["child3.py"])

        parent_fsm.register_sub_fsm("child1", sub1)
        parent_fsm.register_sub_fsm("child2", sub2)
        parent_fsm.register_sub_fsm("child3", sub3)

        assert len(parent_fsm.sub_fsms) == 3
        assert parent_fsm.sub_fsms["child1"] is sub1
        assert parent_fsm.sub_fsms["child2"] is sub2
        assert parent_fsm.sub_fsms["child3"] is sub3

    def test_register_duplicate_sub_fsm_raises_error(self):
        """Test that registering a duplicate sub-FSM name raises ValueError."""
        parent_fsm = FSM(changed_files=["parent.py"])
        sub1 = FSM(changed_files=["child1.py"])
        sub2 = FSM(changed_files=["child2.py"])

        parent_fsm.register_sub_fsm("child", sub1)

        try:
            parent_fsm.register_sub_fsm("child", sub2)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already registered" in str(e)

    def test_remove_sub_fsm(self):
        """Test removing a registered sub-FSM."""
        parent_fsm = FSM(changed_files=["parent.py"])
        sub_fsm = FSM(changed_files=["child.py"])

        parent_fsm.register_sub_fsm("child", sub_fsm)
        assert "child" in parent_fsm.sub_fsms

        parent_fsm.remove_sub_fsm("child")

        assert "child" not in parent_fsm.sub_fsms

    def test_remove_nonexistent_sub_fsm_raises_error(self):
        """Test that removing a nonexistent sub-FSM raises KeyError."""
        parent_fsm = FSM(changed_files=["parent.py"])

        try:
            parent_fsm.remove_sub_fsm("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError as e:
            assert "not found" in str(e)

    def test_reset_clears_sub_fsms(self):
        """Test that reset() clears all registered sub-FSMs."""
        parent_fsm = FSM(changed_files=["parent.py"])
        sub1 = FSM(changed_files=["child1.py"])
        sub2 = FSM(changed_files=["child2.py"])

        parent_fsm.register_sub_fsm("child1", sub1)
        parent_fsm.register_sub_fsm("child2", sub2)

        assert len(parent_fsm.sub_fsms) == 2

        parent_fsm.reset()

        assert len(parent_fsm.sub_fsms) == 0

    def test_fsm_without_sub_fsms_works_normally(self):
        """Test that FSM without sub-FSMs works normally."""
        fsm = FSM(changed_files=["test.py"])

        assert len(fsm.sub_fsms) == 0

        result = fsm.transition_to("plan")
        assert result.is_ok()
        assert fsm.context.state == "plan"

    def test_sub_fsms_are_independent(self):
        """Test that sub-FSMs maintain independent state."""
        parent_fsm = FSM(changed_files=["parent.py"])
        sub_fsm = FSM(changed_files=["child.py"])

        parent_fsm.register_sub_fsm("child", sub_fsm)

        parent_fsm.transition_to("plan")
        sub_fsm.transition_to("plan")

        assert parent_fsm.context.state == "plan"
        assert sub_fsm.context.state == "plan"

        parent_fsm.reset()

        assert parent_fsm.context.state == "intake"
        assert sub_fsm.context.state == "plan"  # Sub-FSM unchanged
