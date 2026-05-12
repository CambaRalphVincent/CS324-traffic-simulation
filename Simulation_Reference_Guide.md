# Traffic Light System Simulation — Reference Guide

**Course:** CS 324 Modeling and Simulation
**Project Title:** Simulation of Traffic Light System
**Institution:** Batangas State University – Alangilan Campus, CICS
**Academic Year:** 2nd Semester, AY 2025–2026

---

## 1. Overview

This simulation models a four-way intersection controlled by traffic lights. Vehicles arrive from the North, South, East, and West approaches, queue behind the stop line, and cross the intersection when the signal turns green. The simulation is built using **SimPy** (discrete-event simulation engine) and **Pygame** (real-time visualization).

The goal is to measure how different traffic light control strategies affect driver wait times, queue buildup, and overall intersection throughput across three traffic scenarios.

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

---

## 6. Results & Analysis Screen

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

---

## 7. How to Read the Results Together

When analyzing simulation output, consider these patterns:

- **Adaptive wins on Throughput AND Avg Wait in Rush Hour** → Adaptive is clearly better for high-traffic conditions; it holds green long enough to drain large queues.
- **Fixed and Adaptive are similar in Low Traffic** → When arrival rates are low, there is little queue to adapt to, so both modes perform nearly the same.
- **High Max Wait despite low Avg Wait** → Some vehicles are getting trapped behind long queues while others pass freely. Check the per-direction queue stats — one approach may be consistently backlogged.
- **Rising In Queue with stable Throughput** → The intersection is processing cars at a steady rate, but new arrivals are exceeding that rate. Congestion is accumulating.

---

*Generated for CS 324 Modeling and Simulation — Final Project*
*Batangas State University, AY 2025–2026*
