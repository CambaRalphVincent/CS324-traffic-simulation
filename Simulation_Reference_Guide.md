# Traffic Light System Simulation — Reference Guide

**Course:** CS 324 Modeling and Simulation
**Project Title:** Simulation of Traffic Light System
**Institution:** Batangas State University – Alangilan Campus, CICS
**Academic Year:** 2nd Semester, AY 2025–2026

---

## 1. Overview

This simulation models a four-way intersection controlled by traffic lights. Vehicles arrive from the North, South, East, and West approaches, queue behind the stop line, and cross the intersection when the signal turns green. The simulation is built using **SimPy** (discrete-event simulation engine) and **Pygame** (real-time visualization).

The goal is to measure how different traffic light control strategies affect driver wait times, queue buildup, and overall intersection throughput across three traffic scenarios.

The model also includes **pedestrians** crossing at the four crosswalks and **turning vehicles** (cars may go straight, turn left, or turn right). Vehicles are rendered with realistic motion — smooth acceleration and braking, brake lights, gradual turning, and slight per-driver speed variation — so the visualization reflects natural traffic flow. This motion realism is purely visual; the wait-time and throughput statistics are driven by the underlying SimPy discrete-event model, not the animation.

---

## 2. Statistics Explained

All statistics are displayed in the right-side panel during the simulation and in the Results & Analysis screen.

---

### 2.1 Completed

**What it is:** The total number of vehicles that have successfully crossed the intersection since the simulation started.

**How it is calculated:** A vehicle is counted as "completed" the moment it finishes crossing the intersection box. Vehicles still waiting in queue, currently crossing, or in the exit animation are **not** counted.

**What it tells you:** This is a raw running total — it only ever increases. It is the foundation for calculating Throughput.

**Example:** Completed = 40 means 40 cars have passed through the intersection so far.

---

### 2.2 In Queue

**What it is:** The total number of vehicles currently waiting across all four approaches (North, South, East, West) at this exact moment.

**How it is calculated:** The sum of all vehicles in all four queues at the time of sampling.

**What it tells you:** A real-time snapshot of congestion. If In Queue is growing over time while Avg Wait looks low, it means new congestion is building up that has not yet been reflected in completed-vehicle averages.

**Color coding in the panel:**
- White — 0 to 3 vehicles (normal)
- Yellow — 4 to 8 vehicles (moderate congestion)
- Red — 9 or more vehicles (heavy congestion)

**Example:** In Queue = 18 during Rush Hour means 18 cars are currently waiting across all approaches.

---

### 2.3 Throughput

**What it is:** The rate at which vehicles are passing through the intersection, expressed in **vehicles per minute**.

**How it is calculated:** Uses a **rolling 60-second window** — it counts only vehicles that completed their crossing within the last 60 simulation seconds, then scales to a per-minute rate.

> Throughput = (vehicles completed in last 60 sim-seconds) ÷ 60 × 60

**What it tells you:** How efficiently the intersection is moving traffic *right now*. Because it uses a rolling window rather than a lifetime average, it responds quickly to changes — if traffic suddenly worsens, Throughput will drop in real time.

**Higher is better.**

**Example:** Throughput = 38.0/min means approximately 38 cars are passing through the intersection every minute.

---

### 2.4 Avg Wait (Average Wait Time)

**What it is:** The average number of seconds a vehicle spends sitting in the queue before the light turns green and it gets to cross.

**How it is calculated:** For each completed vehicle:

> Wait Time = Start Cross Time − Arrival Time

Avg Wait is the mean of all individual wait times across every completed vehicle.

**What it tells you:** The typical driver experience at this intersection. A low Avg Wait means cars are not being held at the light for long.

**Lower is better.**

**Important limitation:** Only completed vehicles are counted. Vehicles still stuck in a long queue are not yet reflected. Always check In Queue alongside Avg Wait to get the full picture.

**Example:** Avg Wait = 11.06s means on average, each car waited about 11 seconds in the queue before crossing.

