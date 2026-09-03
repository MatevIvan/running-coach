# Runner Profile — Synthetic Example

> **Example data only.** Every athlete detail and training value in this file is fictional. This file documents the expected structure and must never be used for coaching decisions.

This demonstrates the compact current-context projection. Historical profile and activity evidence belongs in `docs/running_data.db`.

Last updated: 2027-04-05

Data sources: mock Strava export, three mock FIT activities, and synthetic recovery entries.

Active schedule: `running_plan_example.md` demonstrates the public format. A real local project uses the ignored private file `docs/running_plan.md`.

## Athlete Baseline

- Age: 36
- Sex: female
- Height: 5 ft 8 in
- Weight used for planning: about 150 lb
- Resting heart rate: 51 bpm, device estimate
- Max heart rate: 190 bpm, device estimate
- VO2 max: 47, device estimate
- Typical sleep: about 7 hr 30 min, recent sleep score about 78
- Preferred run days: Monday, Wednesday, Friday, and Saturday
- Heart-rate source: wrist optical sensor
- Current shoes: one daily trainer with about 180 known miles
- Injury history: no diagnosed injury; occasional mild calf tightness after hills
- Fueling status: water used on longer runs; carbohydrate practice has just started

## Goals and Event Context

- Primary development goal: become a stronger, more consistent all-around runner.
- Current block objective: make four-run weeks routine, build sustainable volume from 22-27 to 27-31 mi/week, and improve controlled-tempo durability.
- Success definition: complete at least six of the next eight weeks at the planned frequency, tolerate a 13-14 mi long run, and show stable or improved pace/HR on the standard aerobic benchmark.
- Next reassessment: 2027-05-31.
- Active race or event: none scheduled.
- Event priority: not applicable. Do not invent a race or force event-specific training.

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
- No validated threshold-pace estimate

Reliable enough for planning:

- FIT distance and duration
- Weekly mileage and run frequency
- Long-run history
- Average HR trends across repeated comparable routes

Do not overinterpret:

- Single max-HR spikes
- Device VO2 max as proof of performance
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

Comparable aerobic runs:

- 6.0 mi on 2027-03-10 at 10:22/mi, average HR 145
- 6.1 mi on 2027-03-24 at 10:16/mi, average HR 144
- 6.0 mi on 2027-04-02 at 10:14/mi, average HR 143

Long-run history:

- 12.6 mi on 2027-03-27 at 10:18/mi, average HR 149
- 11.0 mi on 2027-03-20 at 10:11/mi, average HR 147
- 9.0 mi on 2027-03-13 at 10:24/mi, average HR 145

## Estimates and Open Inputs

Estimates inferred from the mock data:

- Sustainable current volume is about 22-27 mi/week.
- Aerobic development is adequate for a modest volume progression.
- Endurance durability and controlled-tempo experience are improving but still limited.
- A progressive block can continue if calf symptoms remain mild and transient.

Unknowns that could materially change the plan:

- Whether calf tightness occurs outside hill sessions
- Response to two consecutive 28+ mi weeks
- Sweat rate and sodium needs
- Response to 30-45 g carbohydrate per hour on runs longer than 90 minutes
- Whether the athlete chooses an event during this block

## Runner Profile

Current volume and consistency:

- Four-run weeks are becoming routine.
- The recent recovery week was planned, not a loss of consistency.
- Mileage should build from the demonstrated 22-27 mi/week range, not from a hypothetical peak.

Aerobic base:

- Easy HR is stable on comparable routes.
- The athlete can run 10-12 miles without a major late-run pace collapse.
- Continued easy volume should remain the foundation of the block.

Speed and threshold capacity:

- Short controlled tempo work is tolerated.
- Speed is not the main limiter, but repeatable sub-threshold work is underdeveloped.

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

## Readiness

General training readiness:

- Ready for a progressive eight-week block.
- Not ready for simultaneous large increases in both volume and intensity.

Current-goal readiness:

- Close to making four-run weeks durable.
- Needs repeated 27-31 mi weeks before the higher volume is considered established.
- Needs three to five well-controlled tempo sessions before changing threshold estimates.

## Strengths, Limiters, and Risks

Biggest strengths:

- Improving consistency
- Controlled aerobic response on flat routes
- Sensible response to recovery weeks

Primary limiters:

- Limited history above 27 mi/week
- Early-run pacing is sometimes too aggressive
- Fueling practice is new

Main risks:

- Building mileage faster than connective-tissue durability
- Adding too many hills while calf tightness remains active
- Treating device fitness estimates as proof
- Letting the absence of a race turn the plan into maintenance without progression

## Training Zones and Pacing

These mock ranges are conservative estimates, not universal recommendations:

| Session | HR / Effort | Pace Guidance |
|---|---|---|
| Recovery | Conversational, RPE 2-3 | Usually slower than 10:40/mi |
| Easy | Mostly 135-150 bpm, RPE 3-4 | Often 10:00-11:10/mi |
| Long | Mostly 138-153 bpm, RPE 3-5 | Effort first; walk steep hills if needed |
| Tempo | Controlled hard, RPE 6-7 | Set from repeated workout evidence, not VO2 max |

Metrics to watch: frequency, weekly volume, breathing, average HR, late-run drift, pain, and next-day recovery.

Metrics to mostly ignore: isolated max-HR spikes, instantaneous pace, and a single device prediction.

## Active Running Plan

The real private project points to `docs/running_plan.md`. The public synthetic companion is `running_plan_example.md`.

## Future Chats Should Know

- This entire file is synthetic and must not be used as real athlete input.
- The mock athlete is consistently running about 22-27 mi/week with a 12.6-mile long-run ceiling.
- The active objective is a progressive eight-week development block; no event is scheduled.
- Frequency, modest volume growth, and controlled-tempo durability are the current priorities.
- Easy work is effort-led, typically 135-150 bpm in the mock dataset.
- Monitor hill-related calf tightness and early-run pacing.
- Use the active private plan in `docs/running_plan.md` for a real athlete.
