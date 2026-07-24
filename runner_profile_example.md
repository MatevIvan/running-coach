# Runner Profile — Synthetic Example

> **Example data only.** Every athlete detail and training value in this file is fictional. This file documents the expected structure and must never be used for coaching decisions.

Last updated: 2027-04-05

Data sources: mock Strava export, three mock FIT activities, and synthetic recovery entries.

Active schedule: `marathon_plan_example.md` demonstrates the public format. A real local project uses the ignored private file `docs/marathon_plan.md`.

## Athlete Baseline

- Age: 36
- Sex: female
- Height: 5 ft 8 in
- Weight used for planning: about 150 lb
- Resting heart rate: 51 bpm, device estimate
- Max heart rate: 190 bpm, device estimate
- VO2 max: 47, device estimate
- Typical sleep: about 7 hr 30 min, recent sleep score about 78
- Target race: first marathon on 2027-10-03
- Goal hierarchy: finish healthy first; performance target remains open
- Preferred run days: Monday, Wednesday, Friday, and Saturday
- Heart-rate source: wrist optical sensor
- Current shoes: one daily trainer with about 180 known miles
- Injury history: no diagnosed injury; occasional mild calf tightness after hills
- Fueling status: water used on long runs; carbohydrate practice has just started

## Data Processed

Facts directly supported by the mock dataset:

- 38 running activities cover 2027-01-04 through 2027-04-04.
- FIT parsing succeeded for 35 activities; three GPX files lack HR and cadence.
- Total mock running volume is 211.4 miles.
- The longest run is 12.6 miles.
- Recent training has been more consistent than the January baseline.

Missing or limited data:

- No recent race or formal threshold test
- No chest-strap HR data
- Incomplete weather and terrain metadata
- Only three weeks of recovery metrics
- No validated marathon-pace estimate

Reliable enough for planning:

- FIT distance and duration
- Weekly mileage and run frequency
- Long-run history
- Average HR trends across repeated comparable routes

Do not overinterpret:

- Single max-HR spikes
- Device VO2 max as marathon readiness
- Wrist-HR zone percentages from one run
- Pace from hot, hilly, or trail sessions

## Facts Supported by Running Data

Known mock running by month:

| Month | Runs | Miles | Longest Run |
|---|---:|---:|---:|
| 2027-01 | 9 | 42.0 | 6.2 mi |
| 2027-02 | 12 | 63.8 | 8.0 mi |
| 2027-03 | 14 | 87.0 | 12.6 mi |
| 2027-04 through 2027-04-04 | 3 | 18.6 | 8.1 mi |

Recent completed weeks:

| Week Starting | Runs | Miles | Long Run | Avg HR | Notes |
|---|---:|---:|---:|---:|---|
| 2027-03-08 | 4 | 22.4 | 9.0 | 145 | Consistent easy volume |
| 2027-03-15 | 4 | 25.1 | 11.0 | 147 | First fueling practice |
| 2027-03-22 | 4 | 26.3 | 12.6 | 148 | Highest durable week so far |
| 2027-03-29 | 3 | 18.6 | 8.1 | 143 | Planned recovery week |

Long-run history:

- 12.6 mi on 2027-03-27 at 10:18/mi, average HR 149
- 11.0 mi on 2027-03-20 at 10:11/mi, average HR 147
- 9.0 mi on 2027-03-13 at 10:24/mi, average HR 145

Pace and heart-rate patterns:

- Easy runs usually fall between 10:00 and 11:10/mi at 135-150 bpm.
- On cool, flat routes, pace is stable with less than 5% first-half/second-half drift.
- Hill sessions raise average HR substantially, so pace comparisons across terrain are not valid.
- Two recent easy runs started too quickly and required a deliberate slowdown after mile 2.

Cadence and terrain notes:

- Recorded cadence is usually 166-174 spm on easy paved runs.
- No cadence target is prescribed; relaxed form and effort control take priority.
- Most volume is on paved rolling routes. Trail runs are treated as effort-based sessions.

## Estimates and Open Inputs

Estimates inferred from the mock data:

- Sustainable current volume is about 22-27 mi/week.
- Aerobic development is adequate for the current phase.
- Endurance durability is improving but not yet marathon-specific.
- A conservative build can continue if calf symptoms remain mild and transient.

Unknowns that could materially change the plan:

- A recent race result or threshold field test
- Whether calf tightness occurs outside hill sessions
- Exact race course and elevation profile
- Sweat rate and sodium needs
- Response to 30-45 g carbohydrate per hour on longer runs

## Runner Profile

Current volume and consistency:

- Four-run weeks are becoming routine.
- The recent recovery week was planned, not a loss of consistency.
- Mileage should build from the current 22-27 mi/week range, not from a hypothetical peak.

Aerobic base:

- Easy HR is generally stable on comparable routes.
- The athlete can run 10-12 miles without a major late-run pace collapse.
- More months of steady volume are needed before marathon-specific conclusions are justified.

Speed capacity:

- Short controlled tempo work is tolerated.
- Speed is not the current limiter and does not justify aggressive interval volume.

Endurance durability:

- Improving, but only three runs have exceeded 9 miles.
- Long-run progression should remain gradual and include recovery weeks.

Pacing discipline:

- Generally acceptable, with a recurring tendency to make the first two miles too fast.
- Easy days should begin at the slow end of the range and tighten only if HR and breathing remain controlled.

Recovery capacity:

- Recent sleep and resting HR are stable.
- One low-readiness day after the 12.6-mile run resolved with a rest day.
- Calf symptoms need trend monitoring before adding hill volume.

Marathon-specific readiness:

- Not currently ready to race 26.2 miles.
- The October race timeline is reasonable if consistency continues and long-run durability grows.
- No marathon-time prediction is defensible yet.

Biggest strengths:

- Improving consistency
- Controlled aerobic response on flat routes
- Sensible recovery-week response

Biggest weaknesses:

- Limited long-run history
- Early-run pacing is sometimes too aggressive
- Fueling practice is new

Main risks:

- Building mileage faster than connective-tissue durability
- Adding too many hills while calf tightness remains active
- Treating device fitness estimates as race proof
- Delaying fueling practice until peak long runs

## Training Zones and Pacing

These mock ranges are conservative estimates, not universal recommendations:

| Session | HR / Effort | Pace Guidance |
|---|---|---|
| Recovery | Conversational, RPE 2-3 | Usually slower than 10:40/mi |
| Easy | Mostly 135-150 bpm, RPE 3-4 | Often 10:00-11:10/mi |
| Long | Mostly 138-153 bpm, RPE 3-5 | Effort first; walk steep hills if needed |
| Tempo | Controlled hard, RPE 6-7 | Set from current workout evidence, not VO2 max |

Metrics to watch: breathing, average HR, late-run drift, pain, and next-day recovery.

Metrics to mostly ignore: isolated max-HR spikes, instantaneous pace, and a single device race prediction.

## Active Marathon Plan

The real private project points to `docs/marathon_plan.md`. The public mock companion is `marathon_plan_example.md`.

## Future Chats Should Know

- This entire file is synthetic and must not be used as real athlete input.
- The mock athlete is consistently running about 22-27 mi/week with a 12.6-mile long-run ceiling.
- Durability and fueling practice are the current limiters; speed is not.
- Easy work is effort-led, typically 135-150 bpm in the mock dataset.
- Monitor hill-related calf tightness and early-run pacing.
- Use the active private plan in `docs/marathon_plan.md` for a real athlete.