---

### 2.5 Max Wait (Maximum Wait Time)

**What it is:** The single longest wait time experienced by any one vehicle since the simulation started.

**How it is calculated:** The maximum value among all individual wait times from completed vehicles.

**What it tells you:** The worst-case scenario — how bad it gets for the unluckiest driver. While Avg Wait describes the typical experience, Max Wait exposes congestion spikes and fairness issues.

A **low Avg Wait with a very high Max Wait** is a warning sign: most cars move quickly, but some vehicles are getting trapped — commonly seen in Rush Hour when a queue builds faster than the green phase can drain it.

**Lower is better.**

**Example:** Max Wait = 27.20s means at least one car had to wait over 27 seconds before it could cross.

---

### 2.6 Efficiency

**What it is:** A single score that measures how well the intersection balances two competing goals — moving many vehicles (high throughput) while keeping wait times short (low avg wait). It rewards doing both at the same time and penalizes doing one at the expense of the other.

**How it is calculated:**

> Efficiency = Rolling Throughput ÷ Avg Wait

**Why this formula works:** Throughput alone does not tell the full story — an intersection could push many cars through by giving very long green phases, but that forces the opposing direction to wait a long time. Dividing throughput by avg wait means the score only stays high when cars are moving *and* not being made to wait. If wait times rise, the score drops even if throughput stays the same.

**A simple analogy:** Think of a tollbooth. One booth processes 40 cars per minute but each driver waits 20 seconds — Efficiency = 40 ÷ 20 = **2.0**. Another booth processes 38 cars per minute but drivers only wait 8 seconds — Efficiency = 38 ÷ 8 = **4.75**. The second booth is more efficient even though it processes slightly fewer cars, because it achieves a better balance.

**What it tells you:** The mode or scenario with the higher Efficiency score is making better use of the available green time. It is the most useful stat for directly comparing **Fixed vs. Adaptive** control, because it captures the trade-off in a single number instead of requiring you to weigh throughput and wait time separately.

**Higher is better.**

**Example:** Efficiency = 3.44 means for every second a driver waits, the intersection is serving 3.44 cars per minute. An Efficiency of 5.0 on the same scenario would mean the intersection is serving more cars with shorter waits — a clear improvement.

---

### 2.7 Pedestrians (Waiting & Crossing)

**What it is:** The **PEDESTRIANS** section of the panel shows two live counts — how many pedestrians are currently *waiting* at a crosswalk for a safe signal, and how many are currently *crossing*.

**How it is calculated:**
- **Waiting** — pedestrians who have arrived at a crosswalk but cannot cross yet because vehicles facing that crosswalk still have a green or yellow light.
- **Crossing** — pedestrians who are currently walking across the intersection (each crossing takes 4 simulation seconds).

**When pedestrians may cross:** A pedestrian only steps off when the vehicles that would hit their crosswalk are stopped. Pedestrians at the **North/South crosswalks** cross while the East–West direction has the green (i.e. during EW green, yellow, or the all-red buffer), and vice versa. This mirrors how real signalized intersections give pedestrians a walk interval against stopped traffic.

**Color coding in the panel:**
- Waiting — white normally, **red** when more than 4 pedestrians are backed up at the crosswalks
- Crossing — **green** while at least one pedestrian is in the intersection, white when none

**What it tells you:** A persistently high Waiting count indicates the signal cycle is leaving pedestrians stranded — a fairness signal that complements the vehicle-side queue stats.

---

## 3. Queue Statistics (Per Direction)

The **Queues** section of the panel shows the current number of vehicles waiting at each of the four approaches individually.

| Direction | Description |
|-----------|-------------|
| N | North approach — vehicles traveling southward |
| S | South approach — vehicles traveling northward |
| E | East approach — vehicles traveling westward |
| W | West approach — vehicles traveling eastward |

**Color coding:**
- Green — 0 to 2 vehicles
- Yellow — 3 to 5 vehicles
- Red — 6 or more vehicles

