"""
Traffic Light System Simulation
CS 324: Modeling and Simulation - Final Project
Batangas State University

Tech stack: SimPy (discrete-event simulation) + Pygame (visualization)
Author: [Group Name]

Usage:
    python traffic_simulation.py

Controls (in window):
    SPACE      - Pause/Resume
    R          - Reset simulation
    1, 2, 3    - Switch scenarios (Low / Normal / Rush)
    F          - Toggle Fixed vs Adaptive light control
    UP/DOWN    - Speed up / slow down simulation
    S          - Save results to CSV
    ESC        - Quit
"""

import simpy
import pygame
import random
import csv
import os
from collections import deque
from datetime import datetime

# =====================================================================
# CONFIGURATION
# =====================================================================

# Display
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
INTERSECTION_CENTER = (500, 400)
ROAD_WIDTH = 100
LANE_WIDTH = 100
FPS = 60

# Colors
COLOR_BG = (30, 30, 35)
COLOR_ROAD = (60, 60, 65)
COLOR_LANE_LINE = (200, 200, 100)
COLOR_RED = (220, 50, 50)
COLOR_YELLOW = (240, 200, 60)
COLOR_GREEN = (60, 200, 90)
COLOR_LIGHT_OFF = (50, 50, 50)
COLOR_TEXT = (230, 230, 235)
COLOR_TEXT_DIM = (160, 160, 170)
COLOR_PANEL = (40, 40, 48)
COLOR_PANEL_BORDER = (70, 70, 80)
COLOR_ACCENT = (90, 180, 255)

CAR_COLORS = [
    (200, 100, 100), (100, 150, 220), (220, 180, 80),
    (150, 200, 120), (200, 120, 200), (120, 200, 200),
    (240, 140, 80), (180, 180, 180),
]

# Simulation parameters
LIGHT_TIMINGS_FIXED = {
    'green': 20.0,
    'yellow': 3.0,
    'all_red': 1.0,  # safety buffer when both directions red
}

# Adaptive control parameters
ADAPTIVE_MIN_GREEN = 8.0
ADAPTIVE_MAX_GREEN = 40.0
ADAPTIVE_QUEUE_THRESHOLD = 2  # extend green if queue still long

# Vehicle behavior
CAR_LENGTH = 55
CAR_WIDTH = 38
CAR_SPACING = 8  # gap between queued cars
CAR_SPEED = 60   # pixels per simulated second when moving
CROSS_TIME = 2.5        # seconds for a car to clear the intersection box
APPROACH_ANIM_TIME = 1.5  # sim seconds to slide in from the road edge
EXIT_SPEED = 130          # px/sim-second for post-intersection travel to screen edge
DEPART_HEADWAY = 2.0      # min sim-seconds between consecutive departures from same approach

# Scenarios: arrival rate per direction (vehicles/sec)
SCENARIOS = {
    'Low Traffic': {
        'N': 0.10, 'S': 0.10, 'E': 0.10, 'W': 0.10,
    },
    'Normal Traffic': {
        'N': 0.25, 'S': 0.25, 'E': 0.20, 'W': 0.20,
    },
    'Rush Hour': {
        'N': 0.50, 'S': 0.45, 'E': 0.35, 'W': 0.35,
    },
}

DIRECTIONS = ['N', 'S', 'E', 'W']
NS_DIRECTIONS = ['N', 'S']
EW_DIRECTIONS = ['E', 'W']

# Pedestrian parameters
CROSSWALK_WIDTH = 14          # px — stripe band width
PED_CROSS_TIME = 4.0          # seconds to walk across
PED_ARRIVAL_RATE = 0.06       # pedestrians/sec per crosswalk
PED_COLORS = [
    (230, 190, 140), (180, 230, 160), (160, 190, 240),
    (240, 160, 190), (210, 210, 150), (150, 210, 210),
]


# =====================================================================
# EXIT PATH LOOKUP  (precomputed from module-level constants)
# Each entry: (start_pos, end_pos) — start = exit stop-line, end = off-screen
# =====================================================================

_CX, _CY = INTERSECTION_CENTER
_LN = LANE_WIDTH // 2
_RW = ROAD_WIDTH
_EM = CAR_LENGTH + 5          # margin beyond screen edge

_EXIT_INFO = {
    ('N', 'straight'): ((_CX-_LN, _CY+_RW), (_CX-_LN, WINDOW_HEIGHT+_EM)),
    ('N', 'right'):    ((_CX-_RW, _CY-_LN), (-_EM,            _CY-_LN)),
    ('N', 'left'):     ((_CX+_RW, _CY+_LN), (WINDOW_WIDTH+_EM, _CY+_LN)),
    ('S', 'straight'): ((_CX+_LN, _CY-_RW), (_CX+_LN, -_EM)),
    ('S', 'right'):    ((_CX+_RW, _CY+_LN), (WINDOW_WIDTH+_EM, _CY+_LN)),
    ('S', 'left'):     ((_CX-_RW, _CY-_LN), (-_EM,            _CY-_LN)),
    ('E', 'straight'): ((_CX-_RW, _CY-_LN), (-_EM,            _CY-_LN)),
    ('E', 'right'):    ((_CX+_LN, _CY-_RW), (_CX+_LN, -_EM)),
    ('E', 'left'):     ((_CX-_LN, _CY+_RW), (_CX-_LN, WINDOW_HEIGHT+_EM)),
    ('W', 'straight'): ((_CX+_RW, _CY+_LN), (WINDOW_WIDTH+_EM, _CY+_LN)),
    ('W', 'right'):    ((_CX-_LN, _CY+_RW), (_CX-_LN, WINDOW_HEIGHT+_EM)),
    ('W', 'left'):     ((_CX+_LN, _CY-_RW), (_CX+_LN, -_EM)),
}

# All exit paths are purely H or V, so Manhattan distance == Euclidean
EXIT_TIMES = {
    key: (abs(e[0]-s[0]) + abs(e[1]-s[1])) / EXIT_SPEED
    for key, (s, e) in _EXIT_INFO.items()
}

_EXIT_ANGLES = {
    ('N', 'straight'): 0,   ('N', 'right'): 270, ('N', 'left'): 90,
    ('S', 'straight'): 180, ('S', 'right'): 90,  ('S', 'left'): 270,
    ('E', 'straight'): 270, ('E', 'right'): 180, ('E', 'left'): 0,
    ('W', 'straight'): 90,  ('W', 'right'): 0,   ('W', 'left'): 180,
}


# =====================================================================
# UI BUTTON
# =====================================================================

class Button:
    def __init__(self, rect, label, font, bg_color, hover_color,
                 text_color=(230, 230, 235)):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color

    def draw(self, screen):
        color = (self.hover_color
                 if self.rect.collidepoint(pygame.mouse.get_pos())
                 else self.bg_color)
        pygame.draw.rect(screen, color, self.rect, border_radius=7)
        pygame.draw.rect(screen, (200, 200, 210), self.rect, 1, border_radius=7)
        text = self.font.render(self.label, True, self.text_color)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


