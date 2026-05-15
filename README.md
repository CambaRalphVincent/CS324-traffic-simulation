# Traffic Light System Simulation

A discrete-event simulation of a four-way signalised intersection, built with
**SimPy** (simulation engine) and **Pygame** (visualisation). It compares two
traffic-light control strategies — **Fixed-time** vs **Adaptive** — across three
traffic scenarios (Low, Normal, Rush Hour), and models turning vehicles with
permissive left turns, pedestrians, and realistic car motion.

*CS 324 — Modeling and Simulation, Final Project — Batangas State University.*

---

## Requirements

- **Python 3.10 or newer** (developed and tested on Python 3.13)
- Install the dependencies:

```
pip install -r requirements.txt
```

---

## Running it

### 1. Visual simulation (the window)

```
python traffic_simulation.py
```

A window opens — click **START**. Controls:

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `R` | Reset |
| `1` / `2` / `3` | Switch scenario (Low / Normal / Rush Hour) |
| `F` | Toggle Fixed vs Adaptive control |
| `Up` / `Down` | Speed up / slow down |
| `S` | Save the current run to a CSV (in `results/`) |
| `A` | Open the Results & Analysis screen |
| `ESC` | Quit |

### 2. Batch experiments (use this for the report)

Runs with no graphics, repeated many times, with a warm-up period removed and
95% confidence intervals — the statistically defensible numbers for the paper.

```
python traffic_simulation.py --batch
```

Writes two CSV files to `results/`. Useful variants:

```
# Only the fast, stable scenarios, full settings
python traffic_simulation.py --batch --scenarios "Low Traffic,Normal Traffic"

# Rush Hour on its own, shortened so it finishes in reasonable time
python traffic_simulation.py --batch --scenarios "Rush Hour" --duration 600 --reps 5

# See every option
python traffic_simulation.py --help
```

A batch run can be safely interrupted with `Ctrl+C` — whatever finished is
already saved.

---

## Project structure

| Path | What it is |
|------|------------|
| `traffic_simulation.py` | The entire simulation — model, visualisation, and the batch experiment runner |
| `Simulation_Reference_Guide.md` | Full documentation: statistics, control modes, scenarios, vehicle/pedestrian behaviour, and experimental methodology |
| `requirements.txt` | Python dependencies |
| `results/` | CSV output from saved runs and batch experiments |

---

## Documentation

This README is the quick start. For the detailed explanation of every
statistic, the control modes, permissive left turns, and the experimental
methodology (replications, warm-up, confidence intervals) — read
**`Simulation_Reference_Guide.md`**. That guide is the document to cite in the
project paper.
