#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Direction, Stop
from pybricks.tools import wait
import random
import math

# Initialize hardware
ev3 = EV3Brick()
left_motor = Motor(Port.B, positive_direction=Direction.COUNTERCLOCKWISE)
right_motor = Motor(Port.C, positive_direction=Direction.COUNTERCLOCKWISE)
sensor = UltrasonicSensor(Port.S4)

# PSO Parameters
num_particles = 5
particles = []
inertia = 0.8
c1 = 1.5  # cognitive coefficient
c2 = 1.5  # social coefficient
max_velocity = 1.0

# Map (0 = free, 1 = obstacle)
grid = [
    [0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0]
]

# Position and orientation
robot_pos = [0, 0]
robot_dir = [0, -1]  # North
goal = [4, 4]

# Physical grid size (in mm)
CELL_SIZE = 200
OBSTACLE_THRESHOLD = 150  # distance in mm to detect obstacles

# Directions (N, S, E, W)
directions = {
    (0, -1): "N",
    (0, 1): "S",
    (1, 0): "E",
    (-1, 0): "W"
}

class Particle:
    def __init__(self):
        self.position = [robot_pos[0], robot_pos[1]]
        self.velocity = [random.uniform(-1, 1), random.uniform(-1, 1)]
        self.best_position = self.position[:]
        self.best_score = float('inf')
        
    def update_velocity(self, global_best):
        for i in range(2):
            r1 = random.random()
            r2 = random.random()
            cognitive = c1 * r1 * (self.best_position[i] - self.position[i])
            social = c2 * r2 * (global_best[i] - self.position[i])
            self.velocity[i] = inertia * self.velocity[i] + cognitive + social
            # Limit velocity
            self.velocity[i] = max(-max_velocity, min(max_velocity, self.velocity[i]))
    
    def update_position(self):
        # Convert continuous to discrete movement
        dx = 1 if self.velocity[0] > 0.5 else -1 if self.velocity[0] < -0.5 else 0
        dy = 1 if self.velocity[1] > 0.5 else -1 if self.velocity[1] < -0.5 else 0
        
        new_pos = [self.position[0] + dx, self.position[1] + dy]
        if is_valid(new_pos):
            self.position = new_pos
            return True
        return False

def is_valid(pos):
    x, y = pos
    return 0 <= x < 5 and 0 <= y < 5 and grid[y][x] == 0

def update_grid_with_sensor():
    dist = sensor.distance()
    if dist < OBSTACLE_THRESHOLD:
        # Calculate position in front of robot
        front_x = robot_pos[0] + robot_dir[0]
        front_y = robot_pos[1] + robot_dir[1]
        if 0 <= front_x < 5 and 0 <= front_y < 5:
            grid[front_y][front_x] = 1
            return True
    return False

def euclidean_distance(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx*dx + dy*dy)

def calculate_fitness(position):
    # Distance to target + obstacle penalty
    distance = euclidean_distance(position, goal)
    if not is_valid(position):
        distance += 10  # Strong penalty for invalid position
    return distance

def move_to(direction):
    current = tuple(robot_dir)
    target = direction
    
    if current == target:
        forward()
        return
    
    # Calculate required turn
    dirs = list(directions.keys())
    current_idx = dirs.index(current)
    target_idx = dirs.index(target)
    
    diff = (target_idx - current_idx) % 4
    
    if diff == 1:
        turn_right()
    elif diff == 2:
        turn_around()
    elif diff == 3:
        turn_left()
    
    forward()

def forward():
    left_motor.run_angle(900, 360, wait=True)
    right_motor.run_angle(900, 360, wait=True)

def turn_left():
    left_motor.run_angle(200, -180, wait=True)
    right_motor.run_angle(200, 180, wait=True)
    # Update robot direction (90° left rotation)
    robot_dir[0], robot_dir[1] = robot_dir[1], -robot_dir[0]

def turn_right():
    left_motor.run_angle(200, 180, wait=True)
    right_motor.run_angle(200, -180, wait=True)
    # Update robot direction (90° right rotation)
    robot_dir[0], robot_dir[1] = -robot_dir[1], robot_dir[0]

def turn_around():
    turn_left()
    turn_left()

# Initialize particles
for _ in range(num_particles):
    particles.append(Particle())

# Main loop
for step in range(100):
    ev3.screen.clear()
    ev3.screen.print("Step:" + str(step))
    ev3.screen.print("Pos:" + str(robot_pos))
    
    # Update map with sensor
    if update_grid_with_sensor():
        ev3.screen.print("Obstacle detected!")
    
    # Check if goal reached
    if robot_pos[0] == goal[0] and robot_pos[1] == goal[1]:
        ev3.screen.print("Goal reached!")
        break
    
    # Execute PSO
    global_best = None
    global_best_score = float('inf')
    
    # Update particles
    for p in particles:
        p.update_velocity(goal)
        p.update_position()
        
        # Evaluate fitness
        score = calculate_fitness(p.position)
        if score < p.best_score:
            p.best_score = score
            p.best_position = p.position[:]
        
        if score < global_best_score:
            global_best_score = score
            global_best = p.position[:]
    
    # Move robot toward best global position
    if global_best:
        # Calculate required direction
        dx = global_best[0] - robot_pos[0]
        dy = global_best[1] - robot_pos[1]
        
        # Normalize direction
        if dx != 0: 
            dx = dx // abs(dx)
        if dy != 0: 
            dy = dy // abs(dy)
        
        target_dir = (dx, dy)
        if target_dir not in directions:
            target_dir = tuple(robot_dir)
        
        new_pos = [robot_pos[0] + dx, robot_pos[1] + dy]
        if is_valid(new_pos):
            move_to(target_dir)
            robot_pos[0] = new_pos[0]
            robot_pos[1] = new_pos[1]
    
    wait(500)

ev3.screen.print("Execution completed")