# =====================================================================
# SIMULATION MODEL (SimPy)
# =====================================================================

class TrafficLightController:
    """
    Controls the traffic light cycle.
    Two modes:
      - Fixed: alternates NS/EW with constant timing
      - Adaptive: extends green time when queue is still long
    """
    def __init__(self, env, intersection, mode='fixed'):
        self.env = env
        self.intersection = intersection
        self.mode = mode
        # Phase: 'NS_green', 'NS_yellow', 'EW_green', 'EW_yellow', 'all_red'
        self.phase = 'NS_green'
        self.phase_start_time = 0.0
        self.action = env.process(self.run())

    def state_for(self, direction):
        """Return current light color for a given approach."""
        if direction in NS_DIRECTIONS:
            if self.phase == 'NS_green':
                return 'green'
            elif self.phase == 'NS_yellow':
                return 'yellow'
            else:
                return 'red'
        else:  # E or W
            if self.phase == 'EW_green':
                return 'green'
            elif self.phase == 'EW_yellow':
                return 'yellow'
            else:
                return 'red'

    def time_in_phase(self):
        return self.env.now - self.phase_start_time

    def run(self):
        while True:
            # NS GREEN
            self.phase = 'NS_green'
            self.phase_start_time = self.env.now
            yield self.env.process(self._green_phase(NS_DIRECTIONS))

            # NS YELLOW
            self.phase = 'NS_yellow'
            self.phase_start_time = self.env.now
            yield self.env.timeout(LIGHT_TIMINGS_FIXED['yellow'])

            # ALL RED (safety buffer)
            self.phase = 'all_red_1'
            self.phase_start_time = self.env.now
            yield self.env.timeout(LIGHT_TIMINGS_FIXED['all_red'])

            # EW GREEN
            self.phase = 'EW_green'
            self.phase_start_time = self.env.now
            yield self.env.process(self._green_phase(EW_DIRECTIONS))

            # EW YELLOW
            self.phase = 'EW_yellow'
            self.phase_start_time = self.env.now
            yield self.env.timeout(LIGHT_TIMINGS_FIXED['yellow'])

            # ALL RED (safety buffer)
            self.phase = 'all_red_2'
            self.phase_start_time = self.env.now
            yield self.env.timeout(LIGHT_TIMINGS_FIXED['all_red'])

    def _green_phase(self, directions):
        """Run a green phase, optionally extending in adaptive mode."""
        if self.mode == 'fixed':
            yield self.env.timeout(LIGHT_TIMINGS_FIXED['green'])
        else:
            # Adaptive: start with min green, then check queues
            elapsed = 0.0
            yield self.env.timeout(ADAPTIVE_MIN_GREEN)
            elapsed += ADAPTIVE_MIN_GREEN
            # Extend in 2-second increments while queue is long
            while elapsed < ADAPTIVE_MAX_GREEN:
                queue_size = sum(
                    len(self.intersection.queues[d]) for d in directions
                )
                cross_queue = sum(
                    len(self.intersection.queues[d])
                    for d in DIRECTIONS if d not in directions
                )
                # Stop extending if our queue is short OR cross queue is much longer
                if queue_size <= ADAPTIVE_QUEUE_THRESHOLD:
                    break
                if cross_queue > queue_size * 2:
                    break
                yield self.env.timeout(2.0)
                elapsed += 2.0


class Vehicle:
    """Represents one car in the simulation."""
    _id_counter = 0

    def __init__(self, env, direction, intersection):
        Vehicle._id_counter += 1
        self.id = Vehicle._id_counter
        self.env = env
        self.direction = direction
        self.intersection = intersection
        self.arrival_time = env.now
        self.start_cross_time = None
        self.finish_time = None
        self.color = random.choice(CAR_COLORS)
        self.turn = random.choice(['straight', 'straight', 'left', 'right'])
        # Position is computed dynamically based on queue index
        self.queue_index = None
        self.appear_time = env.now  # used to animate the road-edge approach
        # State: 'queued', 'crossing', 'exiting', 'done'
        self.state = 'queued'
        self.cross_progress = 0.0   # 0→1 while crossing intersection box
        self.exit_progress = 0.0    # 0→1 while travelling to screen edge
        self.process = env.process(self.run())

    def wait_time(self):
        if self.start_cross_time is None:
            return self.env.now - self.arrival_time
        return self.start_cross_time - self.arrival_time

    def run(self):
        # Join the queue
        queue = self.intersection.queues[self.direction]
        queue.append(self)
        self.queue_index = len(queue) - 1

        # Wait until: green AND head of queue AND minimum headway since last departure
        while True:
            light = self.intersection.controller.state_for(self.direction)
            at_head = (queue[0] is self) if queue else False
            gap = self.env.now - self.intersection.last_depart[self.direction]
            if light == 'green' and at_head and gap >= DEPART_HEADWAY:
                break
            yield self.env.timeout(0.1)
            if self in queue:
                self.queue_index = queue.index(self)

        # Depart — record time so next car enforces headway
        self.start_cross_time = self.env.now
        self.intersection.last_depart[self.direction] = self.env.now
        self.state = 'crossing'
        queue.popleft()
        for i, v in enumerate(queue):
            v.queue_index = i
        self.intersection.active_crossing.append(self)

        # Animate through intersection box
        start = self.env.now
        while self.env.now - start < CROSS_TIME:
            self.cross_progress = (self.env.now - start) / CROSS_TIME
            yield self.env.timeout(0.05)
        self.cross_progress = 1.0

        # Intersection cleared — record for stats and release blocking slot
        self.finish_time = self.env.now
        self.intersection.completed.append(self)
        self.intersection.active_crossing.remove(self)

        # Exit phase: animate from exit stop-line to screen edge (non-blocking)
        self.state = 'exiting'
        self.exit_progress = 0.0
        self.intersection.exiting.append(self)

        exit_time = EXIT_TIMES[(self.direction, self.turn)]
        start = self.env.now
        while self.env.now - start < exit_time:
            self.exit_progress = (self.env.now - start) / exit_time
            yield self.env.timeout(0.05)
        self.exit_progress = 1.0
        self.state = 'done'
        self.intersection.exiting.remove(self)


