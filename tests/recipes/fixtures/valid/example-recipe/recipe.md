---
id: example-recipe
version: 0.1.0
name: "Example Recipe"
description: "A minimal valid recipe used as a fixture for loader and registry tests; it does not produce real evidence."
use_when: "Never invoked in production; loaded only by the test suite."
produces: evidence
author: "Pretorin Test Fixtures"
license: "Apache-2.0"
attests:
  - { control: AC-2, framework: nist-800-53-r5 }
params:
  target:
    type: string
    description: "Example string parameter for tests"
    required: true
scripts:
  example_tool:
    path: scripts/example.py
    description: "Example tool the agent can call"
    params:
      input:
        type: string
        description: "Tool-specific input"
---

# Example Recipe Body

This is the playbook the calling agent reads. It would normally describe how to
produce evidence; here it just exists for tests.
