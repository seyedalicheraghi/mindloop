---
title: "How NAVSIM Evaluates Autonomous Driving Planners"
date: 2026-06-28
summary: "A deep dive into NAVSIM's pseudo-simulation approach to benchmarking AV planners — covering open-loop vs. closed-loop evaluation, the PDMS/EPDMS scoring structure, and why the framework doesn't transfer cleanly to off-road autonomy."
---

More and more companies are entering the autonomy field by bringing AI into their products. Waymo already operates a large commercial robotaxi service in San Francisco, and Amazon-owned Zoox has begun offering free public rides in parts of the city as it works toward a paid service. This momentum is pulling more companies into the space, including startups like Pronto, which applies autonomy not to city streets but to off-road environments such as mines and quarries, retrofitting haul trucks to operate where there are no lanes, traffic lights, or HD maps.

Training the models behind these vehicles requires enormous amounts of data, both real and synthetic. But assuming you have the data and can train a model to automate the driving task, you still face a harder question: how do you evaluate it? A model is only as trustworthy as the testing behind it, and there are two main paradigms for testing a planner.

## Open-loop vs. closed-loop

Open-loop evaluation treats the recorded human trajectory as ground truth and scores any deviation from it as error. The problem is that driving has many safe answers, not one. On a straight road, a path slightly left or right of the human's line is still perfectly safe, yet open-loop punishes it. In effect, open-loop asks the model to imitate the human exactly, when what we actually want is for it to complete the task safely and efficiently.

Closed-loop evaluation is more realistic. Sensor inputs are fed to the planner, the planner's output is executed, the simulated world steps forward, and the resulting new observation is fed back to the planner, in a feedback loop. This captures how small errors compound over time and how the scene reacts to the vehicle's choices, which is exactly what open-loop misses. The catch is cost: running the planner over and over at high frequency, with realistic simulation at each step, is computationally expensive.

## NAVSIM's middle ground

NAVSIM proposes a compromise it calls **pseudo-simulation**. Camera frames and LiDAR together with the ego status (current velocity, acceleration, and a navigation command of left/straight/right) are fed into the planner. The planner outputs a trajectory: a sequence of future waypoints. That single trajectory is then committed and unrolled for a short horizon (4 seconds) using an **LQR controller** and a **kinematic bicycle model** — a standard trajectory-tracking controller paired with a simplified steering model — which together turn the waypoints into the vehicle's actual motion.

Crucially, the planner is queried only once and receives no feedback during the unroll. NAVSIM works from a static recording, so the frames after the initial timestep are never an input to the planner. They serve a different role, as the answer key the executed trajectory is scored against. This non-reactive trick is what lets NAVSIM compute simulation-based safety metrics at a fraction of closed-loop's cost. The navigation command (left/straight/right) exists precisely to disambiguate cases like intersections, where several routes are safe and open-loop's "imitate the human" assumption would otherwise break down.

## Where the data comes from

NAVSIM is not a simulator that renders scenes from scratch; it is built on real-world driving logs. The framework is dataset-agnostic in principle, but in practice it uses **OpenScene**, a redistribution of **nuPlan** — the largest annotated public driving dataset. OpenScene condenses nuPlan from 10 Hz down to 2 Hz, cutting storage from over 20 TB to about 2 TB while keeping 120 hours of driving.

## Filtering for the scenes that matter

A central design choice is that NAVSIM does not evaluate on every frame. Most human driving is trivial: sitting stationary or cruising straight at near-constant speed. A dumb baseline that simply maintains constant velocity and heading already scores about 79% on raw OpenScene, against roughly 91% for human-level driving, which means easy scenes barely separate good planners from bad ones.

So NAVSIM resamples the data to emphasize challenging segments (turns, intent changes, interactions) and filters out the trivial portions where holding speed and heading would suffice. The curated result is delivered as standardized splits: **navtrain** for training and validation and **navtest** for testing (commonly cited as 1,192 and 136 filtered scenarios, drawn from roughly 103k and 12k underlying samples). v2 adds **navhard**, a deliberately difficult split built around situations like unprotected turns. This filtering is what makes simply fitting the ego status insufficient and forces planners to actually reason about the scene.

## NAVSIM v2: pseudo-closed-loop mechanics

Here is how v2 works step by step. For each scene, past frames, LiDAR, and ego status are passed into the planner. The planner is queried only at the initial frame and generates a trajectory for the next 4 seconds; during this horizon it receives no new data, and the trajectory is held fixed. The ego's motion is rolled out with the kinematic bicycle model and LQR controller.