class Pedestrian:
    """A pedestrian waiting at a crosswalk and walking across when safe."""
    _id_counter = 0

    def __init__(self, env, crosswalk, intersection):
        Pedestrian._id_counter += 1
        self.id = Pedestrian._id_counter
        self.env = env
        self.crosswalk = crosswalk   # 'N' | 'S' | 'E' | 'W'
        self.intersection = intersection
        self.side = random.randint(0, 1)  # which end of the crosswalk they start from
        self.color = random.choice(PED_COLORS)
        self.state = 'waiting'       # 'waiting' | 'crossing' | 'done'
        self.cross_progress = 0.0
        self.process = env.process(self.run())

    def _signal_green(self):
        """True when the cars that would hit this crosswalk are stopped."""
        phase = self.intersection.controller.phase
        if self.crosswalk in ('N', 'S'):
            return 'NS' not in phase   # safe during EW_green / yellow / all_red
        else:
            return 'EW' not in phase   # safe during NS_green / yellow / all_red

    def run(self):
        self.intersection.active_pedestrians.append(self)
        while not self._signal_green():
            yield self.env.timeout(0.1)
        self.state = 'crossing'
        start = self.env.now
        while self.env.now - start < PED_CROSS_TIME:
            self.cross_progress = (self.env.now - start) / PED_CROSS_TIME
            yield self.env.timeout(0.1)
        self.cross_progress = 1.0
        self.state = 'done'
        self.intersection.active_pedestrians.remove(self)


class Intersection:
    """Holds queues, controller, statistics."""
    def __init__(self, env, control_mode='fixed', scenario='Normal Traffic'):
        self.env = env
        self.scenario = scenario
        self.queues = {d: deque() for d in DIRECTIONS}
        self.completed = []
        self.active_crossing = []
        self.exiting = []
        self.active_pedestrians = []
        self.last_depart = {d: -999.0 for d in DIRECTIONS}
        self.controller = TrafficLightController(env, self, mode=control_mode)
        for d in DIRECTIONS:
            env.process(self._spawn_vehicles(d))
            env.process(self._spawn_pedestrians(d))

    def _spawn_vehicles(self, direction):
        rate = SCENARIOS[self.scenario][direction]
        while True:
            yield self.env.timeout(random.expovariate(rate))
            Vehicle(self.env, direction, self)

    def _spawn_pedestrians(self, crosswalk):
        while True:
            yield self.env.timeout(random.expovariate(PED_ARRIVAL_RATE))
            Pedestrian(self.env, crosswalk, self)

    def stats(self):
        n_completed = len(self.completed)
        now = self.env.now
        if n_completed == 0:
            avg_wait = 0.0
            max_wait = 0.0
        else:
            waits = [v.wait_time() for v in self.completed]
            avg_wait = sum(waits) / len(waits)
            max_wait = max(waits)
        # Rolling 60-second window throughput (recent performance, not lifetime average)
        window = 60.0
        recent = [v for v in self.completed if v.finish_time is not None and v.finish_time >= now - window]
        rolling_throughput = len(recent) / min(max(now, 1), window) * 60
        cumulative_throughput = n_completed / max(now, 1) * 60
        # Efficiency: how many cars/min are served per second of average wait
        efficiency = (rolling_throughput / avg_wait) if avg_wait > 0 else rolling_throughput
        queue_lengths = {d: len(self.queues[d]) for d in DIRECTIONS}
        total_queued = sum(queue_lengths.values())
        return {
            'sim_time': now,
            'completed': n_completed,
            'avg_wait': avg_wait,
            'max_wait': max_wait,
            'queues': queue_lengths,
            'total_queued': total_queued,
            'throughput': cumulative_throughput,
            'rolling_throughput': rolling_throughput,
            'efficiency': efficiency,
        }


# =====================================================================
# VISUALIZATION (Pygame)
# =====================================================================

