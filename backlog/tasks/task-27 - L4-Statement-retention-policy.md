---
id: TASK-27
title: 'L4: Statement retention policy'
status: To Do
assignee: []
created_date: '2026-07-26 05:11'
labels:
  - phase-1
milestone: m-6
dependencies:
  - TASK-12
  - TASK-20
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
As a user, raw statement files are deleted automatically after a defined window once balances are confirmed, and account deletion reaches stored PDFs and per-sender passwords, so my most sensitive documents are not retained indefinitely.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Configurable retention window with scheduled purge job
- [ ] #2 Deletion covers stored PDFs and passwords (with X3)
- [ ] #3 Retention stated in the privacy policy
<!-- AC:END -->
