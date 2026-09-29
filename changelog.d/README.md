# Changelog entries

One file per change, so two open PRs never edit the same line of `changelog.md`.

- `<short-slug>.feature.md` lands under **Features/Improvements**.
- `<short-slug>.fix.md` lands under **Fixes**.

Each file holds one or more lines written exactly as they read in the changelog:

```
* **[Mission Generation]** A carrier keeps the same TACAN channel every mission.
```

`python tools/changelog.py render` prints the changelog with these folded in; the
release build ships that. `python tools/changelog.py fold` writes them into
`changelog.md` for good, when a version is cut. A test fails CI on a malformed file.
