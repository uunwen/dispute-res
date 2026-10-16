# Evaluation report

- dataset: synthetic variants of organizer samples
- concurrency: 3 (LLM_MOCK=False)
- models: advocate=`gemini-3.5-flash-lite` · judge=`gemini-3.5-flash-lite` · tools=`gemini-3.5-flash-lite`
- embedding: fastembed/BAAI/bge-small-en-v1.5 (dim 384)

## Summary

- disputes resolved: **23**
- degraded (excluded from metrics): **3**
  - VAR-R02, VAR-N03, VAR-N06
- non-degraded: **20**

## Metrics

| metric | value |
|---|---|
| outcome accuracy | 20/20 (100.0%) |
| refund error (mean |actual − expected|) | 0.000 (n=20, max 0.000) |
| escalation precision | 8/12 (66.7%) |
| escalation recall | 8/8 (100.0%) |
| mean time per dispute | 47.42s (n=23, median 51.92s, max 85.51s) |

## Per-section accuracy

| section | correct | total | accuracy |
|---|---|---|---|
| 1 | 8 | 8 | 100.0% |
| 2 | 5 | 5 | 100.0% |
| 3 | 7 | 7 | 100.0% |

## Per-dispute

| id | sec | expected | actual | escal (exp→act) | degraded | seconds |
|---|---|---|---|---|---|---|
| DISP-001 | 1 | partial_refund / 3.44 | partial_refund / 3.44 | Y→Y | N | 12.091 |
| DISP-002 | 2 | no_refund / 0.00 | no_refund / 0.00 | Y→Y | N | 12.025 |
| DISP-003 | 3 | full_refund / 4.50 | full_refund / 4.50 | N→N | N | 11.811 |
| VAR-R01 | 1 | no_refund / 0.00 | no_refund / 0.00 | N→N | N | 11.293 |
| VAR-R02 | 1 | full_refund / 1.20 | full_refund / 1.20 | N→Y | Y | 84.834 |
| VAR-R03 | 1 | partial_refund / 1.20 | partial_refund / 1.20 | N→Y | N | 11.287 |
| VAR-R04 | 1 | no_refund / 0.00 | no_refund / 0.00 | N→N | N | 68.796 |
| VAR-R05 | 1 | partial_refund / 2.00 | partial_refund / 2.00 | Y→Y | N | 70.853 |
| VAR-R06 | 1 | full_refund / 1.20 | full_refund / 1.20 | Y→Y | N | 47.841 |
| VAR-R07 | 1 | partial_refund / 1.20 | partial_refund / 1.20 | Y→Y | N | 48.815 |
| VAR-R08 | 1 | full_refund / 1.20 | full_refund / 1.20 | N→Y | N | 46.126 |
| VAR-N01 | 2 | no_refund / 0.00 | no_refund / 0.00 | N→N | N | 62.789 |
| VAR-N02 | 2 | full_refund / 5.00 | full_refund / 5.00 | N→N | N | 53.538 |
| VAR-N03 | 2 | full_refund / 5.00 | full_refund / 5.00 | N→N | Y | 83.677 |
| VAR-N04 | 2 | full_refund / 5.00 | full_refund / 5.00 | N→N | N | 9.225 |
| VAR-N05 | 2 | no_refund / 0.00 | no_refund / 0.00 | Y→Y | N | 62.232 |
| VAR-N06 | 2 | full_refund / 5.00 | full_refund / 5.00 | Y→Y | Y | 85.51 |
| VAR-S01 | 3 | full_refund / 4.50 | full_refund / 4.50 | N→N | N | 34.213 |
| VAR-S02 | 3 | no_refund / 0.00 | no_refund / 0.00 | N→N | N | 62.109 |
| VAR-S03 | 3 | full_refund / 4.50 | full_refund / 4.50 | Y→Y | N | 51.916 |
| VAR-S04 | 3 | full_refund / 48.00 | full_refund / 48.00 | Y→Y | N | 30.232 |
| VAR-S05 | 3 | no_refund / 0.00 | no_refund / 0.00 | N→Y | N | 65.527 |
| VAR-S06 | 3 | full_refund / 0.50 | full_refund / 0.50 | N→Y | N | 64.009 |
