---
id: runnable-recipe
version: 0.2.0
name: "Runnable Recipe"
description: "A pure-transformation recipe used by the cli `recipe run` tests; it returns the params it received plus a static greeting and never touches the network."
use_when: "Only used by tests of `pretorin recipe run`; it has no real auditor utility."
produces: evidence
author: "Pretorin Test Fixtures"
license: "Apache-2.0"
scripts:
  echo:
    path: scripts/echo.py
    description: "Echo back the params for cli-run testing"
    params:
      message:
        type: string
        description: "Anything the test wants to round-trip"
---

# Runnable Recipe Body

Test fixture only. The `echo` script returns its kwargs so the cli-run tests
can assert on the parsed param shape.
