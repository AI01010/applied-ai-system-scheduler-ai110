---
topic: conflict
pet_type: dog
energy: high
age: any
---

# Conflict: Owner Busy During Prime Walk Time

A high-energy dog ideally gets a long walk between 17:00 and 18:30 — peak energy release before evening settle. But many owners cannot leave a 17:00 meeting or 18:00 commute.

## Resolution heuristics, in order of preference

1. **Earlier morning extension.** Push the morning walk from 30 min to 60 min. Roughly 60% of the lost evening exercise can be made up by extending the morning walk, since exercise effects compound through the day.

2. **Midday dog walker.** A 30-minute midday walk takes most of the pressure off the evening. Even 2–3 days/week of a midday walker dramatically improves evening behavior.

3. **Post-busy-window walk.** If the owner is free by 19:00, walking then is fine — but it must end before 19:30. Late vigorous exercise spikes cortisol and disrupts bedtime settling.

4. **Mental fatigue substitute.** A 15-minute training session, snuffle mat, or food puzzle is roughly equivalent to a 30-minute walk in terms of mental tiredness. Mental enrichment cannot fully replace physical exercise but it bridges short gaps.

## What does not work

- **Skipping the walk entirely.** Under-exercised high-energy dogs become destructive, anxious, or hyper-vigilant. Damage to property is the visible cost; chronic stress is the invisible one.
- **Two short walks crammed back-to-back at 19:00 and 19:45.** This pushes the wind-down window too late.
- **Off-leash backyard "exercise".** Most dogs do not self-exercise. They wait for the owner to come outside, then the play is brief.

## How PawPal+ handles this conflict

The constraint engine flags the 17:30 walk as overlapping the busy window 17:00–19:00 and auto-shifts it forward in 15-min increments until it fits. The default first valid slot is 19:00 with a 30 min walk ending at 19:30 — the latest acceptable slot per heuristic #3.

If no valid window is found before 21:00, the system surfaces a warning suggesting heuristics #1 or #2 instead.
