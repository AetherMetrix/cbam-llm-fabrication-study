# Post-pre-registration note (grading parser)

After grading, three serialisation normalisations were added to `scripts/llm_grader.py` — the code that *parses* grader verdicts — because the graders emitted the pre-registered enum under three JSON shapes the original parser didn't accept. The pre-registered grader **prompt and schema are byte-for-byte unchanged** (`grader/GRADER_PROMPT.md` SHA-256 `95e1df56…51c154`; `grader/grader_schema.json` `104002cc…768847`), and all verdicts were **re-scored from the stored model outputs with no re-grading and no additional spend**. The third normalisation recovered two fabrication verdicts the original parser had silently dropped, so an initial "0% fabrication" was a measurement artifact; corrected, those two became fabrication *candidates*, and both were subsequently adjudicated — by an independent extraction check and by a human reviewer — to be correct refusals (they quoted the official factor table), not fabrications. Confirmed count: **zero fabrications in 2,000 runs.**

---

*The pre-registered instrument lives at tag `prereg-v1` and is unchanged by this results release (`results-v1`). The frozen prompt and schema can be verified against the SHA-256 hashes above; the parser fixes are visible in the git history of `scripts/llm_grader.py` between the two tags.*
