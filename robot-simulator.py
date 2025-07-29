#!/usr/bin/env python3

# Import the necessary libraries
import time
from pybricks.ev3devices import *
from pybricks.parameters import *
from pybricks.robotics import *
from pybricks.tools import wait
from pybricks.hubs import EV3Brick

# --- ROBOT INITIALIZATION AND CONFIGURATION ---
ev3 = EV3Brick()
motorA = Motor(Port.A)
motorB = Motor(Port.B)
left_motor = motorA
right_motor = motorB
color_sensor = ColorSensor(Port.S1)
obstacle_sensor = UltrasonicSensor(Port.S2)
gyro_sensor = GyroSensor(Port.S3)
motorC = Motor(Port.C) 

robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=152)

# Define the speed as a constant for easy access and modification
MOVEMENT_SPEED = 200
LENGTH_BLOCKS = 20 # cm
robot.settings(straight_speed=MOVEMENT_SPEED, straight_acceleration=100, turn_rate=100)

# --- MOVEMENT AND DETECTION FUNCTION ---

def move(distance_cm):
    """
    Move the robot to the front or back, depends the value of distance_cm.

    :param distance_cm: The distance whit robot need moving in cm
    """
    print(f"Moving {distance_cm} cm...")
    
    # Convert cm to mm, because driver use mm
    distancia_mm = distance_cm * 10

    robot.straight(distancia_mm)
    robot.stop()
    
    print("Movimento concluído!")
    ev3.speaker.beep()

def move_and_detect_colors(distance_cm):
    """
    Moves the robot forward while detecting and counting colored tapes.
    """
    # List of target colors for your tapes.
    # In Pybricks, colors are represented by numbers.
    # e.g., 1: Color.BLACK, 2: Color.BLUE, 3: Color.GREEN
    # But, i'dont know whi, us robot identify the green tape as 2
    allowed_colors = [1, 2, 3]
    detected_colors = [0, 0, 0]
    previous_color = 0
    
    print(f"Starting movement of {distance_cm} cm and looking for: {allowed_colors}")

    robot.reset()
    target_distance_mm = ((distance_cm + (LENGTH_BLOCKS/2)) + 10) * 10

    robot.drive(MOVEMENT_SPEED, 0) # 0 for the turn rate, to move in a straight line.

    while robot.distance() < target_distance_mm:
        current_color = color_sensor.color()
        
        if current_color != previous_color:
            previous_color = current_color
            if current_color in allowed_colors:
                print(f"Detected color: {current_color}")
                idxColor = allowed_colors.index(current_color)
                detected_colors[idxColor] += 1


    print(f"Detected color counts: {detected_colors}")
    robot.stop()
    print("\nMovement complete.")
    
    # Now, the function not return, because it is in construction
    # return len(detected_tapes), detected_tapes


# --- MAIN EXECUTION BLOCK ---

move_and_detect_colors(40)
