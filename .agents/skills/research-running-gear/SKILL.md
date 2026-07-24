---
name: research-running-gear
description: Research and compare current running products for the athlete's actual needs. Use for purchase recommendations, shortlists, or comparisons involving running shoes, watches, heart-rate straps, hydration vests or bottles, fueling products, apparel, lights, recovery tools, strength equipment, race gear, or product compatibility, pricing, availability, durability, and replacement decisions.
---

# Research Running Gear

## Goal

Produce a current, evidence-backed buying recommendation tied to the athlete's use case, constraints, and training plan without exposing private athlete data.

## Establish the Use Case

Read `docs/runner_profile.md` and `docs/marathon_plan.md` only when athlete-specific fit, current equipment, injury history, race needs, climate, or training volume matters.

When recent training volume, long-run distance, terrain, climate exposure, or activity history would materially affect the recommendation:

1. State the relevant date range.
2. Check `docs/garmindb/data/DBs/garmin_activities.db` and confirm coverage for that range before using its data. Use `.agents/skills/analyze-running-activity/scripts/list_recent_garmindb_runs.py` with `--start-date`, `--end-date`, and a sufficient `--limit` when running history is relevant.
3. Extract only the activity facts needed for the purchase decision. Do not expose routes or unrelated health data.
4. After the objective check, ask for missing qualitative information such as fit problems, discomfort, stability preference, sweat rate, carrying comfort, gastrointestinal tolerance, budget, or intended use. Label symptom questions with the applicable date or range and do not infer them from activity data.

Identify:

- intended use and required features;
- budget and location/market;
- sizing, fit, compatibility, and current equipment;
- training or race timeline;
- deal-breakers and acceptable tradeoffs.

Ask a concise question only when a missing answer would materially change the recommendation. Otherwise state reasonable assumptions.

## Research

Browse the web because products, prices, stock, specifications, and model generations change.

- Use manufacturer documentation for specifications, sizing, compatibility, warranty, and current models.
- Use reputable independent testing or reviews for ride, fit tendencies, durability, real-world usability, and limitations.
- Verify important claims across more than one source when practical.
- Separate measured facts, reviewer observations, user-specific inference, and unknowns.
- Compare current prices only when the user's market and date are clear.
- Generalize search terms; never include private health details, home routes, full identity, or private document text in external queries.

## Evaluate

Prioritize criteria relevant to the purchase rather than generic feature count.

For shoes, consider fit, intended pace and distance, surface, stability needs, geometry, cushioning, durability, rotation role, break-in timing, and return policy. Do not diagnose biomechanics or prescribe a medical device from symptoms alone.

For electronics, consider sensor quality, compatibility, battery life, data access, comfort, platform lock-in, and whether the added metric will change decisions.

For hydration and fueling gear, consider capacity, carry comfort, race rules, refill strategy, carbohydrate/sodium delivery, gastrointestinal tolerance, and practice time.

Account for the cost of an unnecessary or poorly timed purchase. Do not recommend premium equipment merely because it is newer.

## Response

Lead with the recommendation. Provide:

- a small ranked shortlist or a direct keep/replace decision;
- the best use case and important drawback for each option;
- athlete-specific reasoning without revealing unnecessary private details;
- current price/availability when requested;
- citations near claims;
- what should be tried, measured, or confirmed before purchase.

Do not buy, reserve, message sellers, or make other external changes unless the user explicitly requests and authorizes that action.

Do not update the private athlete record from a recommendation alone. Update equipment facts only after the user confirms a purchase, retirement, or actual use and asks for the record to change.