These values directly feed into the **Queue Length Over Time** chart in the Analysis screen.

---

## 4. Control Modes

### 4.1 Fixed Control

The traffic light follows a rigid, pre-set cycle regardless of traffic conditions:

- **Green phase:** exactly 20 seconds
- **Yellow phase:** 3 seconds
- **All-red buffer:** 1 second (safety gap before opposing traffic moves)

The cycle repeats: NS Green → NS Yellow → All Red → EW Green → EW Yellow → All Red → repeat.

**Best for:** Predictable, consistent behavior. Easy to understand and analyze.

---

### 4.2 Adaptive Control

The traffic light starts with a shorter green phase (8 seconds minimum) and extends it in 2-second increments — up to a maximum of 40 seconds — based on real-time queue conditions.

**Extension conditions (green is held longer if):**
1. The active direction's queue still has more than 2 vehicles waiting, AND
2. The opposing direction's queue is not more than twice as large (prevents starving the other side)

**Effect in practice:**
- **Low Traffic:** Green phases are cut short (8s instead of 20s), cycling faster through directions.
- **Rush Hour:** Green is extended up to 40s to drain large queues before switching.

**Best for:** Dynamic traffic conditions where Fixed timing would either waste green time (low traffic) or fail to clear heavy queues (rush hour).

---

## 5. Traffic Scenarios

| Scenario | Arrival Rate (vehicles/sec per approach) | Description |
|----------|------------------------------------------|-------------|
| Low Traffic | 0.10 (all directions) | Light traffic — queues rarely build up |
| Normal Traffic | 0.25 (N/S), 0.20 (E/W) | Moderate traffic with occasional queuing |
| Rush Hour | 0.50 (N), 0.45 (S), 0.35 (E/W) | Heavy traffic — queues build quickly, congestion likely |

Arrival times follow an **exponential distribution** (Poisson process), which reflects the random, memoryless nature of real vehicle arrivals.

Pedestrians arrive independently at each of the four crosswalks, also as a Poisson process (a low arrival rate of roughly one pedestrian every ~17 seconds per crosswalk), so foot traffic stays light relative to vehicle traffic.

---

## 6. Vehicle & Pedestrian Behavior

### 6.1 Turning Movements

Every vehicle is randomly assigned a movement when it spawns:

| Movement | Probability |
|----------|-------------|
| Straight (through) | 50% |
| Left turn | 25% |
| Right turn | 25% |

The chosen movement determines which exit road the car takes after clearing the intersection. Turning is shown visually as the car gradually rotates onto its new heading rather than snapping instantly.

### 6.2 Permissive Left Turns

The signal runs as a standard real-world **two-phase** controller: North and South go green together, then East and West go green together. Opposing *through* movements share a green because they do not conflict — this pairing is exactly how the majority of real signalised intersections operate, and the Adaptive mode simply lengthens or shortens these same two phases based on demand.

Left turns are modelled as **permissive** (a green *ball*, not a protected green *arrow*) — the same as a typical unprotected left in real life. A left-turning car:

1. Enters the intersection on its green and pulls forward to the **centre**.
2. **Holds at the centre** and yields until there is a safe gap.
3. Completes the turn once clear — frequently finishing during the **yellow / all-red clearance** after oncoming traffic has stopped, just as real drivers do.

A waiting left-turner yields to:

| Conflict | Rule |
|----------|------|
| **Oncoming through traffic** (opposite approach going straight) | Wait until it has cleared the centre |
| **The opposing left turn** | Strict first-come order — whichever entered the intersection first goes first (so two opposing lefts can never deadlock) |
| **Any opposing car merging into the same exit lane** | e.g. a South-left and a North-right both feed the **westbound** lane — the car behind follows rather than overlapping |

Through and right-turning cars are **never** blocked by a left-turner — consistent with reality, the permissive left yields, not the other way around. The right-of-way ordering is strict, so conflict resolution is **deadlock-free**: every conflict always clears.

