# Repository review before the bug-tracking extension

Reviewed all four advertised branches and their 16 reachable commits on
November 27, 2026. Git author names describe commits; they do not necessarily
identify who pushed them. Deleted/unreachable branches and historical push
events are outside this snapshot.

| Branch | Tip | Findings |
| --- | --- | --- |
| `main` | `ea64031` | Steps 1–3 and the earlier Step 4 matcher; latest README update |
| `readme-changes` | `c6444a2` | README work already merged via PR #1; branch predates later implementation |
| `step4-resolve-conflicts` | `3f77579` | Saly's manual Levenshtein conflict resolver, CLI integration, shared TF-IDF context |
| `sura-step5` | `69e7755` | Includes Step 4 commits plus Sura's split detector and examples |

The bug-tracking branch starts at `69e7755`, preserving Steps 1–5 in their
existing order. It does not overwrite teammates' branches or merge them into
`main`. A PR targeting `sura-step5` isolates the bug-tracking contribution;
that branch's Step 4/5 work still needs the group's normal integration into
`main`.

| Git author | Existing contributions |
| --- | --- |
| Yasmeen / Yasmeen Elbik | Repository initialization; comments and cleanup in the initial pipeline |
| Karanveer Sidhu / Karanveer Singh Sidhu | Preprocessing, unchanged-line detection, dependencies, initial fixes, SimHash candidates, similarity/context helpers, README updates |
| saly Khalil / saly-kha | README and PR #1 merge; manual Step 4 conflict resolution and shared context integration |
| Sura Gaafar | Step 5 split detection, CLI integration, split examples and documentation |

## Integration observations

- Steps 4 and 5 were implemented but had not reached `main` in this snapshot.
- The active Step 4 implementation on `sura-step5` is `resolve_conflicts.py`.
  `match_candidates.py` is an earlier alternative. The extension reuses the
  active implementation and leaves both existing files intact.
- Step 1 lowercases input, appropriate to the prescribed mapping pipeline but
  unsafe as the sole test for a substantive bug-fix edit. The extension uses
  raw text for that decision.
- Step 5's default threshold is `0.8`; the outline calls `0.85` a starting
  point. The extension preserves the group's chosen setting.
- Existing tests were removed in commit `24c9371`. The new feature adds an
  independent integration suite and a reproducible synthetic evaluation.
- The attached requirements also ask for a new 25-file line-mapping dataset
  and evaluation against old datasets. The new bug-tracking evaluation is a
  separate deliverable; the repository snapshot does not contain those full
  course benchmark results.
