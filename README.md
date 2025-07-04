# EV3 PSO Path Planning Robot

![Robot in Action](assets/demo.gif)

## Overview
This project implements a Particle Swarm Optimization (PSO) algorithm for autonomous path planning using LEGO Mindstorms EV3. The robot navigates a grid environment from (0,0) to (4,4) while avoiding obstacles using sensor data.

## Features
- Real-time path planning with PSO
- Dynamic obstacle detection and mapping
- Position tracking through odometry
- Visual feedback on EV3 screen

## Hardware Setup
- LEGO EV3 Brick
- 2 Large Motors (Ports B and C)
- Ultrasonic Sensor (Port 4)
- Differential drive chassis

```mermaid
graph LR
    A[EV3 Brick] --> B[Ultrasonic Sensor]
    A --> C[Motor B]
    A --> D[Motor C]
