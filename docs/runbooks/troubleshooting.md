# Diagnose a local failure

## Preconditions

Have access to the affected terminal and checkout. Keep private output and
credentials out of public issues and committed logs.

## Actions

1. Record app/Python/OS/terminal and `gh --version`, without credential values.
2. For startup/discovery, check PATH and run `gh help reference` and `gh --help`.
3. For execution, inspect the preview's working directory and repository field.
4. If stdin/editor interaction is required, rerun only after choosing Terminal.
5. For Stop/timeout, inspect GitHub state with a read-only command before retrying
   any mutation. Cancellation does not roll back completed actions.
6. Reproduce with a fixture or minimal read-only command where possible.

## Verification

Confirm the local catalog loads and that a fixture/read-only command completes
with expected context. Run the relevant pytest file for a code regression.

## Escalation

Submit sanitized reproduction steps through the bug template. Use
[security reporting](../../.github/SECURITY.md) for vulnerabilities. No automatic
collector, durable error file, or on-call service exists.
