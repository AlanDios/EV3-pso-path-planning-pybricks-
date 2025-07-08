#!/usr/bin/env python3

# link for the simulator
# https://fll-pigeons.github.io/gamechangers/simulator/public/

# Import the necessary libraries
import math
import time
from pybricks.ev3devices import *
from pybricks.parameters import *
from pybricks.robotics import *
from pybricks.tools import wait
from pybricks.hubs import EV3Brick

ev3 = EV3Brick()
motorA = Motor(Port.A)
motorB = Motor(Port.B)
left_motor = motorA
right_motor = motorB

robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=152)
robot.settings(straight_speed=200, straight_acceleration=100, turn_rate=100)


color_sensor_in1 = ColorSensor(Port.S1)
obstacle_sensor = UltrasonicSensor(Port.S2)
gyro_sensor= GyroSensor(Port.S3)

motorC = Motor(Port.C) # Magnet

# Here is where your code start
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

move(90)
