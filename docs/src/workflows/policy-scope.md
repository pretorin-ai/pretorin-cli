# Policy & Scope Questionnaires

Pretorin uses questionnaire workflows to capture organizational policy information and system scope details. Both follow a similar lifecycle: answer questions, generate documents, review, and iterate.

## Policy Questionnaire Workflow

Organization policies (e.g., Access Control Policy, Incident Response Policy) are defined at the org level and apply across systems.

### 1. List Available Policies

```bash
pretorin policy list
```

Or via MCP: `pretorin_list_org_policies`

### 2. View Current State

```bash
# Show questionnaire state and saved review findings
pretorin policy show --policy <policy-id-or-name>
```

Or via MCP:

```
pretorin_get_pending_policy_questions  # lightweight — only unanswered
pretorin_get_policy_question_detail    # guidance and examples per question
```

### 3. Answer Questions

**Via CLI** — Draft answers from your workspace:

```bash
# Preview proposed answers
pretorin policy populate --policy <policy-id>

# Apply answers to the platform
pretorin policy populate --policy <policy-id> --apply
```

**Via MCP** — Answer individually for precise control:

```
pretorin_answer_policy_question(policy_id, question_id, answer)
```

Or batch-update multiple answers:

```
pretorin_patch_org_policy_qa(policy_id, updates=[{question_id, answer}, ...])
```

### 4. Generate Policy Document

Once questions are answered, trigger AI document generation:

```
pretorin_trigger_policy_generation(policy_id)
```

### 5. Review

Trigger an AI review of the policy:

```
pretorin_trigger_policy_review(policy_id)
pretorin_get_policy_review_results(policy_id)  # poll for results
```

Review results include findings with severity levels, affected sections, and recommended fixes.

### 6. Track Status

```
pretorin_get_policy_workflow_state(policy_id)
pretorin_get_policy_analytics()
```

## Scope Questionnaire Workflow

Scope questionnaires are system+framework specific. They define what's in scope, what's excluded, and system boundary details.

### 1. View Current State

```bash
# Show scope questionnaire state and review findings
pretorin scope show --system "My System" --framework-id fedramp-moderate
```

Or via MCP:

```
pretorin_get_pending_scope_questions(system_id, framework_id)
pretorin_get_scope_question_detail(system_id, framework_id, question_id)
```

### 2. Answer Questions

**Via CLI** — Draft answers from your workspace:

```bash
# Preview proposed answers
pretorin scope populate --system "My System" --framework-id fedramp-moderate

# Apply answers to the platform
pretorin scope populate --system "My System" --framework-id fedramp-moderate --apply
```

**Via MCP** — Answer individually:

```
pretorin_answer_scope_question(system_id, framework_id, question_id, answer)
```

Or batch-update:

```
pretorin_patch_scope_qa(system_id, framework_id, updates=[{question_id, answer}, ...])
```

### 3. Generate Scope Document

```
pretorin_trigger_scope_generation(system_id, framework_id)
```

### 4. Review

```
pretorin_trigger_scope_review(system_id, framework_id)
pretorin_get_scope_review_results(system_id, framework_id)
```

### 5. View Full Scope

```
pretorin_get_scope(system_id, framework_id)
```

Returns scope narrative, excluded controls, and Q&A responses.

## Bulk Questionnaire Campaigns

For answering many questions at once, use campaigns:

```bash
# Answer all incomplete policy questions
pretorin campaign policy --mode answer --all-incomplete

# Answer scope questions
pretorin campaign scope --mode answer --system "My System" --framework-id fedramp-moderate

# Fix review findings
pretorin campaign policy --mode review-fix --policies <policy-id>
```

See [Campaign Workflows](./campaigns.md) for details on the campaign lifecycle.
