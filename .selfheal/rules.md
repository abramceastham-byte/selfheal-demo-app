# Notes for the agent

- Write a failing test that reproduces the error first, then the smallest fix that makes it pass.
- Put the new test in `tests/`. Do not change existing tests unless they are wrong.
- Do not change endpoint paths or response field names.
- Run `pytest` before finishing; it must pass.
- Never edit files matching `protected_files` in `.selfheal/config.yml`.
