# In-game-pass checklist rows

One file per row, named by its id, so two open PRs adding rows never touch the same file.

- `python tools/claim_id.py row` reserves the next free `B###` and writes `B###.md` here.
- The file holds one `### B### — <what it checks> · <feature or §N> · ☐ UNTESTED` heading and
  its body, in the same format as the rows in
  [retlab-ingame-pass-checklist.md](../retlab-ingame-pass-checklist.md).
- Grade the row in this file when you fly it.
- A branch that added its row to the end of the main checklist moves it here with
  `python tools/checklist_rows.py move B###`.

Rows from before 2026-09-29 stay in the main file. `tools/checklist_board.py`, the
session-start hook and the tests read both.
