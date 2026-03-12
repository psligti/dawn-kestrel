# Policy Agent Evals (Ash-Hawk)

This eval pack is authored in the dawn-kestrel repo and executed with ash-hawk.

The scenarios evaluate policy-based agent behavior using:

- `llm_judge` with explicit artifact-grounded rubric
- transcript-based constraints (`transcript` grader)
- output structure checks (`format` + `schema`)

## Files

- `policy_rules_artifact_judgement.scenario.yaml`
- `policy_react_failure_recovery_judgement.scenario.yaml`
- `policy_plan_execute_todo_evidence_judgement.scenario.yaml`
- `policy_router_budget_routing_judgement.scenario.yaml`
- `policy_approval_gate_judgement.scenario.yaml`
- `policy_budget_hard_stop_judgement.scenario.yaml`

## Run from ash-hawk

```bash
uv run ash-hawk scenario validate ../dawn-kestrel/evals/policy-agents/
uv run ash-hawk scenario run ../dawn-kestrel/evals/policy-agents/policy_rules_artifact_judgement.scenario.yaml --sut sdk_dawn_kestrel --policy-mode rules
uv run ash-hawk scenario matrix ../dawn-kestrel/evals/policy-agents/ --sut sdk_dawn_kestrel --policies rules,react,plan_execute,router,fsm --models <model_a>,<model_b>
```

## Report

```bash
uv run ash-hawk scenario report --run <run_id>
```
