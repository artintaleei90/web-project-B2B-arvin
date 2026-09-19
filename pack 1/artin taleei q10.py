import sys
from controller import Robot
from controller import Receiver
from controller import Emitter
import math

timeStep = 16

robot = Robot()

speed_right = robot.getDevice("wheel1 motor")
speed_left = robot.getDevice("wheel2 motor")

encoder_right = robot.getDevice("wheel1 sensor")
encoder_left = robot.getDevice("wheel2 sensor")

speed_right.setPosition(float("inf"))
speed_left.setPosition(float("inf"))

LIDAR = robot.getDevice("lidar")
LIDAR.enable(timeStep)
LIDAR.enablePointCloud()

rangeImage = []


def get_lidar_data():
    global rangeImage
    rangeImage = [x * 100 for x in LIDAR.getRangeImage()]


def get_front_lidar():
    left_values = []
    right_values = []
    front_values = []
    
    for i in range(950, 1000):
        if math.isfinite(rangeImage[i]):
            left_values.append(rangeImage[i])
    for i in range(1000, 1049):
        if math.isfinite(rangeImage[i]):
            front_values.append(rangeImage[i])
    for i in range(1049, 1099):
        if math.isfinite(rangeImage[i]):
            right_values.append(rangeImage[i])


    left = min(left_values) if left_values else 999
    front = min(front_values) if front_values else 999
    right = min(right_values) if right_values else 999

    return left, front, right


def drive():
    left_distance, front_distance, right_distance = get_front_lidar()

    base_speed = 6.0
    max_speed = 6.28
    turn_distance = 20
    danger_distance = 8

    left_speed = base_speed
    right_speed = base_speed

    if front_distance > turn_distance:
        left_speed = base_speed
        right_speed = base_speed

    elif front_distance > danger_distance:
        if left_distance < right_distance:
            turn = min((right_distance - left_distance) * 0.08, 1.5)
            left_speed = base_speed + turn
            right_speed = base_speed - turn
        else:
            turn = min((left_distance - right_distance) * 0.08, 1.5)
            left_speed = base_speed - turn
            right_speed = base_speed + turn

    else:
        if right_distance < danger_distance and left_distance > danger_distance:
            left_speed = 2.0
            right_speed = 6.28

        elif left_distance < danger_distance and right_distance > danger_distance:
            left_speed = 6.28
            right_speed = 2.0

        elif left_distance < danger_distance and right_distance < danger_distance:
            left_speed = -6.28
            right_speed = 6.28

        elif left_distance > right_distance:
            left_speed = 2.0
            right_speed = 6.28

        else:
            left_speed = 6.28
            right_speed = 2.0

    left_speed = max(-max_speed, min(max_speed, left_speed))
    right_speed = max(-max_speed, min(max_speed, right_speed))

    speed_left.setVelocity(left_speed)
    speed_right.setVelocity(right_speed)


state = "check"
start = robot.getTime()

while robot.step(timeStep) != -1:
    get_lidar_data()
    drive()