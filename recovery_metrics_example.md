# Recovery Metrics — Synthetic Example

> **Example data only.** All values and notes are fictional. Never use this file for real training decisions.

Last updated: 2027-04-05

Purpose: demonstrate the compact rolling view. A real local project uses `docs/recovery_metrics.md` as a current projection and `docs/running_data.db` as the permanent source of truth.

## Use Rules

- Keep this as a rolling log, not a full-history archive.
- Use the most recent 7 valid daily entries for run decisions.
- Keep at most the most recent 14 daily entries.
- Update the private SQLite record first, then regenerate the private rolling Markdown view.
- Look for clusters across sleep, resting HR, HRV, readiness, symptoms, and run response.
- These metrics guide adjustment; they do not diagnose medical conditions.

## What to Provide

Preferred compact format:

```text
Date:
Sleep duration:
Sleep score:
Resting HR:
HRV status/value:
Training readiness:
Body Battery / stress:
Soreness or pain:
Notes:
```

## Rolling Daily Log

| Date | Sleep | Sleep Score | Resting HR | HRV | Training Readiness | Body Battery / Stress | Soreness or Pain | Notes |
|---|---:|---:|---:|---|---:|---|---|---|
| 2027-04-05 | 7h 42min | 82 | 50 | 61 ms, balanced | 76, high | High 91 / low 28; low-stress prior day | None | Green-light example: normal recovery cluster supports the planned easy run. |
| 2027-04-04 | 7h 06min | 74 | 52 | 58 ms, balanced | 62, moderate | High 84 / low 21; moderate stress | Mild general leg fatigue | Yellow-light example after an 8.1 mi run: rest day remains appropriate. |
| 2027-04-03 | 6h 18min | 63 | 54 | 55 ms, unbalanced | 48, low | High 70 / low 16; stressful day | Mild calf tightness, 1/10 | Orange-light example: multiple negative signals remove intensity; use rest or short easy movement. |

## Interpretation Rules

- Green: metrics are near baseline, no meaningful soreness, and easy-run response is normal.
- Yellow: one poor signal or mild soreness. Keep training easy unless the warmup is clearly normal.
- Orange: multiple poor signals, recurring symptoms, or unusually high easy effort. Remove quality and reduce load.
- Red: pain changes stride, worsens, or appears localized to bone/tendon. Stop and consider clinical assessment if concerning.