> **Effect on statistics:** The centre-hold delays a left-turner's time *inside* the intersection only. It does **not** change **Avg Wait**, which is measured from arrival until the car leaves the queue (see §2.4). The extra delay instead appears as slightly lower **Rolling Throughput** and **Efficiency** when there are many left turns (most visible in Rush Hour) — the realistic cost of unprotected left turns. A *protected* left-turn phase would reduce this but lengthen the overall cycle.

### 6.3 Departure Headway

Cars do not all surge forward the instant the light turns green. A minimum **departure headway of 2 seconds** is enforced between consecutive vehicles leaving the *same* approach. This models real driver reaction time and following distance, and it caps how many cars a single green phase can realistically discharge — an important factor when interpreting Throughput.

### 6.4 Realistic Motion (Visualization)

The rendered cars use simple physics so the animation looks natural:

- **Acceleration / braking** — cars speed up smoothly and brake when approaching a queue or a red light.
- **Brake lights** — illuminate when a car decelerates hard.
- **Speed variance** — each car has a slightly different preferred speed (±18%), so drivers are not identical.
- **Smooth turning** — heading changes are rotated over time, not instant.

> **Important:** This motion is cosmetic. Wait time, throughput, and efficiency are computed from the SimPy event model (arrival, start-cross, and finish timestamps), so the statistics remain exact regardless of the on-screen animation. The one place animation and model meet is the departure rule: a car will not begin crossing until its sprite has actually reached the stop line.

---

## 7. Results & Analysis Screen

Press **A** during the simulation to open the Results & Analysis screen. It contains four panels:

### Top-Left: Queue Length Over Time
Shows how queue lengths changed over the last 3 simulation minutes. Each direction is a separate colored line; the bold white line shows the **total queue** across all approaches. A rising total queue line indicates growing congestion.

### Top-Right: Avg Wait & Rolling Throughput Over Time
Shows three time-series lines:
- **Red** — Avg Wait (left axis, in seconds)
- **Green** — Rolling Throughput (right axis, in cars/min)
- **Purple** — Efficiency score (right axis, scaled)

Watching these together reveals trade-offs: a mode that increases throughput while keeping wait times low will show green rising while red stays flat.

### Bottom-Left: Throughput by Scenario & Mode
A bar chart comparing Fixed (blue) vs. Adaptive (green) throughput across all three scenarios. Bars only appear for scenario/mode combinations that have been run for at least 30 simulation seconds.

### Bottom-Right: Fixed vs. Adaptive — Efficiency Summary
A comparison table showing four metrics side by side for each scenario:

| Metric | What "Better" Means |
|--------|---------------------|
| Avg Wait | Lower is better |
| Max Wait | Lower is better |
| Throughput | Higher is better |
| Efficiency | Higher is better |

The **Δ (Delta)** column shows the difference (Adaptive − Fixed). The **Winner** column highlights which mode performed better for that metric.

> **Note on which Throughput is shown:** The live side panel and the Top-Right chart use the **rolling 60-second** Throughput (recent performance, see §2.3). The two comparison panels above — the bar chart and this summary table — instead use the **cumulative lifetime average** (total vehicles ÷ total sim time × 60). This is intentional: cross-scenario comparisons are fairer using a stable lifetime figure than a fluctuating rolling one.

---

## 8. How to Read the Results Together

When analyzing simulation output, consider these patterns:

- **Adaptive wins on Throughput AND Avg Wait in Rush Hour** → Adaptive is clearly better for high-traffic conditions; it holds green long enough to drain large queues.
- **Fixed and Adaptive are similar in Low Traffic** → When arrival rates are low, there is little queue to adapt to, so both modes perform nearly the same.
- **High Max Wait despite low Avg Wait** → Some vehicles are getting trapped behind long queues while others pass freely. Check the per-direction queue stats — one approach may be consistently backlogged.
- **Rising In Queue with stable Throughput** → The intersection is processing cars at a steady rate, but new arrivals are exceeding that rate. Congestion is accumulating.

---

