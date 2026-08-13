# Security Policy

## Supported versions

nepkit is pre-1.0 (see the README's status note). Only the latest release on
PyPI is supported — there is no backport policy yet, so a fix ships as a new
version rather than a patch to an old one.

## Scope

nepkit is a pure date-conversion library: no network access, no file I/O
beyond the calendar table bundled at import time, no user input executed as
code. The realistic risk surface is narrow — the calendar data itself
(`src/nepkit/data/`, provenance in
[`DATA.md`](src/nepkit/data/DATA.md)) and the supply chain (the PyPI release
process, documented in the README's
[Releasing](README.md#releasing) section, uses Trusted Publishing specifically
so no long-lived token exists to leak).

## Reporting a vulnerability

Email **rameshneupane.ai@gmail.com** rather than opening a public issue.
Include:

- the affected version
- what's wrong and why it matters (e.g., a way to make the package execute
  untrusted input, or a compromised release artifact)
- steps to reproduce, if applicable

Expect an acknowledgment within a few days. If confirmed, a fix will be
released and credited in the release notes unless you ask otherwise.

Bugs that produce a wrong *date* (not a security issue) belong in a normal
[bug report](.github/ISSUE_TEMPLATE/bug_report.md) instead.
