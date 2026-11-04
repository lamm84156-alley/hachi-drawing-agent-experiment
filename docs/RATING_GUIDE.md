# Blind human review

Before research runs, freeze the rubric on two development tasks and record its version. Required decisions: per-part shape criteria, normalized center/size tolerances, layout-error formula and redraw threshold. Do not substitute pixel similarity or an automatic classifier for completion.

Generate packets with `hachi blind RUNS OUTPUT --seed N`. Give only OUTPUT/raters to two independent raters. Keep coordinator_only private; it contains the run mapping. No response text, condition, demonstrations, or model ID is included. Packets contain target, final drawing, intermediate agent frames and actions, allowing redraw inspection. Contents can still suggest a condition by behavior; raters must not receive assignment metadata.

Raters independently fill separate completion CSVs (0/1) and parts/redraws tables. Do not invent missing annotations. A missing part is an omission; visible but malformed parts fail shape validity. Normalize center/size errors by canvas width/height. Do not impose an expected action order. Mark redraws by the same semantic part and compare before/after layout using the frozen formula.

The coordinator preserves the original independent tables unchanged, joins blind IDs via the private mapping, computes raw agreement and Cohen's kappa before discussion, and documents discussion. Remaining disagreements go to a third rater. Supply the analysis CSV columns:

`run_id,provenance,rater1_id,rater2_id,rater1,rater2,discussion_completion,discussion_record,adjudicated,adjudicator_id`

Use provenance `human`; completion values 0/1. Leave resolution fields blank for initial agreements. For disagreements resolved by discussion, record discussion_completion and a discussion_record reference. Unresolved disagreements require adjudicated and a distinct adjudicator_id. Raw agreement and kappa always use the original independent labels. Call `hachi.analysis.agreement` on the two independent vectors and save that output before any discussion; the final analyzer recomputes the same statistics from those original labels.

Blinding now verifies original per-response provenance, request/response receipts and rendered-artifact hashes before export. Raw invalid actions, free text, extra JSON fields, provider/model identifiers and error text are omitted from the rater action file. Invalid commands retain their index and validity flag with a null action. Valid geometry/undo/stop remains available for redraw review. Complete raw responses stay in the private run directory. Inconsistent valid-action records fail closed.