## 9. Experimental Methodology — Headless Batch Mode

The on-screen simulation is for demonstration. For **results reported in the project paper**, the simulation is run in *headless batch mode*, which applies three standard discrete-event-simulation practices so the numbers are statistically defensible rather than a single observed run.

### 9.1 Why a single run is not enough

Vehicle (and pedestrian) arrivals are random (Poisson, see §5). Running one scenario once gives **one sample** — run it again with different randomness and the numbers change. Reporting a single run is not defensible. Batch mode addresses this with replications, warm-up removal, and confidence intervals.

### 9.2 Running it

```
python traffic_simulation.py --batch
```

This runs every scenario × every mode with no graphics and writes the results as CSV files. The normal command (`python traffic_simulation.py`, no flag) still launches the visual simulation, unchanged. Options:

| Flag | Default | Meaning |
|------|---------|---------|
| `--reps` | 10 | Independent replications per scenario/mode |
| `--duration` | 1800 | Simulated seconds per replication |
| `--warmup` | 300 | Initial sim-seconds discarded as transient |
| `--seed` | 12345 | Base RNG seed |
| `--scenarios` | all | Comma list or `all` |
| `--modes` | all | Comma list or `all` (fixed, adaptive) |
| `--out` | results | Output folder for the CSVs |

### 9.3 Replications

Each scenario/mode is run `--reps` times. Replication *r* uses seed `base_seed + r`, so every run is **independent** but the whole experiment is **exactly reproducible** (re-running with the same seed reproduces the same results — a requirement for a credible report).

### 9.4 Warm-up period removal

When the simulation starts, the intersection is empty — no queues. That startup is not representative of steady operation, so any vehicle that **finishes before `--warmup` sim-seconds** is discarded. All reported metrics are computed only over the steady-state window `[warmup, duration]`. This is the standard remedy for *initialisation bias* in discrete-event simulation.

### 9.5 Confidence intervals (95%)

For each metric, batch mode reports the **mean across replications** and a **95% confidence interval** using the Student's *t* distribution:

> half-width = t₀.₉₇₅(df = R − 1) × (sample standard deviation) ÷ √R

reported as **mean ± half-width**. Interpretation: *"we are 95% confident the true value lies within this range."* A smaller interval = more reliable; widen `--reps` to tighten it. (For more than 30 replications the normal approximation 1.96 is used.)

**Stating a result as significant — the overlap check:** if the ± ranges of two modes **do not overlap**, the difference is statistically significant and can be stated as a firm conclusion. If they **overlap**, the difference is not conclusive from this evidence alone and should be reported as such.

### 9.6 Output files

Two timestamped CSVs are written to the output folder (and saved incrementally, so a long run can be safely interrupted with Ctrl+C and keep whatever finished):

- **`batch_summary_<timestamp>.csv`** — one row per scenario/mode, with `mean`, `stdev`, and `ci95_halfwidth` for each metric. This is the table to put in the report.
- **`batch_replications_<timestamp>.csv`** — one row per individual run (`scenario, mode, replication, avg_wait, max_wait, throughput, efficiency, completed`). This is the raw evidence for an appendix; `completed` is the number of vehicles counted in the steady-state window.

Metrics use the definitions in §2. Note **Avg Wait** is still queue wait (start-cross − arrival, §2.4); throughput here is the steady-state rate over `[warmup, duration]`.

### 9.7 Caveat: oversaturation and non-stationarity

Low Traffic reaches a stable steady state, so its metrics are well-defined. **Normal Traffic and Rush Hour are oversaturated** — vehicles arrive faster than the intersection can discharge, so the queue never stabilises: average wait keeps growing the longer the run, while throughput plateaus at the intersection's capacity. For these scenarios, always report results **at a fixed, stated `--duration`** and explicitly note the system is non-stationary. This stable-vs-oversaturated contrast is itself a key analytical finding.

---

*CS 324 Modeling and Simulation — Final Project*
*Batangas State University, AY 2025–2026*
