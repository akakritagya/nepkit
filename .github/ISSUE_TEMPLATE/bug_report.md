---
name: Bug report
about: Something behaves differently than the README/DEMO.md says it should
title: ""
labels: bug
assignees: ""
---

## Command and output

<!-- The exact command you ran and what it printed -- copy/paste, not a
paraphrase. Include --json output if you were scripting against it. -->

## Expected

<!-- What you expected instead, ideally with the README/DEMO.md section that
led you to expect it. -->

## Environment

- nepkit version (`nepkit --version` or `pip show nepkit`):
- Python version:
- OS (and Git Bash, if on Windows):

## Wrong date vs. wrong behavior

- [ ] This is a wrong *conversion result* (a specific date maps incorrectly)
- [ ] This is wrong *behavior* (crash, wrong exit code, CLI/library mismatch,
      docs mismatch)

If it's a wrong conversion result, include both the BS and AD dates involved
— that's usually a data issue, and the report will need to go through the
cross-check process in
[DATA.md](https://github.com/akakritagya/nepkit/blob/main/src/nepkit/data/DATA.md)
rather than a code fix.
