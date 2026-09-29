# Checklist rows, one file each

Every in-game-pass checklist row added after B172 is its own file here, named for its
id: `B173.md`. Rows appended at the end of
[`retlab-ingame-pass-checklist.md`](../retlab-ingame-pass-checklist.md) conflicted
between every pair of PRs that each added one; separate files never do.

To add a row:

1. `python tools/claim_id.py row` prints the next free id, reserved on GitHub.
2. Create `<id>.md` here. Its first line is the row heading, in the checklist's format:
   `### B173 — What it checks · §N · ☐ UNTESTED`, then the same body a row in the
   checklist has (what was built, Setup, Pass, Fail signatures).
3. Re-grade it later by editing its heading in this file.

Rows up to B172 stay in the checklist file and are edited there. The session-start
board, `python tools/checklist_board.py` and the tests read both places. Find any row
with `grep -rn "^### B173 " docs/dev/retlab-ingame-pass-checklist.md docs/dev/checklist-rows/`.