class Renderer:
    def __init__(self, screen, font, font_small, font_big):
        self.screen = screen
        self.font = font
        self.font_small = font_small
        self.font_big = font_big
        self.cx, self.cy = INTERSECTION_CENTER

    def draw_roads(self):
        # Vertical road
        pygame.draw.rect(
            self.screen, COLOR_ROAD,
            (self.cx - ROAD_WIDTH, 0, ROAD_WIDTH * 2, WINDOW_HEIGHT)
        )
        # Horizontal road
        pygame.draw.rect(
            self.screen, COLOR_ROAD,
            (0, self.cy - ROAD_WIDTH, WINDOW_WIDTH, ROAD_WIDTH * 2)
        )
        # Center divider lines (dashed)
        for y in range(0, WINDOW_HEIGHT, 30):
            if abs(y - self.cy) > ROAD_WIDTH:
                pygame.draw.line(
                    self.screen, COLOR_LANE_LINE,
                    (self.cx, y), (self.cx, y + 15), 2
                )
        for x in range(0, WINDOW_WIDTH, 30):
            if abs(x - self.cx) > ROAD_WIDTH:
                pygame.draw.line(
                    self.screen, COLOR_LANE_LINE,
                    (x, self.cy), (x + 15, self.cy), 2
                )
        # Stop lines — RHT: each line spans the approaching car's lane
        # N southbound: west lane (cx-ROAD_WIDTH to cx)
        pygame.draw.line(self.screen, (240, 240, 240),
                         (self.cx - ROAD_WIDTH, self.cy - ROAD_WIDTH),
                         (self.cx, self.cy - ROAD_WIDTH), 3)
        # S northbound: east lane (cx to cx+ROAD_WIDTH)
        pygame.draw.line(self.screen, (240, 240, 240),
                         (self.cx, self.cy + ROAD_WIDTH),
                         (self.cx + ROAD_WIDTH, self.cy + ROAD_WIDTH), 3)
        # E westbound: north lane (cy-ROAD_WIDTH to cy)
        pygame.draw.line(self.screen, (240, 240, 240),
                         (self.cx + ROAD_WIDTH, self.cy - ROAD_WIDTH),
                         (self.cx + ROAD_WIDTH, self.cy), 3)
        # W eastbound: south lane (cy to cy+ROAD_WIDTH)
        pygame.draw.line(self.screen, (240, 240, 240),
                         (self.cx - ROAD_WIDTH, self.cy),
                         (self.cx - ROAD_WIDTH, self.cy + ROAD_WIDTH), 3)

    def draw_lights(self, controller):
        """Traffic lights at each approach."""
        # RHT: each light sits at the near-right corner of its approach lane
        positions = {
            'N': (self.cx - ROAD_WIDTH - 35, self.cy - ROAD_WIDTH - 30),  # top-left
            'S': (self.cx + ROAD_WIDTH + 15, self.cy + ROAD_WIDTH + 15),  # bottom-right
            'E': (self.cx + ROAD_WIDTH + 15, self.cy - ROAD_WIDTH - 30),  # top-right
            'W': (self.cx - ROAD_WIDTH - 35, self.cy + ROAD_WIDTH + 15),  # bottom-left
        }
        for direction, (x, y) in positions.items():
            state = controller.state_for(direction)
            # Housing
            pygame.draw.rect(self.screen, (25, 25, 30), (x, y, 20, 50))
            pygame.draw.rect(self.screen, (70, 70, 80), (x, y, 20, 50), 1)
            # Three lights
            colors = {
                'red': COLOR_RED if state == 'red' else COLOR_LIGHT_OFF,
                'yellow': COLOR_YELLOW if state == 'yellow' else COLOR_LIGHT_OFF,
                'green': COLOR_GREEN if state == 'green' else COLOR_LIGHT_OFF,
            }
            pygame.draw.circle(self.screen, colors['red'], (x + 10, y + 8), 5)
            pygame.draw.circle(self.screen, colors['yellow'], (x + 10, y + 25), 5)
            pygame.draw.circle(self.screen, colors['green'], (x + 10, y + 42), 5)
            # Direction label
            label = self.font_small.render(direction, True, COLOR_TEXT_DIM)
            self.screen.blit(label, (x + 4, y + 52))

    def _crossing_path(self, direction, turn):
        """
        Returns (start, pivot, end, angle_start, angle_end) for a crossing vehicle.
        pivot is None for straight (simple lerp); otherwise a two-segment path is used.
        All positions are in the correct exit lane for right-hand traffic.
        """
        cx, cy = self.cx, self.cy
        LN = LANE_WIDTH // 2   # 50 — half-lane offset from road centre
        RW = ROAD_WIDTH        # 100
        EXT = 0                # car ends at exit stop-line; _exit_path handles the rest

        if direction == 'N':           # RHT: west lane (cx-LN) going south
            s, a0 = (cx - LN, cy - RW), 0
            if turn == 'straight':
                return s, None,               (cx - LN, cy + RW + EXT), a0, 0
            elif turn == 'right':             # → west; westbound = north lane (cy-LN)
                return s, (cx - LN, cy - LN), (cx - RW - EXT, cy - LN), a0, 270
            else:                             # left → east; eastbound = south lane (cy+LN)
                return s, (cx,      cy),      (cx + RW + EXT, cy + LN), a0, 90

        elif direction == 'S':         # RHT: east lane (cx+LN) going north
            s, a0 = (cx + LN, cy + RW), 180
            if turn == 'straight':
                return s, None,               (cx + LN, cy - RW - EXT), a0, 180
            elif turn == 'right':             # → east; eastbound = south lane (cy+LN)
                return s, (cx + LN, cy + LN), (cx + RW + EXT, cy + LN), a0, 90
            else:                             # left → west; westbound = north lane (cy-LN)
                return s, (cx,      cy),      (cx - RW - EXT, cy - LN), a0, 270

        elif direction == 'E':         # RHT: north lane (cy-LN) going west
            s, a0 = (cx + RW, cy - LN), 270
            if turn == 'straight':
                return s, None,               (cx - RW - EXT, cy - LN), a0, 270
            elif turn == 'right':             # → north; northbound = east lane (cx+LN)
                return s, (cx + LN, cy - LN), (cx + LN, cy - RW - EXT), a0, 180
            else:                             # left → south; southbound = west lane (cx-LN)
                return s, (cx,      cy),      (cx - LN, cy + RW + EXT), a0, 0

        else:                          # W — RHT: south lane (cy+LN) going east
            s, a0 = (cx - RW, cy + LN), 90
            if turn == 'straight':
                return s, None,               (cx + RW + EXT, cy + LN), a0, 90
            elif turn == 'right':             # → south; southbound = west lane (cx-LN)
                return s, (cx - LN, cy + LN), (cx - LN, cy + RW + EXT), a0, 0
            else:                             # left → north; northbound = east lane (cx+LN)
                return s, (cx,      cy),      (cx + LN, cy - RW - EXT), a0, 180

    def car_position(self, vehicle):
        """Compute the (x, y, angle) of a vehicle on screen."""
        cx, cy = self.cx, self.cy
        d = vehicle.direction
        if vehicle.state == 'queued':
            offset = vehicle.queue_index * (CAR_LENGTH + CAR_SPACING) + CAR_LENGTH // 2 + 10
            # Target queue position and road-edge spawn point
            if d == 'N':
                tx, ty, angle = cx - LANE_WIDTH/2, cy - ROAD_WIDTH - offset, 0
                sx, sy = tx, 0
            elif d == 'S':
                tx, ty, angle = cx + LANE_WIDTH/2, cy + ROAD_WIDTH + offset, 180
                sx, sy = tx, WINDOW_HEIGHT
            elif d == 'E':
                tx, ty, angle = cx + ROAD_WIDTH + offset, cy - LANE_WIDTH/2, 270
                sx, sy = WINDOW_WIDTH, ty
            else:  # W
                tx, ty, angle = cx - ROAD_WIDTH - offset, cy + LANE_WIDTH/2, 90
                sx, sy = 0, ty
            # Slide in from the edge over APPROACH_ANIM_TIME sim seconds
            elapsed = vehicle.env.now - vehicle.appear_time
            if elapsed < APPROACH_ANIM_TIME:
                t = elapsed / APPROACH_ANIM_TIME
                return (sx + t * (tx - sx), sy + t * (ty - sy), angle)
            return (tx, ty, angle)
        elif vehicle.state == 'crossing':
            p = vehicle.cross_progress
            start, pivot, end, a_start, a_end = self._crossing_path(d, vehicle.turn)
            if pivot is None:
                # Straight — simple linear interpolation
                x = start[0] + p * (end[0] - start[0])
                y = start[1] + p * (end[1] - start[1])
                return (x, y, a_start)
            elif p < 0.5:
                # First half: entry point → pivot
                t = p * 2
                x = start[0] + t * (pivot[0] - start[0])
                y = start[1] + t * (pivot[1] - start[1])
                return (x, y, a_start)
            else:
                # Second half: pivot → exit point (car has turned)
                t = (p - 0.5) * 2
                x = pivot[0] + t * (end[0] - pivot[0])
                y = pivot[1] + t * (end[1] - pivot[1])
                return (x, y, a_end)
        return None

    def exit_position(self, vehicle):
        """Linear interpolation from exit stop-line to off-screen edge."""
        key = (vehicle.direction, vehicle.turn)
        s, e = _EXIT_INFO[key]
        angle = _EXIT_ANGLES[key]
        p = vehicle.exit_progress
        return (s[0] + p * (e[0] - s[0]), s[1] + p * (e[1] - s[1]), angle)

    def draw_car(self, x, y, angle, color):
        # Build a rotated rectangle
        if angle in (0, 180):
            w, h = CAR_WIDTH, CAR_LENGTH
        else:
            w, h = CAR_LENGTH, CAR_WIDTH
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (x, y)
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        pygame.draw.rect(self.screen, (20, 20, 20), rect, 1, border_radius=5)
        # Windshield hint
        if angle == 0:
            pygame.draw.rect(self.screen, (100, 130, 160),
                             (rect.x + 4, rect.y + 4, w - 8, 8))
        elif angle == 180:
            pygame.draw.rect(self.screen, (100, 130, 160),
                             (rect.x + 4, rect.bottom - 12, w - 8, 8))
        elif angle == 270:
            pygame.draw.rect(self.screen, (100, 130, 160),
                             (rect.x + 4, rect.y + 4, 8, h - 8))
        elif angle == 90:
            pygame.draw.rect(self.screen, (100, 130, 160),
                             (rect.right - 12, rect.y + 4, 8, h - 8))

    def draw_vehicles(self, intersection):
        for d in DIRECTIONS:
            for v in intersection.queues[d]:
                pos = self.car_position(v)
                if pos:
                    self.draw_car(pos[0], pos[1], pos[2], v.color)
        for v in intersection.active_crossing:
            pos = self.car_position(v)
            if pos:
                self.draw_car(pos[0], pos[1], pos[2], v.color)
        for v in intersection.exiting:
            pos = self.exit_position(v)
            if pos:
                self.draw_car(pos[0], pos[1], pos[2], v.color)

    def draw_panel(self, sim_state):
        """Right-side info panel."""
        x = 1000
        w = 200
        pygame.draw.rect(self.screen, COLOR_PANEL, (x, 0, w, WINDOW_HEIGHT))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER,
                         (x, 0), (x, WINDOW_HEIGHT), 1)

        # Title
        title = self.font_big.render("Traffic Sim", True, COLOR_ACCENT)
        self.screen.blit(title, (x + 15, 15))
        subtitle = self.font_small.render("CS 324 Final Project",
                                          True, COLOR_TEXT_DIM)
        self.screen.blit(subtitle, (x + 15, 45))

        y = 130

        def line(label, value, color=COLOR_TEXT):
            nonlocal y
            lbl = self.font_small.render(label, True, COLOR_TEXT_DIM)
            self.screen.blit(lbl, (x + 15, y))
            val = self.font.render(str(value), True, color)
            self.screen.blit(val, (x + 15, y + 14))
            y += 33

        def sep(title):
            nonlocal y
            y += 4
            s = self.font_small.render(title, True, COLOR_TEXT_DIM)
            self.screen.blit(s, (x + 15, y))
            y += 16

        # Status
        line("Scenario", sim_state['scenario'])
        line("Control", sim_state['mode'].upper(), COLOR_ACCENT)
        line("Sim Time", f"{sim_state['sim_time']:.1f}s")
        line("Speed", f"{sim_state['speed']:.1f}x")

        sep("─ STATISTICS ─")
        line("Completed", sim_state['completed'])
        line("In Queue",  sim_state['total_queued'],
             COLOR_RED if sim_state['total_queued'] > 8 else
             (COLOR_YELLOW if sim_state['total_queued'] > 3 else COLOR_TEXT))
        line("Throughput", f"{sim_state['rolling_throughput']:.1f}/min")
        line("Avg Wait", f"{sim_state['avg_wait']:.2f}s")
        line("Max Wait", f"{sim_state['max_wait']:.2f}s")
        line("Efficiency", f"{sim_state['efficiency']:.2f}")

        sep("─ QUEUES ─")
        # Compact 2-column grid: NS row, then EW row
        col_r = x + 108
        for dl, dr in [('N', 'S'), ('E', 'W')]:
            ql = sim_state['queues'][dl]
            qr = sim_state['queues'][dr]
            cl = COLOR_RED if ql > 5 else (COLOR_YELLOW if ql > 2 else COLOR_GREEN)
            cr = COLOR_RED if qr > 5 else (COLOR_YELLOW if qr > 2 else COLOR_GREEN)
            self.screen.blit(self.font_small.render(dl, True, COLOR_TEXT_DIM), (x + 15, y))
            self.screen.blit(self.font_small.render(dr, True, COLOR_TEXT_DIM), (col_r,   y))
            self.screen.blit(self.font.render(str(ql), True, cl), (x + 15, y + 14))
            self.screen.blit(self.font.render(str(qr), True, cr), (col_r,        y + 14))
            y += 33

        sep("─ PEDESTRIANS ─")
        pw = sim_state['peds_waiting']
        pc = sim_state['peds_crossing']
        line("Waiting", pw, COLOR_RED if pw > 4 else COLOR_TEXT)
        line("Crossing", pc, COLOR_GREEN if pc > 0 else COLOR_TEXT)

        # Controls help (bottom) — draw upward from the bottom edge
        help_lines = [
            "ESC    Quit",
            "A      Analysis",
            "R      Reset",
            "S      Save CSV",
            "↑/↓    Speed",
            "F      Toggle mode",
            "1/2/3  Scenario",
            "SPACE  Pause/Resume",
        ]
        hy = WINDOW_HEIGHT - 14
        for hl in help_lines:
            t = self.font_small.render(hl, True, COLOR_TEXT_DIM)
            self.screen.blit(t, (x + 15, hy - 13))
            hy -= 15
        # Divider above controls
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER,
                         (x + 10, hy), (x + w - 10, hy), 1)

    def draw_crosswalks(self):
        cx, cy = self.cx, self.cy
        RW = ROAD_WIDTH
        CW = CROSSWALK_WIDTH
        stripe = 5
        gap = 4

        # Crosswalks sit INSIDE the intersection edges so approaching cars
        # (which stop before the edge) never animate through them.
        # North — just inside the top edge
        y0 = cy - RW
        for x in range(cx - RW, cx + RW, stripe + gap):
            pygame.draw.rect(self.screen, (190, 190, 190), (x, y0, stripe, CW))

        # South — just inside the bottom edge
        y0 = cy + RW - CW
        for x in range(cx - RW, cx + RW, stripe + gap):
            pygame.draw.rect(self.screen, (190, 190, 190), (x, y0, stripe, CW))

        # West — just inside the left edge
        x0 = cx - RW
        for y in range(cy - RW, cy + RW, stripe + gap):
            pygame.draw.rect(self.screen, (190, 190, 190), (x0, y, CW, stripe))

        # East — just inside the right edge
        x0 = cx + RW - CW
        for y in range(cy - RW, cy + RW, stripe + gap):
            pygame.draw.rect(self.screen, (190, 190, 190), (x0, y, CW, stripe))

    def ped_position(self, ped):
        cx, cy = self.cx, self.cy
        RW = ROAD_WIDTH
        CW = CROSSWALK_WIDTH
        p = ped.cross_progress
        cw = ped.crosswalk
        s = ped.side  # 0 = left/top start, 1 = right/bottom start

        if cw == 'N':
            y = cy - RW + CW // 2          # centre of inner-top crosswalk band
            x0 = cx - RW if s == 0 else cx + RW
            x1 = cx + RW if s == 0 else cx - RW
            return (x0 + p * (x1 - x0), y)
        elif cw == 'S':
            y = cy + RW - CW // 2          # centre of inner-bottom band
            x0 = cx - RW if s == 0 else cx + RW
            x1 = cx + RW if s == 0 else cx - RW
            return (x0 + p * (x1 - x0), y)
        elif cw == 'W':
            x = cx - RW + CW // 2          # centre of inner-left band
            y0 = cy - RW if s == 0 else cy + RW
            y1 = cy + RW if s == 0 else cy - RW
            return (x, y0 + p * (y1 - y0))
        else:  # E
            x = cx + RW - CW // 2          # centre of inner-right band
            y0 = cy - RW if s == 0 else cy + RW
            y1 = cy + RW if s == 0 else cy - RW
            return (x, y0 + p * (y1 - y0))

    def draw_pedestrians(self, intersection):
        for ped in intersection.active_pedestrians:
            px, py = self.ped_position(ped)
            # Red dot when waiting, pedestrian color when crossing
            color = (210, 60, 60) if ped.state == 'waiting' else ped.color
            pygame.draw.circle(self.screen, color, (int(px), int(py)), 4)
            pygame.draw.circle(self.screen, (15, 15, 15), (int(px), int(py)), 4, 1)

    def draw_pause_overlay(self):
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 120))
        self.screen.blit(s, (0, 0))
        msg = self.font_big.render("PAUSED", True, COLOR_TEXT)
        rect = msg.get_rect(center=(self.cx, self.cy))
        self.screen.blit(msg, rect)

    # ─────────────────────────────────────────────────────────────
    # ANALYSIS SCREEN  (toggled with A key)
    # ─────────────────────────────────────────────────────────────

    def _chart_bg(self, rect, title):
        """Draw chart card; return inner (cx, cy, cw, ch) for plotting."""
        rx, ry, rw, rh = rect
        pygame.draw.rect(self.screen, (30, 30, 38), rect)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, rect, 1)
        self.screen.blit(self.font.render(title, True, COLOR_ACCENT), (rx + 8, ry + 6))
        # Top: 28 px for title.  Bottom: 24 px for x-axis labels.
        return rx + 50, ry + 28, rw - 60, rh - 52

    def _axes(self, cx, cy, cw, ch, y_max, n=4):
        for i in range(n + 1):
            gy = cy + int(ch * i / n)
            pygame.draw.line(self.screen, (45, 45, 55), (cx, gy), (cx + cw, gy), 1)
            val = y_max * (1 - i / n)
            lbl = self.font_small.render(f"{val:.1f}", True, COLOR_TEXT_DIM)
            self.screen.blit(lbl, (cx - lbl.get_width() - 4, gy - 7))
        pygame.draw.line(self.screen, (100, 100, 110), (cx, cy),      (cx,      cy + ch), 1)
        pygame.draw.line(self.screen, (100, 100, 110), (cx, cy + ch), (cx + cw, cy + ch), 1)

    def _plot(self, cx, cy, cw, ch, values, y_max, color, thick=2):
        if len(values) < 2:
            return
        y_max = max(y_max, 0.001)
        n = len(values)
        pts = [
            (cx + int(cw * i / (n - 1)),
             max(cy, min(cy + ch, cy + int(ch * (1 - min(v, y_max) / y_max)))))
            for i, v in enumerate(values)
        ]
        pygame.draw.lines(self.screen, color, False, pts, thick)

    def _draw_queue_chart(self, rect, history):
        data = history[-180:]
        cx, cy, cw, ch = self._chart_bg(
            rect, "Queue Length Over Time  (last 3 min sim)")
        dir_series = [
            ('N', (220, 80,  80)),
            ('S', (80,  140, 220)),
            ('E', (80,  200, 100)),
            ('W', (220, 180,  60)),
        ]
        totals = [sum(h['queues'][d] for d in DIRECTIONS) for h in data]
        all_q  = [h['queues'][d] for h in data for d in 'NSEW'] + totals
        y_max  = max(max(all_q, default=0), 1)
        self._axes(cx, cy, cw, ch, y_max)
        # Per-direction lines (thin)
        for label, color in dir_series:
            self._plot(cx, cy, cw, ch, [h['queues'][label] for h in data], y_max, color, thick=1)
        # Total queue (bold white line — most visible indicator of congestion)
        self._plot(cx, cy, cw, ch, totals, y_max, (220, 220, 220), thick=2)
        lx = cx + 4
        for label, color in dir_series:
            pygame.draw.rect(self.screen, color, (lx, cy + 4, 10, 10))
            self.screen.blit(self.font_small.render(label, True, COLOR_TEXT), (lx + 13, cy + 3))
            lx += 36
        pygame.draw.rect(self.screen, (220, 220, 220), (lx, cy + 4, 10, 10))
        self.screen.blit(self.font_small.render("Total", True, COLOR_TEXT), (lx + 13, cy + 3))
        if not data:
            m = self.font.render("Start simulation to collect data", True, COLOR_TEXT_DIM)
            self.screen.blit(m, (cx + cw // 2 - m.get_width() // 2, cy + ch // 2))

    def _draw_wait_throughput_chart(self, rect, history):
        data = history[-180:]
        cx, cy, cw, ch = self._chart_bg(
            rect, "Avg Wait (s)  &  Rolling Throughput (cars/min)")
        waits  = [h['avg_wait']           for h in data]
        thrus  = [h.get('rolling_throughput', h['throughput']) for h in data]
        effics = [h.get('efficiency', 0)  for h in data]
        w_max  = max(max(waits,  default=0), 1)
        t_max  = max(max(thrus,  default=0), 1)
        e_max  = max(max(effics, default=0), 0.001)
        self._axes(cx, cy, cw, ch, w_max)
        self._plot(cx, cy, cw, ch, waits,  w_max, COLOR_RED)
        self._plot(cx, cy, cw, ch, [v / t_max * w_max for v in thrus],  w_max, COLOR_GREEN)
        self._plot(cx, cy, cw, ch, [v / e_max * w_max for v in effics], w_max, (200, 120, 220), thick=1)
        # Right-axis labels for rolling throughput
        for i in range(5):
            gy  = cy + int(ch * i / 4)
            lbl = self.font_small.render(f"{t_max * (1 - i / 4):.0f}", True, (80, 200, 100))
            self.screen.blit(lbl, (cx + cw - lbl.get_width() - 2, gy - 7))
        # Legend
        lx = cx + 4
        for color, label in [
            (COLOR_RED,       "Avg Wait ←"),
            (COLOR_GREEN,     "Throughput →"),
            ((200, 120, 220), "Efficiency →"),
        ]:
            pygame.draw.rect(self.screen, color, (lx, cy + 4, 10, 10))
            self.screen.blit(self.font_small.render(label, True, COLOR_TEXT), (lx + 13, cy + 3))
            lx += 100
        if not data:
            m = self.font.render("Start simulation to collect data", True, COLOR_TEXT_DIM)
            self.screen.blit(m, (cx + cw // 2 - m.get_width() // 2, cy + ch // 2))

    def _draw_scenario_bars(self, rect, scenario_results):
        cx, cy, cw, ch = self._chart_bg(
            rect, "Throughput by Scenario & Mode  (cars/min)")
        scenarios = ['Low Traffic', 'Normal Traffic', 'Rush Hour']
        s_short   = ['Low', 'Normal', 'Rush']
        modes     = [('fixed', (90, 140, 220)), ('adaptive', (80, 195, 100))]

        vals  = {(s, m): scenario_results.get((s, m), {}).get('throughput')
                 for s in scenarios for m, _ in modes}
        all_v = [v for v in vals.values() if v is not None]
        y_max = max(max(all_v, default=0) * 1.2, 1)
        self._axes(cx, cy, cw, ch, y_max)

        gw = cw // 3
        bw = max(gw // 3 - 4, 8)
        for gi, (scenario, short) in enumerate(zip(scenarios, s_short)):
            gx = cx + gi * gw + 6
            for bi, (mode, color) in enumerate(modes):
                v  = vals.get((scenario, mode))
                bx = gx + bi * (bw + 4)
                if v is None:
                    pygame.draw.rect(self.screen, (50, 50, 60), (bx, cy + ch - 18, bw, 18))
                    self.screen.blit(
                        self.font_small.render("—", True, COLOR_TEXT_DIM),
                        (bx + bw // 2 - 4, cy + ch - 14))
                else:
                    bh = int(ch * min(v, y_max) / y_max)
                    pygame.draw.rect(self.screen, color, (bx, cy + ch - bh, bw, bh))
                    if bh > 14:
                        self.screen.blit(
                            self.font_small.render(f"{v:.0f}", True, (220, 220, 220)),
                            (bx + 2, cy + ch - bh + 2))
            lbl = self.font_small.render(short, True, COLOR_TEXT_DIM)
            self.screen.blit(lbl, (gx + gw // 2 - lbl.get_width() // 2, cy + ch + 5))

        lx = cx + 4
        for mode, color in modes:
            pygame.draw.rect(self.screen, color, (lx, cy + 4, 10, 10))
            self.screen.blit(self.font_small.render(mode.capitalize(), True, COLOR_TEXT), (lx + 13, cy + 3))
            lx += 75
        if not all_v:
            m = self.font.render(
                "Switch scenarios (1/2/3) & modes (F) to compare", True, COLOR_TEXT_DIM)
            self.screen.blit(m, (cx + cw // 2 - m.get_width() // 2, cy + ch // 2))

    def _draw_comparison_table(self, rect, scenario_results):
        rx, ry, rw, rh = rect
        pygame.draw.rect(self.screen, (30, 30, 38), rect)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, rect, 1)
        self.screen.blit(
            self.font.render("Fixed vs Adaptive — Efficiency Summary", True, COLOR_ACCENT),
            (rx + 8, ry + 6))

        scenarios = ['Low Traffic', 'Normal Traffic', 'Rush Hour']
        s_short   = {'Low Traffic': 'Low', 'Normal Traffic': 'Normal', 'Rush Hour': 'Rush'}
        # (label, key, lower_is_better)
        metrics   = [
            ('Avg Wait',   'avg_wait',   True),
            ('Max Wait',   'max_wait',   True),
            ('Throughput', 'throughput', False),
            ('Efficiency', 'efficiency', False),
        ]
        cols      = [rx + 8, rx + 68, rx + 158, rx + 248, rx + 338, rx + 418]

        ty = ry + 28
        for txt, x in zip(['Scenario', 'Metric', 'Fixed', 'Adaptive', 'Δ', 'Winner'], cols):
            self.screen.blit(self.font_small.render(txt, True, COLOR_ACCENT), (x, ty))
        ty += 16
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (rx + 6, ty), (rx + rw - 6, ty), 1)
        ty += 5

        has_data = False
        for scenario in scenarios:
            fd = scenario_results.get((scenario, 'fixed'),    {})
            ad = scenario_results.get((scenario, 'adaptive'), {})
            for mi, (mlabel, mkey, lower_better) in enumerate(metrics):
                fv, av = fd.get(mkey), ad.get(mkey)
                if mi == 0:
                    self.screen.blit(
                        self.font_small.render(s_short[scenario], True, COLOR_TEXT),
                        (cols[0], ty))
                self.screen.blit(
                    self.font_small.render(mlabel, True, COLOR_TEXT_DIM), (cols[1], ty))

                def fmtv(v, k=mkey):
                    if v is None:
                        return "—"
                    if k in ('avg_wait', 'max_wait'):
                        return f"{v:.1f}s"
                    return f"{v:.2f}"

                self.screen.blit(self.font_small.render(fmtv(fv), True, COLOR_TEXT), (cols[2], ty))
                self.screen.blit(self.font_small.render(fmtv(av), True, COLOR_TEXT), (cols[3], ty))

                if fv is not None and av is not None:
                    has_data   = True
                    delta      = av - fv
                    adap_wins  = (delta < 0) if lower_better else (delta > 0)
                    d_col      = (80, 200, 100) if adap_wins else (220, 100, 100)
                    sign       = '+' if delta > 0 else ''
                    self.screen.blit(
                        self.font_small.render(f"{sign}{delta:.1f}", True, d_col), (cols[4], ty))
                    winner = 'Adaptive' if adap_wins else 'Fixed'
                    self.screen.blit(
                        self.font_small.render(winner, True,
                                               (80, 200, 100) if adap_wins else (220, 180, 80)),
                        (cols[5], ty))
                ty += 18
            pygame.draw.line(self.screen, (45, 45, 55), (rx + 6, ty + 1), (rx + rw - 6, ty + 1), 1)
            ty += 7

        if not scenario_results:
            for i, line in enumerate([
                "Run each scenario (1 / 2 / 3) with both",
                "Fixed and Adaptive (F) modes for ≥ 30 s each,",
                "then press A to view comparisons here.",
            ]):
                m = self.font.render(line, True, COLOR_TEXT_DIM)
                self.screen.blit(m, (rx + rw // 2 - m.get_width() // 2,
                                     ry + rh // 2 - 22 + i * 22))

    def draw_analysis(self, history, scenario_results):
        """Replaces the simulation view with 4-panel results screen."""
        SIM_W = 1000
        pygame.draw.rect(self.screen, (22, 22, 28), (0, 0, SIM_W, WINDOW_HEIGHT))
        pygame.draw.rect(self.screen, (35, 35, 45), (0, 0, SIM_W, 38))
        self.screen.blit(
            self.font_big.render(
                "RESULTS & ANALYSIS   —   press A to return to simulation",
                True, COLOR_ACCENT),
            (10, 8))

        P = 6
        hw = SIM_W // 2 - P
        hh = (WINDOW_HEIGHT - 42) // 2 - P
        y1 = 42 + P
        y2 = 42 + P * 2 + hh

        self._draw_queue_chart(          (P,            y1, hw, hh), history)
        self._draw_wait_throughput_chart ((SIM_W//2 + P, y1, hw, hh), history)
        self._draw_scenario_bars(        (P,            y2, hw, hh), scenario_results)
        self._draw_comparison_table(     (SIM_W//2 + P, y2, hw, hh), scenario_results)


# =====================================================================
# MAIN APP
# =====================================================================

class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.SCALED | pygame.RESIZABLE
        )
        pygame.display.set_caption("Traffic Light Simulation - CS 324")
        self.clock = pygame.time.Clock()
        # Use default fonts to keep it portable
        self.font = pygame.font.SysFont('Arial', 16)
        self.font_small = pygame.font.SysFont('Arial', 12)
        self.font_big = pygame.font.SysFont('Arial', 22, bold=True)
        self.renderer = Renderer(self.screen, self.font,
                                 self.font_small, self.font_big)

        self.scenario = 'Normal Traffic'
        self.control_mode = 'fixed'
        self.speed = 2.0  # simulated seconds per real second
        self.paused = False
        self.history = []  # for CSV export
        self.show_analysis = False
        self.scenario_results = {}  # {(scenario, mode): stats snapshot}

        # Control buttons (placed in the right panel)
        bx, by, bw, bh = 1015, 78, 165, 38
        self.btn_start = Button(
            (bx, by, bw, bh), "START", self.font_big,
            (45, 155, 65), (65, 185, 85),
        )
        self.btn_pause = Button(
            (bx, by, bw, bh), "PAUSE", self.font_big,
            (190, 120, 35), (220, 148, 55),
        )
        self.btn_resume = Button(
            (bx, by, bw, bh), "RESUME", self.font_big,
            (45, 105, 195), (65, 130, 225),
        )

        self.reset()

    def reset(self):
        self.env = simpy.Environment()
        self.intersection = Intersection(
            self.env, control_mode=self.control_mode, scenario=self.scenario
        )
        Vehicle._id_counter = 0
        Pedestrian._id_counter = 0
        self.sim_target = 0.0
        self.history = []
        self.last_sample_time = -1.0
        self.started = False
        self.paused = False

    def _snapshot_scenario(self, stats):
        """Auto-capture the current scenario+mode result once ≥ 30 sim-seconds have run."""
        if self.started and stats['sim_time'] >= 30.0:
            self.scenario_results[(self.scenario, self.control_mode)] = {
                'completed':          stats['completed'],
                'throughput':         stats['throughput'],
                'rolling_throughput': stats['rolling_throughput'],
                'avg_wait':           stats['avg_wait'],
                'max_wait':           stats['max_wait'],
                'efficiency':         stats['efficiency'],
                'sim_time':           stats['sim_time'],
            }

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if not self.started and self.btn_start.is_clicked(pos):
                    self.started = True
                elif self.started and not self.paused and self.btn_pause.is_clicked(pos):
                    self.paused = True
                elif self.started and self.paused and self.btn_resume.is_clicked(pos):
                    self.paused = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE and self.started:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_1:
                    self.scenario = 'Low Traffic'
                    self.reset()
                elif event.key == pygame.K_2:
                    self.scenario = 'Normal Traffic'
                    self.reset()
                elif event.key == pygame.K_3:
                    self.scenario = 'Rush Hour'
                    self.reset()
                elif event.key == pygame.K_f:
                    self.control_mode = (
                        'adaptive' if self.control_mode == 'fixed' else 'fixed'
                    )
                    self.reset()
                elif event.key == pygame.K_UP:
                    self.speed = min(self.speed + 0.5, 10.0)
                elif event.key == pygame.K_DOWN:
                    self.speed = max(self.speed - 0.5, 0.5)
                elif event.key == pygame.K_a:
                    self.show_analysis = not self.show_analysis
                elif event.key == pygame.K_s:
                    self.save_csv()
        return True

    def save_csv(self):
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"results/sim_{self.scenario.replace(' ', '_')}_{self.control_mode}_{timestamp}.csv"
        with open(fname, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow([
                'sim_time', 'completed', 'total_queued',
                'avg_wait', 'max_wait',
                'throughput_per_min', 'rolling_throughput_per_min', 'efficiency',
                'queue_N', 'queue_S', 'queue_E', 'queue_W',
            ])
            for row in self.history:
                w.writerow([
                    f"{row['sim_time']:.2f}", row['completed'],
                    row['total_queued'],
                    f"{row['avg_wait']:.3f}", f"{row['max_wait']:.3f}",
                    f"{row['throughput']:.3f}",
                    f"{row.get('rolling_throughput', row['throughput']):.3f}",
                    f"{row.get('efficiency', 0):.4f}",
                    row['queues']['N'], row['queues']['S'],
                    row['queues']['E'], row['queues']['W'],
                ])
        print(f"[Saved] {fname}")

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            dt = self.clock.tick(FPS) / 1000.0
            if self.started and not self.paused:
                # Accumulate sim target independently so early events are reachable
                self.sim_target += dt * self.speed
                while self.env.peek() <= self.sim_target:
                    self.env.step()

            stats = self.intersection.stats()
            # Sample history every simulated second
            if stats['sim_time'] - self.last_sample_time >= 1.0:
                self.history.append(stats.copy())
                self.last_sample_time = stats['sim_time']
            # Auto-capture scenario result once enough data is available
            self._snapshot_scenario(stats)

            # ── Render ──
            peds = self.intersection.active_pedestrians
            sim_state = {
                'scenario': self.scenario,
                'mode': self.control_mode,
                'speed': self.speed,
                'peds_waiting':  sum(1 for p in peds if p.state == 'waiting'),
                'peds_crossing': sum(1 for p in peds if p.state == 'crossing'),
                **stats,
            }

            if self.show_analysis:
                self.renderer.draw_analysis(self.history, self.scenario_results)
            else:
                self.screen.fill(COLOR_BG)
                self.renderer.draw_roads()
                self.renderer.draw_crosswalks()
                self.renderer.draw_lights(self.intersection.controller)
                self.renderer.draw_vehicles(self.intersection)
                self.renderer.draw_pedestrians(self.intersection)

            self.renderer.draw_panel(sim_state)
            # Control button
            if not self.started:
                self.btn_start.draw(self.screen)
            elif self.paused:
                self.btn_resume.draw(self.screen)
            else:
                self.btn_pause.draw(self.screen)
            if self.paused and not self.show_analysis:
                self.renderer.draw_pause_overlay()
            pygame.display.flip()

        pygame.quit()


if __name__ == '__main__':
    App().run()