The pseudo-closed-loop behavior comes from a two-stage aggregation. A first-stage score is computed on the initial 4-second scene. Then a set of follow-up scenes — precomputed rollouts that begin from the same initial scene but end in different states — are also scored. These follow-up states are generated independently of the planner, to probe a neighborhood of plausible futures around where the planner ended up. The follow-up scores are aggregated with weights from a **Gaussian kernel** based on how close each follow-up's start state is to the planner's first-stage end state, and the first-stage and aggregated second-stage scores are multiplied to give the final **EPDMS**.

This is where **3D Gaussian Splatting** earns its place. The follow-up scenes start from perturbed ego positions that were never in the original recording, so there is no logged sensor data for them. 3DGS reconstructs the scene and renders realistic camera and LiDAR observations from these novel viewpoints — which is what makes scoring the perturbed futures possible at all. It is the enabling technology for stage two, not a cosmetic detail.

## How the score is built

Scores come from a set of criteria: No at-fault Collision (NC), Drivable Area Compliance (DAC), Driving Direction Compliance (DDC), Traffic Light Compliance (TLC), Ego Progress (EP), Time to Collision (TTC), Lane Keeping (LK), History Comfort (HC), and Extended Comfort (EC). v1's **PDMS** uses the first cluster (NC, DAC, TTC, EP, comfort); v2's **EPDMS** extends it with DDC, TLC, LK, and the comfort terms.

The structure of the combination matters more than the list. The safety-critical terms act as **multiplicative penalties**: a collision or leaving the drivable area multiplies the score toward zero, so one serious violation tanks the whole result no matter how good everything else was. The remaining quality terms (progress, time-to-collision, and comfort) enter as a weighted average. The intuition is that you cannot "average away" a crash, but you can trade off smoothness against progress. EPDMS keeps this multiplicative-times-weighted shape while adding its new sub-scores. One practical wrinkle: Lane Keeping is disabled at intersections, where centerline annotations often do not match the lane markings the sensors actually perceive.

## A note on reactivity

Even though the ego cannot react or change course during the 4-second unroll, background agents can. On navhard (the v2 pseudo-simulation protocol), pedestrians and other vehicles are allowed to stop or change path to avoid an accident the ego would otherwise cause. On the standard navtest benchmark, the environment stays non-reactive: other agents follow their recorded futures regardless of what the ego does. So reactive agents are a property of the reactive benchmark, not of NAVSIM v2 across the board — a distinction worth keeping straight when comparing reported scores.

## NAVSIM in off-road contexts

NAVSIM is a strong evaluation framework for on-road AVs, but its assumptions do not transfer cleanly to off-road autonomy — and the gap is structural, not cosmetic. The issue is not simply that off-road scenes lack lanes; it is that two of NAVSIM's core components, the motion rollout and the scoring metrics, both encode an on-road world.

**Flat-ground motion model.** NAVSIM unrolls a planned trajectory using a kinematic bicycle model on a 2D ground plane. Off-road, vehicle motion is dominated by wheel slip, sinkage, and pitch and roll on uneven or deformable terrain. A trajectory that the bicycle model would execute perfectly on asphalt will not be realized as planned on a loose grade or in mud. So even before scoring, NAVSIM's executor is wrong for off-road surfaces, because it cannot represent how terrain and road material affect how the vehicle actually moves.

**Map-relative metrics.** Most of NAVSIM's sub-scores are defined against HD-map primitives — Drivable Area Compliance, Driving Direction Compliance, Lane Keeping, and Traffic Light Compliance all assume annotated drivable polygons, centerlines, lane directions, and signals. Off-road there are no lanes, intersections, or stop signs, and "drivable area" is not a labeled polygon but a continuous, terrain-dependent notion of traversability. These metrics therefore don't just need relabeling; several have no off-road definition at all. A meaningful off-road benchmark would need new metrics entirely: traversability compliance, slope and rollover stability margins, and ground-pressure or sinkage limits.

**Reconstruction breaks down.** NAVSIM v2's pseudo-closed-loop stage relies on 3D Gaussian Splatting to render realistic sensor data from perturbed viewpoints. 3DGS is at its weakest exactly in off-road conditions — vegetation, dust, low-texture ground, and deformable surfaces are hard to reconstruct, so the synthetic-future machinery that makes v2 work is itself unreliable off-road.

**Data and curation.** Adapting NAVSIM would require collecting and labeling off-road sensor logs, which is costly on its own. But the harder problem is that NAVSIM's scene-filtering logic — which keeps "challenging" scenes by detecting where constant velocity and heading fail — is itself on-road-specific. Off-road difficulty is defined by terrain, which that filter cannot see, so the curation step would have to be rebuilt too.

Taken together, the data pipeline, the motion model, the metrics, and the reconstruction step would each need near-complete replacement rather than reconfiguration. NAVSIM is a useful conceptual blueprint for off-road evaluation (one-shot planning, physics-based rollout, simulation-based scoring) but in practice an off-road benchmark would reuse the philosophy, not the components.
