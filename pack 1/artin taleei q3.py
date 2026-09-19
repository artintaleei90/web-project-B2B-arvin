import sys
sys.path.append("C:\Program Files\Webots\lib\controller\python")
from controller import Robot
from controller import Receiver
from controller import Emitter
import networkx as nx
import keyboard
import math
import cv2 as cv
import numpy as np
import time
import heapq as hp
import struct
from collections import deque
from PIL import Image
from torchvision import transforms
import torch
from ultralytics import YOLO


MAP_SIZE = 8400
TILE_SIZE = 3
GRID_SIZE = 0.1
ARRAY_SIZE = round(MAP_SIZE // (TILE_SIZE / GRID_SIZE)) #Starting Point: (140, 140)
timeStep = 16
max_velocity = 6.28
first_time = 1
up = MAP_SIZE - 1
down = 0
right = 0
left = MAP_SIZE - 1
next_x = 0
next_y = 0
danger_hole=0
end = True
Map = np.zeros((MAP_SIZE, MAP_SIZE), dtype=np.uint8)
Map_Bonus = np.zeros((MAP_SIZE, MAP_SIZE), dtype=np.uint8)
Map_Obstacle = np.zeros((MAP_SIZE, MAP_SIZE), dtype=np.uint8)
Tile_array = np.zeros((ARRAY_SIZE, ARRAY_SIZE), dtype=np.uint8)
Colored_tile_array = np.zeros((ARRAY_SIZE, ARRAY_SIZE), dtype=np.uint8)
Room_tile_array = np.zeros((ARRAY_SIZE, ARRAY_SIZE), dtype=np.uint8)


color_array = np.full((8400, 8400, 3), (192, 192, 192), dtype=np.uint8)

stride = 0.1
first_time_delay = True
first_Time = 0
G = nx.Graph()
key_detect_lop = False
robot_radius = 3.7
robot = Robot()
first_time1 = True
target_list = []
swamp_target_list = []
secondary_target_list = []
gone_secondary_targets = []
my_node = (ARRAY_SIZE//2, ARRAY_SIZE//2)
list_x = []
list_y = []
list_z = []
refx = 0
refy = 0
refz = 0
ref_list_x = []
ref_list_y = []
ref_list_z = []
order = 3
gps_list_x = deque([], maxlen=order)
gps_list_y = deque([], maxlen=order)
gps_list_z = deque([], maxlen=order)
gps_filtered_x = deque([], maxlen=order)
gps_filtered_y = deque([], maxlen=order)
gps_filtered_z = deque([], maxlen=order)
x_motion_model = 0
y_motion_model = 0
x_CF = 0
y_CF = 0
time1 = 0
time2 = 0
time_killer_counter = 0


rotation_yaw = 0
rotation_key = True

exit_key = False

move_key = True
move_back_key = True
detect_room_key_blue = True

Ivejustreported_right = False
Ivejustreported_left = False
Ivejustreported_front = False

mapping_in_colored_tile = False

reportation_angle_right = 0
reportation_angle_left = 0
reportation_angle_front = 0


live_mean = 0
live_sum = 0
loop_counter = 0
time_left_counter=0
Time_left = 3600


state = "choose"
previous_state_victim = "choose"
room = 1
planned_path = []
local_target = (0, 0)
global_target = ()
node_local_target = (ARRAY_SIZE // 2, ARRAY_SIZE // 2)

Key_LOP = True
LoP_happend_key = False

swamp_list = []
checkpoint_list = []
blue_list = []
purple_list = []
orange_list = []
red_list = []
green_list = []
yellow_list = []
color = []
counter_blue = []
counter_green = []
counter_yellow = []
counter_purple = []
counter_orange = []
counter_red = []
victim_pos_list = []
victim_off=[]
recent_visited_tiles = []
recent_visited_nodes = []
recent_size = 4

key_stuck = True
stuck_counter = 0
x_previous_robot_detect_stuck = 0
y_previous_robot_detect_stuck = 0
victim_cam_l = "h"
victim_cam_r = "h"
victim_cam_f = "h"



time_left = 3600
time_key = False
Time_left_real = 3600
time_left_real = 3600
time_left_key = False
time_left_counter=0
Time_left = 3600
time_left_real


report_map_bonus_key = False
got_lop_in_this_loop = False
report_map_bonus_counter = 0
check_region_counter = 0
hole_check_region_counter = 0

previous_x_ = 0
previous_y_ = 0

previous_encoder_l = 0
previous_encoder_r = 0

loop_cnt = 0

csv_filename = r"C:\Users\Lenovo\Desktop\Our Data\flattened_arrays.csv"


# _______VISION PARAMS_______#
# MODEL_PATH = r"D:\Danesh sim maze(8)\erebus-25.0.1-25.0.1\player_controllers\vic_classifier_v1_2.h5" #Artin
# MODEL_PATH = r"C:\Users\AsusIran\OneDrive\Desktop\vision2026\vic_classifier_v1.h5" #Amirsam
# MODEL_PATH = r"C:\Users\fomo\Desktop\erebus-25.0.1-25.0.1\player_controllers\vic_classifier_v1_2.h5"
# MODEL_PATH = r"C:\Users\EMTOO\Downloads\vic_classifier_v1.h5" #Radin v1
# MODEL_PATH = r"D:\python code\YOLO\data_6\runs\pose\runs\marker_pose\yolov8n-pose\weights\best.engine"
# MODEL_PATH = r"D:\danesh school sim maze(9)\erebus - 26.01\player_controllers\best.engine"
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# model = YOLO(MODEL_PATH, task="pose")

MAX_ASPECT_RATIO = 2.2

MinArea = 85
MaxArea = 1100

IMAGE_WIDTH = 18
IMAGE_HEIGHT = 18

# CONFIDENCE_THRESHOLD = 0.98
CONFIDENCE_THRESHOLD = 0.90
# CONFIDENCE_THRESHOLD_MATRIX = [0.97, 0.95, 0.96, 0.90, 0.98, 0.97, 0.97]

FRAME_LIMIT = 1
FRAME_LIMIT_COUNTER = 0
FRAME_LIMIT_COUNTER_LEFT = 0
FRAME_LIMIT_COUNTER_FRONT = 0
FRAME_LIMIT_COUNTER_RIGHT = 0

vision_res_right = None
vision_res_left = None


speed_right = robot.getDevice("wheel1 motor")
speed_left = robot.getDevice("wheel2 motor")

encoder_right = robot.getDevice("wheel1 sensor")
encoder_left = robot.getDevice("wheel2 sensor")

speed_right.setPosition(float("inf"))
speed_left.setPosition(float("inf"))

IMU = robot.getDevice("inertial_unit")
GPS = robot.getDevice("gps")
RCAM = robot.getDevice("camera_right")
LCAM = robot.getDevice("camera_left")
FCAM = robot.getDevice("camera_front")
LIDAR = robot.getDevice("lidar")
VL = robot.getDevice("distance_sensor")
receiver = robot.getDevice("receiver")
emitter = robot.getDevice("emitter")

IMU.enable(timeStep)
GPS.enable(timeStep)
RCAM.enable(timeStep)
LCAM.enable(timeStep)
FCAM.enable(timeStep)
LIDAR.enable(timeStep)
LIDAR.enablePointCloud()
VL.enable(timeStep)
encoder_left.enable(timeStep)
encoder_right.enable(timeStep)
receiver.enable(timeStep)

CHECK_REGION_RADIUS = 3.5
GO_TO_XY_ARRIVAL_RANGE = 0.5
START_GPS_NUMBER_OF_LOOPS = 200
LIDAR_NAVIGATION_RANGE = 8
LIDAR_MAP_BONUS_RANGE = 70
LIDAR_ROOM4_COLORED_TILE_RANGE = 6.5
NEAR_12CM_CENTER_THRESHOLD = 3.5


# base_tf = transforms.Compose([
#     transforms.ToTensor(),
#     transforms.Normalize(mean=[0.5], std=[0.5])
# ])

# base_tf_obstacle = transforms.Compose([
#     transforms.ToTensor()
# ])

# MODEL_PATH_CURVE = r"D:\danesh school sim maze(9)\erebus - 26.01\player_controllers\Best_curve_model.pt"
# curved_wall_mapping_model = torch.jit.load(MODEL_PATH_CURVE, map_location=device)
# curved_wall_mapping_model.eval()

# MODEL_PATH_OBSTACLE = r"D:\danesh school sim maze(9)\erebus - 26.01\player_controllers\Final_Obstacle_Model_Day_2.pt"
# obstacle_mapping_model = torch.jit.load(MODEL_PATH_OBSTACLE, map_location="cpu")
# obstacle_mapping_model.eval()



def remote_control(my_speed = max_velocity):
    if keyboard.is_pressed('w'):
        sr = my_speed
        sl = my_speed
    elif keyboard.is_pressed('s'):
        sr = -my_speed
        sl = -my_speed
    elif keyboard.is_pressed('d'):
        sr = -my_speed
        sl = my_speed
    elif keyboard.is_pressed('a'):
        sr = my_speed
        sl = -my_speed
    elif keyboard.is_pressed('e'):
        sr = 0
        sl = 0

    else:
        sr = 0
        sl = 0

    speed_right.setVelocity(sr)
    speed_left.setVelocity(sl)

def low_pass_filter():
    global gps_filtered_x, gps_filtered_y, gps_filtered_z, gps_x, gps_y, gps_z

    # Fc = 2.75Hz, Fs = 60Hz
    # b0 = 0.01714660
    # b1 = 0.03429319
    # b2 = 0.01714660

    # a1 = -1.59692944
    # a2 = 0.66551583

    # Fc = 20Hz, Fs = 250Hz
    b0 = 0.04613180
    b1 = 0.09226360
    b2 = 0.04613180

    a1 = -1.30728503
    a2 = 0.49181224

    # Fc = 7Hz, Fs = 60Hz
    # b0 = 0.08717908
    # b1 = 0.17435817
    # b2 = 0.08717908

    # a1 = -1.00892162
    # a2 = 0.35763796

    # Mean
    # b = 1.0 / order
    # a = 0.0

    # temp_x = b * sum(gps_list_x)
    # temp_y = b * sum(gps_list_y)
    # temp_z = b * sum(gps_list_z)


    temp_x = (b0 * gps_list_x[-1]) + (b1 * gps_list_x[-2]) + (b2 * gps_list_x[-3]) - (a1 * gps_filtered_x[-1]) - (a2 * gps_filtered_x[-2])
    gps_filtered_x.append(temp_x)
    temp_y = (b0 * gps_list_y[-1]) + (b1 * gps_list_y[-2]) + (b2 * gps_list_y[-3]) - (a1 * gps_filtered_y[-1]) - (a2 * gps_filtered_y[-2])
    gps_filtered_y.append(temp_y)
    temp_z = (b0 * gps_list_z[-1]) + (b1 * gps_list_z[-2]) + (b2 * gps_list_z[-3]) - (a1 * gps_filtered_z[-1]) - (a2 * gps_filtered_z[-2])
    gps_filtered_z.append(temp_z)

    gps_x = temp_x
    gps_y = temp_y
    gps_z = temp_z

    # # # # # # ##### # print(gps_list_x)

def start_gps():
    iiiix = 0
    iiiiy = 0
    iiiiz = 0
    sum_x = 0
    sum_y = 0
    sum_z = 0
    global startz, startx, starty
    for i in range(START_GPS_NUMBER_OF_LOOPS):
        list_x.append(GPS.getValues()[2] * 100)
        list_y.append(GPS.getValues()[0] * 100)
        list_z.append(GPS.getValues()[1] * 100)
        robot.step(timeStep)

    for iiiix in list_x :
        sum_x = sum_x + iiiix

    startx = sum_x / len(list_x)
    for iiiiy in list_y :
        sum_y = sum_y + iiiiy

    starty = sum_y / len(list_y)
    for iiiiz in list_z :
        sum_z = sum_z + iiiiz

    startz = sum_z / len(list_z)

def get_gps_data():
    global gps_z, gps_y, gps_x, gps_list_z, gps_list_y, gps_list_x, x_motion_model, y_motion_model
    # gps_z = GPS.getValues()[1] * 100 - startz
    # gps_list_z.append(gps_z)
    # gps_y = GPS.getValues()[0] * 100 - starty
    # gps_list_y.append(gps_y)
    # gps_x = GPS.getValues()[2] * 100 - startx
    # gps_list_x.append(gps_x)
    # low_pass_filter()

    motion_model()
    gps_x = x_motion_model
    gps_y = y_motion_model

def refresh_GPS(count=START_GPS_NUMBER_OF_LOOPS):
    global refz, refx, refy
    stop()
    iiiix = 0
    iiiiy = 0
    iiiiz = 0
    sum_x = 0
    sum_y = 0
    sum_z = 0

    ref_list_x = []
    ref_list_y = []
    ref_list_z = []

    for i in range(count):
        ref_list_x.append(GPS.getValues()[2] * 100)
        ref_list_y.append(GPS.getValues()[0] * 100)
        ref_list_z.append(GPS.getValues()[1] * 100)
        robot.step(timeStep)

    for iiiix in ref_list_x :
        sum_x = sum_x + iiiix
    refx = sum_x / len(ref_list_x)

    for iiiiy in ref_list_y :
        sum_y = sum_y + iiiiy
    refy = sum_y / len(ref_list_y)

    for iiiiz in ref_list_z :
        sum_z = sum_z + iiiiz
    refz = sum_z / len(ref_list_z)

    return refx, refy, refz

def motion_model(alpha = 0.0):
    global x_motion_model, y_motion_model, time1, previous_encoder_l, previous_encoder_r

    delta_t = robot.getTime() - time1

    delta_x = (GPS.getSpeedVector()[2] * 100) * delta_t
    delta_y = (GPS.getSpeedVector()[0] * 100) * delta_t

    x_motion_model += delta_x
    y_motion_model += delta_y

    time1 = robot.getTime()

def complementary_filter(alpha):
    global x_CF, y_CF

    x_CF = alpha * (x_motion_model) + (1 - alpha) * (gps_filtered_x[-1])
    # gps_filtered_x.append(x_CF)

    y_CF = alpha * (y_motion_model) + (1 - alpha) * (gps_filtered_y[-1])
    # gps_filtered_y.append(y_CF)

def get_lidar_data():
    # 1024 : front - 1152: right - 1280: back - 1408: left
    global rangeImage
    rangeImage = LIDAR.getRangeImage()
    rangeImage = [x * 100 for x in rangeImage]

def get_vl_data():
    global distance_sensor
    distance_sensor = VL.getValue() * 100

def get_camera_data():
    global frame_r,frame_l,frame_f


    # RCAM.setExposure(100)
    # FCAM.setExposure(100)
    # LCAM.setExposure(100)

    image_r=RCAM.getImage()
    image_l=LCAM.getImage()
    image_f=FCAM.getImage()
    image_r=np.frombuffer(image_r, np.uint8).reshape((RCAM.getHeight(), RCAM.getWidth(), 4))
    image_l=np.frombuffer(image_l, np.uint8).reshape((LCAM.getHeight(), LCAM.getWidth(), 4))
    image_f=np.frombuffer(image_f, np.uint8).reshape((FCAM.getHeight(), FCAM.getWidth(), 4))
    frame_r=cv.cvtColor(image_r,cv.COLOR_BGRA2BGR)
    frame_l=cv.cvtColor(image_l,cv.COLOR_BGRA2BGR)
    frame_f=cv.cvtColor(image_f,cv.COLOR_BGRA2BGR)

def get_IMU_data():
    global yaw , pitch , roll
    yaw = math.degrees(IMU.getRollPitchYaw()[2]) + 180
    pitch = math.degrees(IMU.getRollPitchYaw()[1]) + 180
    roll = math.degrees(IMU.getRollPitchYaw()[0]) + 180

def get_left_time():
    global time_left_counter, time_left, state, report_map_bonus_key ,Time_left, time_left_key , Time_left_real , time_left_real

    time_left_counter+=1

    if time_left <= 40 or time_left_real <= 40:
        time_left_key = True
        time_left_counter = 101
        if ((time_left <= 7) and (not report_map_bonus_key)) or ((time_left_real <= 12) and (not report_map_bonus_key)):
            # state = "report map bonus"
            state = "exit"
            report_map_bonus_key = True


    if time_left_counter >= 100:
        time_left_key = True
        _temp_time = Time_left
        _temp_time_real = Time_left_real

        if (_temp_time != None) and (_temp_time_real != None):
            time_left = _temp_time
            time_left_real = _temp_time_real
            time_left_counter = 0

def update_data():
    global got_lop_in_this_loop
    get_IMU_data()
    get_vl_data()
    get_camera_data()
    get_gps_data()
    get_lidar_data()
    get_left_time()

def update_world(obs):
    global up, down, right, left
    if obs[0] < up:
        up = obs[0]
    elif obs[0] > down:
        down = obs[0]
    if obs[1] > right:
        right = obs[1]
    elif obs[1] < left:
        left = obs[1]

def localToGlobal(theta, obstacle_coordinate):
    x2 = (math.cos(theta) * obstacle_coordinate[0]) - (math.sin(theta) * obstacle_coordinate[1])
    y2 = (math.sin(theta) * obstacle_coordinate[0]) + (math.cos(theta) * obstacle_coordinate[1])
    a = x2 + gps_x
    b = y2 + gps_y
    return a, b

def lidar(alpha):
    global Map, Map_Bonus
    alpha = math.radians(alpha)
    if (not LoP_happend_key) and (not key_detect_lop):
        if not(mapping_in_colored_tile):
            mapping_max_range = LIDAR_MAP_BONUS_RANGE
        else:
            mapping_max_range = LIDAR_ROOM4_COLORED_TILE_RANGE
        for i in range(1024, 1535):
            d = rangeImage[i]
            if not math.isinf(d) and d < mapping_max_range and d > 3.7:
                d = d * math.cos( (0.2 / 3.0) / 2 )
                theta = ((1024 - i) * (360.0 / 512.0)) - 0.3515625 - (0.3515625 / 2.0)
                rad = math.radians(theta)
                x1 = d * math.cos(rad)
                y1 = d * math.sin(rad)
                a, b = localToGlobal(alpha, [x1, y1])
                wall_list = [round((MAP_SIZE/2)+(a/GRID_SIZE)), round((MAP_SIZE/2)+(b/GRID_SIZE))]
                if (room == 4) and (Map_Bonus[wall_list[0], wall_list[1]] != 255):
                    Map_Bonus[wall_list[0], wall_list[1]] = 128
                else:
                    if d <= 13:
                        Map_Bonus[wall_list[0], wall_list[1]] = 255
                    else:
                        if (Map_Bonus[wall_list[0], wall_list[1]] != 128):
                            Map_Bonus[wall_list[0], wall_list[1]] = 255

                update_world(wall_list)

            if not math.isinf(d) and d < LIDAR_NAVIGATION_RANGE and d > 3.7:
                d = d * math.cos( (0.2 / 3.0) / 2)
                theta = ((1024 - i) * (360.0 / 512.0)) - 0.3515625 - (0.3515625 / 2.0)
                rad = math.radians(theta)
                x1 = d * math.cos(rad)
                y1 = d * math.sin(rad)
                a, b = localToGlobal(alpha, [x1, y1])
                wall_list = [round((MAP_SIZE/2)+(a/GRID_SIZE)), round((MAP_SIZE/2)+(b/GRID_SIZE))]
                Map[wall_list[0], wall_list[1]] = 255


            if not math.isinf(d) and d < 30 and d > 3.7:
                d = d * math.cos( (0.2 / 3.0) / 2)
                theta = ((1024 - i) * (360.0 / 512.0)) - 0.3515625 - (0.3515625 / 2.0)
                rad = math.radians(theta)
                x1 = d * math.cos(rad)
                y1 = d * math.sin(rad)
                a, b = localToGlobal(alpha, [x1, y1])
                wall_list = [round((MAP_SIZE/2)+(a/GRID_SIZE)), round((MAP_SIZE/2)+(b/GRID_SIZE))]
                color_array[wall_list[0], wall_list[1]] = (139,127,61)

def turn_to_angle(target):

    if abs(target-yaw)<=180 and target>=yaw:
        error=target-yaw
    elif abs(target-yaw)>180 and target>=yaw:
        error=target-yaw-360
    elif abs(target-yaw)<=180 and target<yaw:
        error=target-yaw
    else:
        error=target-yaw+360

    kp=0.5
    sr=kp*error
    sl=-1*(kp*error)
    sr=filter_speed(sr)
    sl=filter_speed(sl)

    speed_left.setVelocity(sl)
    speed_right.setVelocity(sr)

def rotation(angle):
    global yaw, rotation_key, rotation_yaw
    if rotation_key:
        rotation_yaw = yaw
        rotation_key = False

    target = rotation_yaw + angle
    if target >= 360:
        target = target - 360
    elif target < 0:
        target = target + 360
    turn_to_angle(target)
    if (abs(yaw - target) < 0.05):
        return True
    else:
        return False

def get_distance(x1, y1, x2, y2):
    # return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return (x2 - x1)**2 + (y2 - y1)**2

def go_to_xy(target_position):  # C = vatar, beta = wanted angel
    x_2, y_2 = target_position[0], target_position[1]

    x_1 = gps_x
    y_1 = gps_y
    C = math.sqrt((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2)
    if x_1 >= x_2 and y_1 >= y_2:
        beta = 270 - math.degrees(math.asin((x_1 - x_2) / C))
    elif x_1 <= x_2 and y_1 >= y_2:
        beta = 360 - math.degrees(math.asin((y_1 - y_2) / C))
    elif x_1 <= x_2 and y_1 <= y_2:
        beta = math.degrees(math.asin((y_2 - y_1) / C))
    elif x_1 >= x_2 and y_1 <= y_2 :
        beta = 180 - math.degrees(math.asin((y_2 - y_1) / C))

    #Error calculating

    if abs(beta - yaw) <= 180 and beta >= yaw:
        error = beta - yaw
    elif abs(beta - yaw) > 180 and beta >= yaw:
        error = beta - yaw - 360
    elif abs(beta-yaw) <= 180 and beta < yaw:
        error = beta - yaw
    else:
        error = beta - yaw + 360

    kp = 0.9
    sr = max_velocity + kp * error
    sl = max_velocity - kp * error
    sr = filter_speed(sr)
    sl = filter_speed(sl)
    speed_right.setVelocity(sr)
    speed_left.setVelocity(sl)
    if math.sqrt((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) < GO_TO_XY_ARRIVAL_RANGE:
        return True
    return False

def go_to_xy_backward(target_position):  # C = vatar, beta = wanted angel
    x_2, y_2 = target_position[0], target_position[1]

    x_1 = gps_x
    y_1 = gps_y
    C = math.sqrt((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2)
    if x_1 >= x_2 and y_1 >= y_2:
        beta = 270 - math.degrees(math.asin((x_1 - x_2) / C))
    elif x_1 <= x_2 and y_1 >= y_2:
        beta = 360 - math.degrees(math.asin((y_1 - y_2) / C))
    elif x_1 <= x_2 and y_1 <= y_2:
        beta = math.degrees(math.asin((y_2 - y_1) / C))
    elif x_1 >= x_2 and y_1 <= y_2 :
        beta = 180 - math.degrees(math.asin((y_2 - y_1) / C))

    beta += 180
    #Error calculating

    if abs(beta - yaw) <= 180 and beta >= yaw:
        error = beta - yaw
    elif abs(beta - yaw) > 180 and beta >= yaw:
        error = beta - yaw - 360
    elif abs(beta-yaw) <= 180 and beta < yaw:
        error = beta - yaw
    else:
        error = beta - yaw + 360


    kp = 0.8
    sr = -max_velocity + kp * error
    sl = -max_velocity - kp * error
    sr = filter_speed(sr)
    sl = filter_speed(sl)

    speed_right.setVelocity(sr)
    speed_left.setVelocity(sl)
    if math.sqrt((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) < 0.5:
        return True
    return False

def move(distance):
    global move_key, saved_gps_move
    if move_key:
        move_key = False
        saved_gps_move = (gps_x, gps_y)
    else:
        error = distance - math.sqrt((gps_x - saved_gps_move[0]) ** 2 + (gps_y - saved_gps_move[1]) ** 2)
        kp = 5
        sr = error * kp
        sl = error * kp


        sr = filter_speed(sr)
        sl = filter_speed(sl)

        speed_right.setVelocity(sr)
        speed_left.setVelocity(sl)

        if abs(error) < 0.0001:
            return True
        else:
            return False

def move_back(distance):
    global move_back_key, saved_gps_move_back
    if move_back_key:
        move_back_key = False
        saved_gps_move_back = (gps_x, gps_y)
    else:
        error = distance - math.sqrt((gps_x - saved_gps_move_back[0]) ** 2 + (gps_y - saved_gps_move_back[1]) ** 2)
        kp = 5
        sr = error * kp
        sl = error * kp


        sr = filter_speed(sr)
        sl = filter_speed(sl)

        speed_right.setVelocity(-sr)
        speed_left.setVelocity(-sl)

        if abs(error) < 0.0001:
            return True
        else:
            return False

def filter_speed(myspeed):
    if myspeed > max_velocity:
        myspeed = max_velocity
    elif myspeed < -max_velocity :
        myspeed = -max_velocity
    return myspeed

def stop():
    speed_left.setVelocity(0)
    speed_right.setVelocity(0)

def gps_to_tile(gps_cordinate):
    tile_x = round(gps_cordinate[0] / TILE_SIZE + ARRAY_SIZE / 2)
    tile_y = round(gps_cordinate[1] / TILE_SIZE + ARRAY_SIZE / 2)
    tile_position = (tile_x, tile_y)
    return tile_position

def tile_to_gps(tile_position):
    gx = (tile_position[0] - ARRAY_SIZE / 2) * TILE_SIZE
    gy = (tile_position[1] - ARRAY_SIZE / 2) * TILE_SIZE
    tile_gps = (gx, gy)
    return tile_gps

def gps_to_map(gps_cordinate):
    map_x_index = round(gps_cordinate[0] / GRID_SIZE + MAP_SIZE / 2)
    map_y_index = round(gps_cordinate[1] / GRID_SIZE + MAP_SIZE / 2)
    map_index = (map_x_index, map_y_index)
    return map_index

def map_to_gps(map_index):
    gps_x_cordinate = (map_index[0] - MAP_SIZE // 2) * GRID_SIZE
    gps_y_cordinate = (map_index[1] - MAP_SIZE // 2) * GRID_SIZE
    gps_co = (gps_x_cordinate, gps_y_cordinate)
    return gps_co

def tile_to_map(tile_position):
    tile_map = gps_to_map(tile_to_gps(tile_position))
    return tile_map

def map_to_tile(map_index):
    tile_position = gps_to_tile(map_to_gps(map_index))
    return tile_position

def check_region(center, R=3.72):
    global check_region_counter, hole_check_region_counter
    check_region_counter = 0
    hole_check_region_counter = 0
    # center is in Map space
    for i in range(center[0] - round(R / GRID_SIZE), center[0] + round(R / GRID_SIZE)):
        for j in range(center[1] - round(R / GRID_SIZE), center[1] + round(R / GRID_SIZE)):
            distance = math.sqrt((center[0] - i) ** 2 + (center[1] - j) ** 2) * GRID_SIZE
            if distance > R:
                continue

            # if Map[i][j] != 0:
            #     return False

            if Map[i][j] == 200:
                hole_check_region_counter += 1
            if Map[i][j] == 255:
                check_region_counter += 1

            if check_region_counter > 1 :
                return False
            if hole_check_region_counter > 5 :
                return False

    return True

def way_check_region(pos_1, pos_2, crs=1, R=3.72):
    global Map

    if (pos_1[0] - pos_2[0]) == 0:
        for i in range(min(pos_1[1], pos_2[1]), max(pos_1[1], pos_2[1]), crs):
            if not check_region((pos_1[0], i), R):
                return False


    else:
        alpha = (pos_2[1] - pos_1[1]) / (pos_2[0] - pos_1[0])
        beta = pos_1[1] - alpha * pos_1[0]

        for i in range(min(pos_1[0], pos_2[0]), max(pos_1[0], pos_2[0]), crs):
            temp_x = i
            temp_y = round(alpha * temp_x + beta)
            if not check_region((temp_x, temp_y), R):
                return False


        for i in range(min(pos_1[1], pos_2[1]), max(pos_1[1], pos_2[1]), crs):
            temp_y = i
            temp_x = round((temp_y - beta) / alpha)
            if not check_region((temp_x, temp_y), R):
                return False

    return True

def A_star(Start, End):
    if type(End[0]) == float or type(End[1]) == float:
        if not check_region(gps_to_map(End), CHECK_REGION_RADIUS):
            ## # ## # # # # ##### # print("in first if")
            return []

    else :
        if not check_region(tile_to_map(End), CHECK_REGION_RADIUS):
            ## # ## # # # # ##### # print("in second if")
            return []

    if Start == End:
        return [Start]

    def heuristic(a, b):
        if detect_space(a) == "Tile" and detect_space(b) == "Tile":
            a_prime = tile_to_gps(a)
            b_prime = tile_to_gps(b)
            return get_distance(a_prime[0], a_prime[1], b_prime[0], b_prime[1])
        if detect_space(a) == "GPS" and detect_space(b) == "Tile":
            a_prime = a
            b_prime = tile_to_gps(b)
            return get_distance(a_prime[0], a_prime[1], b_prime[0], b_prime[1])
        if detect_space(a) == "Tile" and detect_space(b) == "GPS":
            a_prime = tile_to_gps(a)
            b_prime = b
            return get_distance(a_prime[0], a_prime[1], b_prime[0], b_prime[1])
        if detect_space(a) == "GPS" and detect_space(b) == "GPS":
            a_prime = a
            b_prime = b
            return get_distance(a_prime[0], a_prime[1], b_prime[0], b_prime[1])
    try:
        path = nx.astar_path(G, Start, End, heuristic=heuristic, weight='weight')
        # ## # ## # # # # ##### # print("trying")

        if path:
            # ## # ## # # # # ##### # print("full")
            pass

    except:
        ## # ## # # # # ##### # print("I cant find a way")
        path = []
        # ## # ## # # # # ##### # print("I can not")

    # path = path.reverse()

    path.reverse()
    path = path[:-1]
    # ## # ## # # # # ##### # print(path)
    return path

def detect_space(pos):
    if type(pos[0]) == int or type(pos[1]) == int :
        return "Tile"
    else:
        return "GPS"

# def A_star(Start, End):
#     open_set = []
#     closed_set = []
#     previous = {}
#     g_value = {Start : 0}
#     f_value = {Start : math.sqrt( (Start[0] - End[0]) ** 2 + (Start[1] - End[1]) ** 2 )}
#     path = []

#     hp.heappush(open_set, (0, Start))
#     counter = 0
#     if detect_space(End) == "GPS":
#         if not check_region(gps_to_map(End), CHECK_REGION_RADIUS):
#             # ## # ## # # # # ##### # print("in first if")
#             return []

#     else :
#         if not check_region(tile_to_map(End), CHECK_REGION_RADIUS):
#             # ## # ## # # # # ##### # print("in second if")
#             return []

#     if Start == End:
#         return [Start]

#     while open_set:
#         # # ## # ## # # # # ##### # print("_______", counter,"==============")
#         counter += 1
#         if counter > 10000 :
#             return []
#         current = hp.heappop(open_set)[1]
#         closed_set.append(current)

#         if current == End:
#             while current != Start:
#                 path.append(current)
#                 current = previous[current]
#             return path

#         # for (i, j) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
#         for neighbor in list(G.neighbors(current)):
#             # if neighbor[0] == 396:
#             #     # ## # ## # # # # ##### # print("neighbor: ", neighbor)
#             #     # ## # ## # # # # ##### # print("check region neighbor: ", check_region(tile_to_map(neighbor)))
#             if detect_space(neighbor) == "Tile":

#                 if Tile_array[neighbor[0]][neighbor[1]] == 2:
#                     # if neighbor[0] == 396:
#                     #     # ## # ## # # # # ##### # print("is hole")
#                     continue
#                 if neighbor[0] < 0 or neighbor[0] > ARRAY_SIZE-1 or neighbor[1] < 0 or neighbor[1] > ARRAY_SIZE-1:
#                     # if neighbor[0] == 396:
#                     #     # ## # ## # # # # ##### # print("out of boundaries")
#                     continue
#                 if (not check_region(tile_to_map(neighbor), CHECK_REGION_RADIUS)) or (neighbor in closed_set):
#                     # if neighbor[0] == 396:
#                     #     # ## # ## # # # # ##### # print("not walkable or in closed set")
#                     continue

#             else:
#                 if Tile_array[gps_to_tile(neighbor)[0]][gps_to_tile(neighbor)[1]] == 2:
#                     # if neighbor[0] == 396:
#                     #     # ## # ## # # # # ##### # print("is hole")
#                     continue
#                 if gps_to_tile(neighbor)[0] < 0 or gps_to_tile(neighbor)[0] > ARRAY_SIZE-1 or gps_to_tile(neighbor)[1] < 0 or gps_to_tile(neighbor)[1] > ARRAY_SIZE-1:
#                     # if neighbor[0] == 396:
#                     #     # ## # ## # # # # ##### # print("out of boundaries")
#                     continue
#                 if (not check_region(gps_to_map(neighbor), CHECK_REGION_RADIUS)) or (neighbor in closed_set):
#                     # if neighbor[0] == 396:
#                     #     # ## # ## # # # # ##### # print("not walkable or in closed set")
#                     continue




#             temp_g_cost = g_value[current] + G[current][neighbor]["weight"]


#             if (neighbor not in [k[1] for k in open_set]) or (temp_g_cost < g_value[neighbor]):
#                 f_cost = temp_g_cost + math.sqrt((neighbor[0] - End[0]) ** 2 + (neighbor[1] - End[1]) ** 2)
#                 f_value[neighbor] = f_cost
#                 g_value[neighbor] = temp_g_cost
#                 previous[neighbor] = current
#                 if neighbor not in [k[1] for k in open_set]:
#                     hp.heappush(open_set, (f_cost, neighbor))

#     return path

# # def A_star(Start, End):
#     counter = 0
#     # ## # ## # # # # ##### # print("Start: ", Start, "    End: ", End)
#     # ## # ## # # # # ##### # print("Check Region Start: ", check_region(tile_to_map(Start)))
#     if not check_region(tile_to_map(End), CHECK_REGION_RADIUS):
#         # ## # ## # # # # ##### # print("End is not reachable")
#         return []
#     if Start == End:
#         # target_list.remove(global_target)
#         # ## # ## # # # # ##### # print("Start == End")
#         return [Start]

#     open_set = []
#     closed_set = []
#     previous = {}
#     g_value = {Start : 0}
#     f_value = {Start : math.sqrt( (Start[0] - End[0]) ** 2 + (Start[1] - End[1]) ** 2 )}
#     path = []

#     hp.heappush(open_set, (0, Start))

#     # if math.sqrt( (gps_x - tile_to_gps(End)[0])**2 + (gps_y - tile_to_gps(End)[1])**2 ) > 0.5 and math.sqrt( (gps_x - tile_to_gps(End)[0])**2 + (gps_y - tile_to_gps(End)[1])**2 ) < 3.5:
#     #     path.append(Start)
#     #     return path


#     while open_set:
#         # ## # ## # # # # ##### # print("_______", counter,"==============")
#         counter += 1
#         if counter > 10000 :
#             return []
#         current = hp.heappop(open_set)[1]
#         closed_set.append(current)

#         if current == End:
#             while current != Start:
#                 path.append(current)
#                 current = previous[current]
#             return path

#         # for (i, j) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
#         for (i, j) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1)]:
#             neighbor = (current[0] + i, current[1] + j)
#             # if neighbor[0] == 396:
#             #     ## # ## # # # # ##### # print("neighbor: ", neighbor)
#             #     ## # ## # # # # ##### # print("check region neighbor: ", check_region(tile_to_map(neighbor)))

#             if Tile_array[neighbor[0]][neighbor[1]] == 2:
#                 # if neighbor[0] == 396:
#                 #     ## # ## # # # # ##### # print("is hole")
#                 continue

#             if neighbor[0] < 0 or neighbor[0] > ARRAY_SIZE-1 or neighbor[1] < 0 or neighbor[1] > ARRAY_SIZE-1:
#                 # if neighbor[0] == 396:
#                 #     ## # ## # # # # ##### # print("out of boundaries")
#                 continue

#             if (not check_region(tile_to_map(neighbor), CHECK_REGION_RADIUS)) or (neighbor in closed_set):
#                 # if neighbor[0] == 396:
#                 #     ## # ## # # # # ##### # print("not walkable or in closed set")
#                 continue

#             if abs(i) - abs(j) == 0:
#                 temp_g_cost = g_value[current] + 1.4
#             else:
#                 temp_g_cost = g_value[current] + 1

#             if (neighbor not in [k[1] for k in open_set]) or (temp_g_cost < g_value[neighbor]):
#                 f_cost = temp_g_cost + math.sqrt((neighbor[0] - End[0]) ** 2 + (neighbor[1] - End[1]) ** 2)
#                 f_value[neighbor] = f_cost
#                 g_value[neighbor] = temp_g_cost
#                 previous[neighbor] = current
#                 if neighbor not in [k[1] for k in open_set]:
#                     hp.heappush(open_set, (f_cost, neighbor))

#     return path

def detect_LOP():
    global Key_LOP, got_lop_in_this_loop
    if receiver.getQueueLength() > 0:
        receivedData = receiver.getBytes()
        if len(receivedData) == 1:
            tup = struct.unpack('c', receivedData)
            if tup[0].decode("utf-8") == 'L':
                got_lop_in_this_loop = True
                receiver.nextPacket()
                if Key_LOP:
                    Key_LOP = False
                    return True
    return False

def LOP():
    # ## # ## # # # # ##### # print(" +++++++++++++++++++++++ IN LOP FUNCTION +++++++++++++++++++++++")
    global Key_LOP, state, planned_path, target_list, recent_visited_tiles, recent_visited_nodes, local_target, LoP_happend_key, my_node , key_detect_lop, room, Room_tile_array, gps_x, gps_y, gps_z, startx, starty, startz, x_motion_model, y_motion_model
    # # ##### # print("key: ", key_detect_lop)
    # ## # ## # # # # ##### # print("LOP KEY ==> ", LoP_happend_key,"\t","MY NODE ==> ", my_node)
    # ## # ## # # # # ##### # print("RECENT VISITED TILE ==> ", recent_visited_tiles, "\n", "RECENT VISITED NODE ==> ", recent_visited_nodes)
    # ## # ## # # # # ##### # print("LOCS =======> ", (X_Tile, Y_Tile))
    # ## # ## # # # # ##### # print("CHECKPOINT LIST ========> ", checkpoint_list)

    if key_detect_lop:
        # # ##### # print(" I DETECTED LoP")
        if target_list:
            # target_list.pop() # think more
            if local_target in target_list:
                target_list.remove(local_target)
            else:
                ## # ## # # # # ##### # print("local target was not in target list")
                pass
        recent_visited_tiles = []
        recent_visited_nodes = []
        LoP_happend_key = True
        key_detect_lop = False

        # # ##### # print("IN LOP HAPPEND")
        # # ##### # print("starts: ", startx, '\t', starty)
        gps_x, gps_y, gps_z = refresh_GPS()
        gps_x, gps_y, gps_z = gps_x - startx, gps_y - starty, gps_z - startz
        gps_x = tile_to_gps(gps_to_tile((gps_x, gps_y)))[0]
        gps_y = tile_to_gps(gps_to_tile((gps_x, gps_y)))[1]
        x_motion_model = gps_x
        y_motion_model = gps_y

        # # ##### # print("gps: ", gps_x, '\t', gps_y)

        X_Tile, Y_Tile = gps_to_tile((gps_x, gps_y))
        # # ##### # print("TILE: ", X_Tile, '\t', Y_Tile)
        for i in range(recent_size):
            # ## # ## # # # # ##### # print("________________ I AM IN SECOND FOR ________________")
            recent_visited_tiles.append((X_Tile, Y_Tile))
            recent_visited_nodes.append((X_Tile, Y_Tile))
        # # ##### # print("recent tiles: ", recent_visited_tiles)
        my_node = (X_Tile, Y_Tile)
        # # ##### # print("my node: ", my_node)
        append_targets()
        append_nodes()
        LoP_happend_key = False
        if Room_tile_array[X_Tile][Y_Tile] != 0:
            room = Room_tile_array[X_Tile][Y_Tile]
            # ## # # # # ##### # print("room changed")
        else:
            for (i, j) in [(1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]:
                if Room_tile_array[X_Tile + i][Y_Tile + j] != 0:
                    room = Room_tile_array[X_Tile + i][Y_Tile + j]
                    # ## # # # # ##### # print("room changed in for")
                    break

        # # ##### # print("room: ", room)
        state = 'choose'
        planned_path = []

def detect_stuck():
    global key_stuck, stuck_counter, x_previous_robot_detect_stuck, y_previous_robot_detect_stuck
    if key_stuck:
        x_previous_robot_detect_stuck = gps_x
        y_previous_robot_detect_stuck = gps_y
        key_stuck = False
    if abs(x_previous_robot_detect_stuck - gps_x) < 0.5 and abs(y_previous_robot_detect_stuck - gps_y) < 0.5:
        stuck_counter += 1
    else:
        stuck_counter = 0
        key_stuck = True

    if stuck_counter > 50:
        stuck_counter = 0
        key_stuck = True
        return True
    return False

def append_targets():
    global state, G, target_list, swamp_target_list
    tile_x, tile_y = gps_to_tile((gps_x, gps_y))
    # for (i, j) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
    for (i, j) in [(1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]:
        neighbor = (tile_x + i, tile_y + j)
        if check_region(tile_to_map(neighbor), CHECK_REGION_RADIUS) and Tile_array[neighbor[0]][neighbor[1]] != 1 and Tile_array[neighbor[0]][neighbor[1]] != 2:
            if neighbor not in target_list:
                # ## # ## # # # # ##### # print("neighbor: ", neighbor)
                if type(my_node[0]) == int or type(my_node[1]) == int:
                    _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], tile_to_gps(neighbor)[0], tile_to_gps(neighbor)[1])
                else :
                    _w = get_distance(my_node[0], my_node[1], tile_to_gps(neighbor)[0], tile_to_gps(neighbor)[1])
                if (my_node in swamp_list) and (neighbor in swamp_list):
                    G.add_edge(my_node, neighbor, weight = _w * 7.5)
                else:
                    G.add_edge(my_node, neighbor, weight = _w)
                if (neighbor in swamp_list) and (check_region(tile_to_map(neighbor), 7.0)):
                    ##### # print("Yes: ", neighbor)
                    # target_list = [neighbor] + target_list
                    if neighbor not in swamp_target_list:
                        swamp_target_list.append(neighbor)
                else:
                    # # ##### # print("No")
                    target_list.append(neighbor)



        #_______________________________________

        if i == 1 and j == 1 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x + 0, tile_y + 1))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x + 0, tile_y + 1))[0]  + ii * stride, tile_to_gps((tile_x + 0, tile_y + 1))[1] + 0)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break

        #______________________________________

        if i == 0 and j == 1 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x - 1, tile_y + 1))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x - 1, tile_y + 1))[0]  + ii * stride, tile_to_gps((tile_x - 1, tile_y + 1))[1] + 0)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break


        #______________________________________

        if i == -1 and j == 1 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x - 1, tile_y + 0))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x - 1, tile_y + 0))[0] + 0, tile_to_gps((tile_x - 1, tile_y + 0))[1] + ii * stride)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break


        #______________________________________

        if i == -1 and j == 0 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x - 1, tile_y - 1))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x - 1, tile_y - 1))[0] + 0, tile_to_gps((tile_x - 1, tile_y - 1))[1] + ii * stride)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break


        #______________________________________

        if i == -1 and j == -1 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x + 0, tile_y - 1))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x - 1, tile_y - 1))[0] + ii * stride, tile_to_gps((tile_x - 1, tile_y - 1))[1] + 0)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break


        #______________________________________

        if i == 0 and j == -1 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x + 1, tile_y - 1))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x + 0, tile_y - 1))[0] + ii * stride, tile_to_gps((tile_x + 0, tile_y - 1))[1] + 0)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break

        #______________________________________

        if i == 1 and j == -1 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x + 1, tile_y + 0))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x + 1, tile_y - 1))[0] + 0, tile_to_gps((tile_x + 1, tile_y - 1))[1] + ii * stride)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break

        #______________________________________

        if i == 1 and j == 0 and not check_region(tile_to_map(neighbor)):
            if not check_region(tile_to_map((tile_x + 1, tile_y + 1))):
                for ii in range(int(TILE_SIZE / stride)):
                    temp_gps = (tile_to_gps((tile_x + 1, tile_y + 0))[0] + 0, tile_to_gps((tile_x + 1, tile_y + 0))[1] + ii * stride)
                    # temp_gps = round(temp_gps, 2)
                    temp_map = gps_to_map(temp_gps)
                    if check_region(temp_map):
                        if temp_gps not in secondary_target_list:
                            if not ((temp_gps in target_list) or (temp_gps in gone_secondary_targets)):
                                if not is_near(temp_gps):
                                    target_list.append(temp_gps)
                                    secondary_target_list.append(temp_gps)

                                    G.add_node(temp_gps)
                                    if type(my_node[0]) == int or type(my_node[1]) == int:
                                        _w = get_distance(tile_to_gps(my_node)[0], tile_to_gps(my_node)[1], temp_gps[0], temp_gps[1])
                                    else :
                                        _w = get_distance(my_node[0], my_node[1], temp_gps[0], temp_gps[1])
                                    G.add_edge(my_node, temp_gps, weight = _w)
                                    # state = "secondaryTarget"
                                    break

def append_nodes():
    global state, G
    if type(my_node[0]) == int or type(my_node[1]) == int:
        tile_x, tile_y = gps_to_tile((gps_x, gps_y))
        # for (i, j) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
        for (i, j) in [(1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]:
            neighbor = (tile_x + i, tile_y + j)
            if check_region(tile_to_map(neighbor), CHECK_REGION_RADIUS) and Tile_array[neighbor[0]][neighbor[1]] != 2:
                if (my_node in swamp_list) and (neighbor in swamp_list):
                    G.add_edge(my_node, neighbor, weight = 7.5 * 9 * get_distance(tile_x, tile_y, neighbor[0], neighbor[1]))
                else:
                    G.add_edge(my_node, neighbor, weight = 9 * get_distance(tile_x, tile_y, neighbor[0], neighbor[1]))
                # # print("Edge added: ", my_node, "  To: ", neighbor)

def detect_color(_cam='f', _row=39, _col=16):
    if _cam == 'f':
        res = frame_f[_row][_col]
        return res
    elif _cam == 'l':
        res_left = frame_l[_row][_col]
        return res_left
    elif _cam == 'r':
        res_right = frame_r[_row][_col]
        return res_right
    else:
        #### # print("IN ELSE detect_color!!")
        res = frame_f[_row][_col]
        return res

def what_tile_is_it(a = 36, b = 16, cam = "f"):
    global swamp_list, checkpoint_list, blue_list, purple_list, orange_list, red_list, green_list, yellow_list

    result = 'normal'

    # Calibrated with Color sensor:

    # if color[0] > 200 and color[0] < 230 and color[1] > 167 and color[1] < 200 and color[2] > 96 and color[2] < 120: #swamp
    #     result = 'swamp'

    # elif color[0] > 35 and color[0] < 100 and color[1] > 40 and color[1] < 100 and color[2] > 54 and color[2] < 112: #checkpoint
    #     result = 'checkpoint'

    # elif abs(color[0] - color[1]) <= 4 and color[1] < 80 and color[2] > 220: #blue
    #     result = 'blue'

    # elif color[0] > 33 and color[0] < 42 and color[1] > 240 and color[1] < 255 and color[2] > 32 and color[2] < 43 and abs(color[0] - color[2]) <= 4: #green
    #     result = 'green'

    # elif color[0] > 159 and color[0] < 165 and color[1] > 70 and color[1] < 76 and color[2] > 236 and color[2] < 241: #purple
    #     result = 'purple'

    # elif color[0] > 248 and color[0] < 255 and color[1] > 70 and color[1] < 76 and color[2] > 70 and color[2] < 76: #red
    #     result = 'red'

    # elif color[0] > 250 and color[0] < 255 and color[1] > 248 and color[1] < 255 and color[2] > 69 and color[2] < 76: #yellow
    #     result = 'yellow'

    # elif color[0] > 250 and color[0] < 255 and color[1] > 235 and color[1] < 242 and color[2] > 69 and color[2] < 76 : #orange
    #     result = 'orange'

    #---------------------------------------------------------------------------------------------------------------------------------------------------------------

    # Calibrated with camera:
    if cam == "f":
        color = cv.cvtColor(frame_f, cv.COLOR_BGR2RGB)[a][b]
    elif cam == "l":
        color = cv.cvtColor(frame_l, cv.COLOR_BGR2RGB)[a][b]
    else:
        color = cv.cvtColor(frame_r, cv.COLOR_BGR2RGB)[a][b]

    if (color[0] > 160 and color[0] < 220 and color[1] > 130 and color[1] < 150 and color[2] > 70 and color[2] < 90) and (color[0] - color[1] < 40): #swamp
        result = 'swamp'

    elif (color[1] - color[0]) < 10 and (color[1] - color[0]) > 2 and (color[2] - color[1]) > 10 and (color[2] - color[1]) < 20: #checkpoint
        # [138  93  76]
        result = 'checkpoint'

    elif (color[0] > 40 and color[0] < 50 and color[1] > 40 and color[1] < 50 and color[2] > 220 and color[2] < 240) and abs(color[0] - color[1]) < 5: #blue
        result = 'blue'

    elif color[0] > 20 and color[0] < 30 and color[1] > 220 and color[1] < 240 and color[2] > 20 and color[2] < 30 and abs(color[0] - color[2]) < 5: #green
        result = 'green'

    elif color[0] > 100 and color[0] < 115 and color[1] > 40 and color[1] < 55 and color[2] > 180 and color[2] < 190: #purple
        result = 'purple'

    elif color[0] > 225 and color[0] < 240 and color[1] > 40 and color[1] < 50 and color[2] > 40 and color[2] < 50 and abs(color[1] - color[2]) < 5: #red
        result = 'red'

    elif color[0] > 225 and color[0] < 245 and color[1] > 225 and color[1] < 245 and color[2] > 40 and color[2] < 55 : #yellow
        result = 'yellow'

    elif color[0] > 225 and color[0] < 240 and color[1] > 180 and color[1] < 190 and color[2] > 40 and color[2] < 55: #orange
        result = 'orange'

    return result

def detect_hole_pixel(_cam='f', _row=36, _col=16):
    if np.array_equal(detect_color(_cam, _row, _col), [30, 30 ,30]) or np.array_equal(detect_color(_cam, _row, _col), [10, 10 ,10]) or np.array_equal(detect_color(_cam, _row, _col), [24, 24 ,24]):
        return True
    else:
        return False

def hole_processing(calibrated_value_x, calibrated_value_y, _rangeImage_index):
    global state, Tile_array, up, down, right, left, Colored_tile_array, Room_tile_array, Map
    hole_gps = localToGlobal(math.radians(yaw), (calibrated_value_x, calibrated_value_y))
    hole_pos = gps_to_tile(hole_gps)
    hole_map = tile_to_map(hole_pos)

    if rangeImage[_rangeImage_index] > 0.02 + math.sqrt((calibrated_value_x ** 2) + (calibrated_value_y ** 2)):
        if hole_map[0] < up:
            up = hole_map[0]
        elif hole_map[0] > down:
            down = hole_map[0]
        if hole_map[1] > right:
            right = hole_map[1]
        elif hole_map[1] < left:
            left = hole_map[1]
        if hole_pos in target_list:
            target_list.remove(hole_pos)
        if Tile_array[hole_pos[0]][hole_pos[1]] != 2:
            if (hole_pos[0] % 4 == 0) and (hole_pos[1] % 4 == 0):
                if room == 4:
                    Room_tile_array[hole_pos[0]][hole_pos[1]] = 4
                cv.rectangle(Map, (hole_map[1] - 60, hole_map[0] - 60), (hole_map[1] + 60, hole_map[0] + 60), 200, -1)
                cv.rectangle(color_array, (hole_map[1] - 60, hole_map[0] - 60), (hole_map[1] + 60, hole_map[0] + 60), (30, 30 ,30), -1)
                for (ii, jj) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
                    Tile_array[hole_pos[0] + ii][hole_pos[1] + jj] = 2
                    Colored_tile_array[hole_pos[0] + ii][hole_pos[1] + jj] = 2
                    for (_iii, _jjj) in [(0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0)]: #TODO: Maybe second layer should be included
                        lt = gps_to_tile(local_target)
                        # # ## # # # # ##### # print("??: ", (hole_pos[0] + ii + _iii, hole_pos[1] + jj + _jjj), lt)
                        if (hole_pos[0] + ii + _iii, hole_pos[1] + jj + _jjj) == lt:
                            if lt in target_list:
                                target_list.remove(lt)
                            # # ## # # # # ##### # print("state to avoid hole")
                            state = "avoid hole"
                    if (hole_pos[0] + ii, hole_pos[1] + jj) in target_list:
                        target_list.remove((hole_pos[0] + ii, hole_pos[1] + jj))
                        state = "avoid hole"
                    if ((hole_pos[0] + ii, hole_pos[1] + jj) in planned_path) or ((hole_pos[0] + ii, hole_pos[1] + jj) == local_target) or ((hole_pos[0] + ii, hole_pos[1] + jj) == global_target):
                        state = "avoid hole"
            if (hole_pos in planned_path) or (hole_pos == gps_to_tile(local_target)) or (hole_pos == global_target):
                state = "avoid hole"
            Tile_array[hole_pos[0]][hole_pos[1]] = 2
            Colored_tile_array[hole_pos[0]][hole_pos[1]] = 2
            if not check_region(gps_to_map(local_target)):
                state = "avoid hole"
            irregular_tiles_correction(hole_pos, "hole")
            lt = gps_to_tile(local_target)
            if Tile_array[lt[0]][lt[1]] == 2:
                state = "avoid hole"

        Map[hole_map[0]][hole_map[1]] = 200

def hole():
    global state, Tile_array, up, down, right, left
#___________________________________________________________________________________
    if detect_hole_pixel('f', 36, 16):
        hole_processing(5.40, 0, 1024)

#______________________________________________________________________________________
    if detect_hole_pixel('f', 29, 16):
        hole_processing(6.839, 0, 1024)

#___________________________________________________________________________________
    if detect_hole_pixel('f', 20, 16):
        hole_processing(9.980, 0, 1024)

#___________________________________________________________________________________
    if detect_hole_pixel('f', 15, 16):
        hole_processing(13.09456, 0, 1024)



#___________________________________________________________________________________
    if detect_hole_pixel('r', 36, 16):
        hole_processing(0, -5.42, 1152)

#______________________________________________________________________________________
    if detect_hole_pixel('r', 29, 16):
        hole_processing(0, -6.856, 1152)

#___________________________________________________________________________________
    if detect_hole_pixel('r', 20, 16):
        hole_processing(0, -9.992, 1152)

#___________________________________________________________________________________
    if detect_hole_pixel('r', 15, 16):
        hole_processing(0, -13.0993, 1152)



#______________________________________________________________________________________
    if detect_hole_pixel('l', 36, 16):
        hole_processing(0, 5.27, 1408)

#______________________________________________________________________________________
    if detect_hole_pixel('l', 29, 16):
        hole_processing(0, 6.884, 1408)

#______________________________________________________________________________________
    if detect_hole_pixel('l', 20, 16):
        hole_processing(0, 10.044, 1408)

#______________________________________________________________________________________
    if detect_hole_pixel('l', 15, 16):
        hole_processing(0, 13.1876, 1408)



def irregular_tiles_correction(_pos, _color):
    global Colored_tile_array, blue_list, green_list, red_list, orange_list, purple_list, yellow_list, checkpoint_list, swamp_list, Map, Tile_array

    A_dic = {"blue": 5,
             "green": 6,
             "red": 7,
             "orange": 8,
             "purple": 9,
             "yellow": 10,
             "checkpoint": 3,
             "swamp": 4,
             "hole": 2}

    # B_dic = {5: "blue",
    #          6: "green",
    #          7: "red",
    #          8: "orange",
    #          9: "purple",
    #          10: "yellow",
    #          3: "checkpoint",
    #          4: "swamp",
    #          2: "hole"}

    if not ((_pos[0] % 4 == 2) or (_pos[1] % 4 == 2)):
        if (_pos[0] % 4 == 1) and (_pos[1] % 4 == 1):
            _Center = (_pos[0] - 1, _pos[1] - 1)
        elif (_pos[0] % 4 == 1) and (_pos[1] % 4 == 0):
            _Center = (_pos[0] - 1, _pos[1])
        elif (_pos[0] % 4 == 1) and (_pos[1] % 4 == 3):
            _Center = (_pos[0] - 1, _pos[1] + 1)
        elif (_pos[0] % 4 == 0) and (_pos[1] % 4 == 3):
            _Center = (_pos[0], _pos[1] + 1)
        elif (_pos[0] % 4 == 3) and (_pos[1] % 4 == 3):
            _Center = (_pos[0] + 1, _pos[1] + 1)
        elif (_pos[0] % 4 == 3) and (_pos[1] % 4 == 0):
            _Center = (_pos[0] + 1, _pos[1])
        elif (_pos[0] % 4 == 3) and (_pos[1] % 4 == 1):
            _Center = (_pos[0] + 1, _pos[1] - 1)
        elif (_pos[0] % 4 == 0) and (_pos[1] % 4 == 1):
            _Center = (_pos[0], _pos[1] - 1)
        elif (_pos[0] % 4 == 0) and (_pos[1] % 4 == 0):
            _Center = (_pos[0], _pos[1])
        else:
            ## # ## # # # # ##### # print("Wierd Error!!!!")
            pass


        _temp_counter = 0
        for i,j in [(0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
            _temp_pos = (_Center[0] + i, _Center[1] + j)
            if Colored_tile_array[_temp_pos[0]][_temp_pos[1]] == A_dic[_color]:
                _temp_counter += 1

        ## # ## # # # # ##### # print("_pos: ", _pos, "       _color: ", _color, "       _temp_counter: ", _temp_counter, "      _Center: ", _Center)

        if _temp_counter >= 3:
            ## # ## # # # # ##### # print("CORRECTION----------------------------------------------------------")
            if _color == "blue":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 5
                    if _temp not in blue_list:
                        blue_list.append(_temp)

            elif _color == "green":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 6
                    if _temp not in green_list:
                        green_list.append(_temp)

            elif _color == "red":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 7
                    if _temp not in red_list:
                        red_list.append(_temp)

            elif _color == "orange":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 8
                    if _temp not in orange_list:
                        orange_list.append(_temp)

            elif _color == "purple":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 9
                    if _temp not in purple_list:
                        purple_list.append(_temp)

            elif _color == "yellow":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 10
                    if _temp not in yellow_list:
                        yellow_list.append(_temp)

            elif _color == "checkpoint":
                ## # ## # # # # ##### # print("I DETECTED A CHECKPOINT ----")
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 3
                    if _temp not in checkpoint_list:
                        ## # ## # # # # ##### # print("I am a blackboard =======>", _temp)
                        checkpoint_list.append(_temp)

            elif _color == "swamp":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        Colored_tile_array[_temp[0]][_temp[1]] = 4
                    if _temp not in swamp_list:
                        swamp_list.append(_temp)

            elif _color == "hole":
                for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2), (-1, -2), (0, -2), (1, -2), (-1, 2), (0, 2), (1, 2)]:
                    _temp = (_Center[0] + i, _Center[1] + j)
                    if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                        ## # ## # # # # ##### # print("hole pos: ", _temp)
                        Colored_tile_array[_temp[0]][_temp[1]] = 2
                        Tile_array[_temp[0]][_temp[1]] = 2
                        hole_center_map = tile_to_map(_Center)
                        if room == 4:
                            Room_tile_array[_Center[0]][_Center[1]] = 4
                        cv.rectangle(Map, (hole_center_map[1] - 60, hole_center_map[0] - 60), (hole_center_map[1] + 60, hole_center_map[0] + 60), 200, -1)
                        cv.rectangle(color_array, (hole_center_map[1] - 60, hole_center_map[0] - 60), (hole_center_map[1] + 60, hole_center_map[0] + 60), (30, 30 ,30), -1)

            else:
                ## # ## # # # # ##### # print("Invalid Color")
                pass

def irregular_tiles_correction_colors(_pos, _color):
    global Colored_tile_array, blue_list, green_list, red_list, orange_list, purple_list, yellow_list, checkpoint_list, swamp_list, Map, Tile_array

    if not ((_pos[0] % 4 == 2) or (_pos[1] % 4 == 2)):

        if (_pos[0] % 4 == 1) and (_pos[1] % 4 == 1):
            _Center = (_pos[0] - 1, _pos[1] - 1)
        elif (_pos[0] % 4 == 1) and (_pos[1] % 4 == 0):
            _Center = (_pos[0] - 1, _pos[1])
        elif (_pos[0] % 4 == 1) and (_pos[1] % 4 == 3):
            _Center = (_pos[0] - 1, _pos[1] + 1)
        elif (_pos[0] % 4 == 0) and (_pos[1] % 4 == 3):
            _Center = (_pos[0], _pos[1] + 1)
        elif (_pos[0] % 4 == 3) and (_pos[1] % 4 == 3):
            _Center = (_pos[0] + 1, _pos[1] + 1)
        elif (_pos[0] % 4 == 3) and (_pos[1] % 4 == 0):
            _Center = (_pos[0] + 1, _pos[1])
        elif (_pos[0] % 4 == 3) and (_pos[1] % 4 == 1):
            _Center = (_pos[0] + 1, _pos[1] - 1)
        elif (_pos[0] % 4 == 0) and (_pos[1] % 4 == 1):
            _Center = (_pos[0], _pos[1] - 1)
        elif (_pos[0] % 4 == 0) and (_pos[1] % 4 == 0):
            _Center = (_pos[0], _pos[1])
            ## # ## # # # # ##### # print("CENTER DETECTED")
        else:
            ## # ## # # # # ##### # print("Wierd Error!!!!")
            pass

        ## # ## # # # # ##### # print("CORRECTION----------------------------------------------------------")
        if _color == "blue":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 5
                if _temp not in blue_list:
                    blue_list.append(_temp)

        elif _color == "green":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 6
                if _temp not in green_list:
                    green_list.append(_temp)

        elif _color == "red":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 7
                if _temp not in red_list:
                    red_list.append(_temp)

        elif _color == "orange":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 8
                if _temp not in orange_list:
                    orange_list.append(_temp)

        elif _color == "purple":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 9
                if _temp not in purple_list:
                    purple_list.append(_temp)

        elif _color == "yellow":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 10
                if _temp not in yellow_list:
                    yellow_list.append(_temp)

        elif _color == "checkpoint":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                Colored_tile_array[_temp[0]][_temp[1]] = 3
                if _temp not in checkpoint_list:
                    checkpoint_list.append(_temp)

        elif _color == "swamp":
            ### # print("in elif swamp in irregular_tiles_correction_colors")
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                # if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                ### # print("_temp: ", _temp)
                Colored_tile_array[_temp[0]][_temp[1]] = 4
                if _temp not in swamp_list:
                    ### # print(_temp, " added to list")
                    swamp_list.append(_temp)

        elif _color == "hole":
            for i, j in [(0, 0), (0, 1), (0, -1), (1, 1), (1, -1), (1, 0), (-1, 0), (-1, 1), (-1, -1), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2), (-1, -2), (0, -2), (1, -2), (-1, 2), (0, 2), (1, 2)]:
                _temp = (_Center[0] + i, _Center[1] + j)
                if Colored_tile_array[_temp[0]][_temp[1]] == 0:
                    ## # ## # # # # ##### # print("hole pos: ", _temp)
                    Colored_tile_array[_temp[0]][_temp[1]] = 2
                    Tile_array[_temp[0]][_temp[1]] = 2
                    hole_center_map = tile_to_map(_Center)
                    if room == 4:
                        Room_tile_array[_Center[0]][_Center[1]] = 4
                    cv.rectangle(Map, (hole_center_map[1] - 60, hole_center_map[0] - 60), (hole_center_map[1] + 60, hole_center_map[0] + 60), 200, -1)
                    cv.rectangle(color_array, (hole_center_map[1] - 60, hole_center_map[0] - 60), (hole_center_map[1] + 60, hole_center_map[0] + 60), (30, 30 ,30), -1)

        else:
            ## # ## # # # # ##### # print("Invalid Color")
            pass

def near_12cm_centers(_gps_pos):
    _a_x = _gps_pos[0] // 12
    _b_x = _gps_pos[0] % 12
    if _b_x >= 6:
        _a_x += 1

    _a_y = _gps_pos[1] // 12
    _b_y = _gps_pos[1] % 12
    if _b_y >= 6:
        _a_y += 1

    _center_12cm = (_a_x * 12.0, _a_y * 12.0)
    # ## # ## # # # # ##### # print("center: ", _center_12cm)

    distance = math.sqrt((_center_12cm[0] - _gps_pos[0]) ** 2 + (_center_12cm[1] - _gps_pos[1]) ** 2)

    if distance < NEAR_12CM_CENTER_THRESHOLD:
        return True, _center_12cm
    else:
        return False, None


def colored_processing(calibrated_x, calibrated_y, _rangeImage_index, pixel_row, pixel_col, _camera_frame):
     if rangeImage[_rangeImage_index] > 0.02 + math.sqrt((calibrated_x ** 2) + (calibrated_y ** 2)):
        if what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "blue":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                print("blue is detect")
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60), (255,0,0), -1)

                irregular_tiles_correction_colors(_center_color_pos, "blue")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "green":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60), (0,255,0), -1)
                irregular_tiles_correction_colors(_center_color_pos, "green")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "red":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60), (0,0,255), -1)
                irregular_tiles_correction_colors(_center_color_pos, "red")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "orange":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60), (48, 185, 232), -1)
                irregular_tiles_correction_colors(_center_color_pos, "orange")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "purple":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60),(107, 48, 185), -1)
                irregular_tiles_correction_colors(_center_color_pos, "purple")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "yellow":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60), (48, 235, 235, ),-1)
                irregular_tiles_correction_colors(_center_color_pos, "yellow")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "checkpoint":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            near = near_12cm_centers(color_pos_gps)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60),(138, 93, 76), -1)
                irregular_tiles_correction_colors(_center_color_pos, "checkpoint")

        elif what_tile_is_it(pixel_row, pixel_col, _camera_frame) == "swamp":
            color_pos_gps = localToGlobal(math.radians(yaw), (calibrated_x, calibrated_y))
            ### # print("I saw swamp: ", color_pos_gps)
            near = near_12cm_centers(color_pos_gps)
            ### # print("near swamp: ", near)
            if near[0]:
                _center_color_pos = gps_to_tile(near[1])
                temp_map  =  tile_to_map(_center_color_pos)
                cv.rectangle(color_array, (temp_map[1] - 60, temp_map[0] - 60), (temp_map[1] + 60, temp_map[0] + 60), (80, 140, 190), -1)
                ### # print("center color pos: ", _center_color_pos)
                irregular_tiles_correction_colors(_center_color_pos, "swamp")

def colored_tile(): # TODO: Be careful of two colored tile next to each other.
# 1024 : front - 1152: right - 1280: back - 1408: left


#Front__________________________________________________________________________________________
    colored_processing(5.40, 0, 1024, 36, 16, 'f')

#Addition (pixel 29) Front__________________________________________________________________________________________
    colored_processing(6.83, 0, 1024, 29, 16, 'f')

#Addition (pixel 20) Front__________________________________________________________________________________________
    colored_processing(9.980, 0, 1024, 20, 16, 'f')

#Addition (pixel 15) Front__________________________________________________________________________________________
    colored_processing(13.09456, 0, 1024, 15, 16, 'f')





#Right__________________________________________________________________________________________
    colored_processing(0, -5.42, 1152, 36, 16, 'r')

#Addition (pixel 29) Right__________________________________________________________________________________________
    colored_processing(0, -6.85, 1152, 29, 16, 'r')

#Addition (pixel 20) Right__________________________________________________________________________________________
    colored_processing(0, -9.992, 1152, 20, 16, 'r')

#Addition (pixel 15) Right__________________________________________________________________________________________
    colored_processing(0, -13.0993, 1152, 15, 16, 'r')





#Left_________________________________________________________________________________________
    colored_processing(0, 5.27, 1408, 37, 16, 'l')

#Addition (pixel 29) Left_________________________________________________________________________________________
    colored_processing(0, 6.88, 1408, 29, 16, 'l')

#Addition (pixel 20) Left__________________________________________________________________________________________
    colored_processing(0, 10.044, 1408, 20, 16, 'l')

#Addition (pixel 15) Left__________________________________________________________________________________________
    colored_processing(0, 13.1876, 1408, 15, 16, 'l')



def update_FIFO(new_input):
    global recent_visited_tiles, recent_size

    if new_input != recent_visited_tiles[-1]:
        for i in range(1, recent_size):
            recent_visited_tiles[i-1] = recent_visited_tiles[i]

        recent_visited_tiles[recent_size-1] = new_input

def update_recent_nodes(new_input):
    global recent_visited_nodes, recent_size

    if new_input != recent_visited_nodes[-1]:
        for i in range(1, recent_size):
            recent_visited_nodes[i-1] = recent_visited_nodes[i]

        recent_visited_nodes[recent_size-1] = new_input

def find_up_left():
    global tile_up, tile_left
    temp = map_to_tile((up, left))
    if temp[0] % 4 == 0:
        tile_up = temp[0]
    elif temp[0] % 4 == 1:
        tile_up = temp[0] - 1
    elif temp[0] % 4 == 2:
        tile_up = temp[0] + 2
    elif temp[0] % 4 == 3:
        tile_up = temp[0] + 1

    if temp[1] % 4 == 0:
        tile_left = temp[1]
    elif temp[1] % 4 == 1:
        tile_left = temp[1] - 1
    elif temp[1] % 4 == 2:
        tile_left = temp[1] + 2
    elif temp[1] % 4 == 3:
        tile_left = temp[1] + 1

    return (tile_up, tile_left)

def find_down_right():
    global tile_down, tile_right
    temp = map_to_tile((down, right))
    if temp[0] % 4 == 0:
        tile_down = temp[0]
    elif temp[0] % 4 == 1:
        tile_down = temp[0] - 1
    elif temp[0] % 4 == 2:
        tile_down = temp[0] - 2
    elif temp[0] % 4 == 3:
        tile_down = temp[0] + 1

    if temp[1] % 4 == 0:
        tile_right = temp[1]

    elif temp[1] % 4 == 1:
        tile_right = temp[1] - 1

    elif temp[1] % 4 == 2:
        tile_right = temp[1] - 2

    elif temp[1] % 4 == 3:
        tile_right = temp[1] + 1

    return (tile_down, tile_right)



def is_colored_tile(input):

    if input in blue_list:
        return True, "blue"
    elif input in green_list:
        return True, "green"
    elif input in red_list:
        return True, "red"
    elif input in orange_list:
        return True, "orange"
    elif input in purple_list:
        return True, "purple"
    elif input in yellow_list:
        return True, "yellow"
    return False, "None"

# def report_map_bonus():
#     global Map_Bonus, report_matrix, device
#     #### # ## # # # # ##### # print("in report map function...")

#     vision_to_map_bonus_dic = {"Corrosive": "C", "Flame": "F", "H": "H", "Organic": "O", "Poison": "P", "S": "S", "U": "U"}

#     x = 12//TILE_SIZE
#     something = TILE_SIZE//3
#     _n = 4*((tile_down - tile_up+4)//x) + 1
#     _m = 4*((tile_right - tile_left+4)//x) + 1
#     # # # ## # # # # ##### # print("-----------------map size: ", (_n, _m))
#     report_matrix = np.full((_n, _m), '0', dtype='U2')
#     ## # ## # # # # ##### # print("tile down: ", tile_down, "tile up: ", tile_up)
#     ## # ## # # # # ##### # print("tile right: ", tile_right, "tile left: ", tile_left)



#     # colored tiles & half walls
#     for i in range(tile_up, tile_down+x, x):
#         for j in range(tile_left, tile_right+x, x):
#             map_ij = tile_to_map((i, j))
#             tile = Map_Bonus[map_ij[0]-60:map_ij[0]+60, map_ij[1]-60:map_ij[1]+60]
#             obstacle_tile_pro = Map_Obstacle[map_ij[0]-90:map_ij[0]+90, map_ij[1]-90:map_ij[1]+90]
#             blur_obs = cv.blur(obstacle_tile_pro, (5, 5))
#             _, thresh_obs = cv.threshold(blur_obs, 10, 255, cv.THRESH_BINARY)
#             boxed = thresh_obs.copy()
#             # cv.imshow("THRESHED", thresh_obs)
#             # cv.waitKey(0)

#             contours, _ = cv.findContours(thresh_obs, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
#             if len(contours) > 0:
#                 # Pick largest contour
#                 largest = max(contours, key=cv.contourArea)
#                 ##### # print("OUR AREA ===> ", cv.contourArea(largest))
#                 if cv.contourArea(largest) > 30:
#                     # Wrap in list for drawContours
#                     cv.drawContours(boxed, [largest], 0, (128, 128, 128), 3)

#                     box = cv.minAreaRect(largest)

#                     # Explicitly cast numpy floats to Python ints
#                     cx = int(round(float(box[0][0])))
#                     cy = int(round(float(box[0][1])))
#                     center = (cx, cy)

#                     ##### # print("CENTER IN OBS ==> ", center)
#                     # cv.circle(boxed, center, 4, (255, 255, 255), -1)
#                     # cv.imshow("BOXED", boxed)
#                     # cv.waitKey(0)

#                     if (30 < cx < 150) and (30 < cy < 150):
#                         report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'x'
#                         report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'x'
#                         report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'x'
#                         report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'x'

#             if (i == ARRAY_SIZE//2) and (j == ARRAY_SIZE//2):
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = '5'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = '5'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = '5'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = '5'
#             # blue: 5, green: 6, red: 7, orange: 8, purple: 9, yellow: 10, checkpoint: 3, swamp: 4
#             elif Colored_tile_array[i][j] == 5:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'b'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'b'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'b'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'b'

#             elif Colored_tile_array[i][j] == 6:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'g'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'g'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'g'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'g'

#             elif Colored_tile_array[i][j] == 7:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'r'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'r'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'r'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'r'

#             elif Colored_tile_array[i][j] == 8:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'o'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'o'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'o'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'o'

#             elif Colored_tile_array[i][j] == 9:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'p'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'p'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'p'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'p'

#             elif Colored_tile_array[i][j] == 10:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'y'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'y'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'y'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'y'

#             elif Colored_tile_array[i][j] == 3:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = '4'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = '4'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = '4'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = '4'

#             elif Colored_tile_array[i][j] == 4:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = '3'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = '3'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = '3'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = '3'

#             elif Colored_tile_array[i][j] == 2:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = '2'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = '2'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = '2'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = '2'



#             with torch.no_grad():
#                 temp_sample_obs = tile
#                 img_obs = Image.fromarray(temp_sample_obs, mode="L")
#                 # transformed_obs = base_tf_obstacle(img_obs).unsqueeze(0).to(device)
#                 transformed_obs = base_tf_obstacle(img_obs).unsqueeze(0)
#                 out_obstacle = obstacle_mapping_model(transformed_obs)
#                 obs_pred = (torch.sigmoid(out_obstacle) > 0.98).int().item()

#             if obs_pred == 1:
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = 'x'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = 'x'
#                 report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = 'x'
#                 report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = 'x'


#             # up left 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(0, 15):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1

#             # up left 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(15, 30):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1


#             # up left 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(30, 45):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1

#             # up left 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(45, 60):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'



#             # up right 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(60, 75):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # up right 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(75, 90):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1



#             # up right 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(90, 105):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1



#             # up right 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(0, 10):
#                 for jj in range(105, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '1'



#             # down left 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(0, 15):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1


#             # down left 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(15, 30):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1



#             # down left 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(30, 45):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1


#             # down left 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(45, 60):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'



#             # down right 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(60, 75):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # down right 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(75, 90):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1



#             # down right 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(90, 105):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1



#             # down right 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(110, 120):
#                 for jj in range(105, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1


#             #### # ## # # # # ##### # print('SUS IN CW 1 2 3 4 :', counter_wall1,'/t', counter_wall2,'/t', counter_wall3,'/t', counter_wall4)
#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '1'



#             # left up 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(0, 15):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # left up 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(15, 30):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1




#             # left up 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(30, 45):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1



#             # left up 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(45, 60):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1


#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'




#             # left down 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(60, 75):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # left down 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(75, 90):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1




#             # left down 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(90, 105):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1



#             # left down 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(105, 120):
#                 for jj in range(0, 10):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '1'



#             # right up 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(0, 15):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # right up 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(15, 30):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1



#             # right up 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(30, 45):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1


#             # right up 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(45, 60):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1


#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'



#             # right down 01
#             counter_wall1 = 0
#             wall_threshold = 20
#             for ii in range(60, 75):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # right down 02
#             counter_wall2 = 0
#             wall_threshold = 20
#             for ii in range(75, 90):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1




#             # right down 03
#             counter_wall3 = 0
#             wall_threshold = 20
#             for ii in range(90, 105):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1



#             # right down 04
#             counter_wall4 = 0
#             wall_threshold = 20
#             for ii in range(105, 120):
#                 for jj in range(110, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '1'




#             # middle up 01

#             counter_wall1 = 0
#             wall_threshold = 40
#             for ii in range(0, 15):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1



#             # middle up 02
#             counter_wall2 = 0
#             wall_threshold = 40
#             for ii in range(15, 30):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1


#             # middle up 03
#             counter_wall3 = 0
#             wall_threshold = 40
#             for ii in range(30, 45):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1


#             # middle up 04
#             counter_wall4 = 0
#             wall_threshold = 40
#             for ii in range(45, 60):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1


#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'

#             # middle down 01
#             counter_wall1 = 0
#             wall_threshold = 40
#             for ii in range(60, 75):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1


#             # middle down 02
#             counter_wall2 = 0
#             wall_threshold = 40
#             for ii in range(75, 90):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1



#             # middle down 03
#             counter_wall3 = 0
#             wall_threshold = 40
#             for ii in range(90, 105):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1



#             # middle down 04
#             counter_wall4 = 0
#             wall_threshold = 40
#             for ii in range(105, 120):
#                 for jj in range(50, 70):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'


#             # middle left 01
#             counter_wall1 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(0, 15):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1




#             # middle left 02
#             counter_wall2 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(15, 30):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1


#             # middle left 03
#             counter_wall3 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(30, 45):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1


#             # middle left 04
#             counter_wall4 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(45, 60):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'


#             # middle right 01
#             counter_wall1 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(60, 75):
#                     if tile[ii, jj] == 255:
#                         counter_wall1 += 1




#             # middle right 02
#             counter_wall2 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(75, 90):
#                     if tile[ii, jj] == 255:
#                         counter_wall2 += 1



#             # middle right 03
#             counter_wall3 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(90, 105):
#                     if tile[ii, jj] == 255:
#                         counter_wall3 += 1




#             # middle right 04
#             counter_wall4 = 0
#             wall_threshold = 40
#             for ii in range(50, 70):
#                 for jj in range(105, 120):
#                     if tile[ii, jj] == 255:
#                         counter_wall4 += 1



#             if counter_wall1 > wall_threshold and counter_wall2 > wall_threshold and counter_wall3 > wall_threshold and counter_wall4 > wall_threshold:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'


#     # curved walls
#     for i in range(tile_up, tile_down+x, x):
#         for j in range(tile_left, tile_right+x, x):
#             map_ij = tile_to_map((i, j))
#             tile = Map_Bonus[map_ij[0]-60:map_ij[0]+60, map_ij[1]-60:map_ij[1]+60]
#             #### # ## # # # # ##### # print("tile array: ", Colored_tile_array[i][j])
#             up_left = Map_Bonus[map_ij[0]-60:map_ij[0]-0, map_ij[1]-60:map_ij[1]-0]
#             up_right = Map_Bonus[map_ij[0]-60:map_ij[0]-0, map_ij[1]-0:map_ij[1]+60]
#             down_left = Map_Bonus[map_ij[0]-0:map_ij[0]+60, map_ij[1]-60:map_ij[1]-0]
#             down_right = Map_Bonus[map_ij[0]-0:map_ij[0]+60, map_ij[1]-0:map_ij[1]+60]
#             with torch.no_grad():
#                 img_up_left = Image.fromarray(up_left, mode="L")
#                 normalized_up_left = base_tf(img_up_left).unsqueeze(0).to(device)
#                 out_up_left = curved_wall_mapping_model(normalized_up_left).argmax(1).item()

#                 #________________________________
#                 img_up_right = Image.fromarray(up_right, mode="L")
#                 normalized_up_right = base_tf(img_up_right).unsqueeze(0).to(device)
#                 out_up_right = curved_wall_mapping_model(normalized_up_right).argmax(1).item()

#                 #________________________________
#                 img_down_left = Image.fromarray(down_left, mode="L")
#                 normalized_down_left = base_tf(img_down_left).unsqueeze(0).to(device)
#                 out_down_left = curved_wall_mapping_model(normalized_down_left).argmax(1).item()

#                 #________________________________
#                 img_down_right = Image.fromarray(down_right, mode="L")
#                 normalized_down_right = base_tf(img_down_right).unsqueeze(0).to(device)
#                 out_down_right = curved_wall_mapping_model(normalized_down_right).argmax(1).item()

#             """ up left """
#             if out_up_left == 1:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#             elif out_up_left == 2:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#             elif out_up_left == 3:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#             elif out_up_left == 4:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'


#             """ up right """
#             if out_up_right == 1:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '1'
#             elif out_up_right == 2:
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'
#             elif out_up_right == 3:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#             elif out_up_right == 4:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'

#             """ down left """
#             if out_down_left == 1:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#             elif out_down_left == 2:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'
#             elif out_down_left == 3:
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '1'
#             elif out_down_left == 4:
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+1] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'


#             """ down right """
#             if out_down_right == 1:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'
#             elif out_down_right == 2:
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '1'
#             elif out_down_right == 3:
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'
#             elif out_down_right == 4:
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '0'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+3] = '1'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '1'

#             # up left
#             # cropped_tile = tile[:60, :60]
#             # cropped_tile = cv.medianBlur(cropped_tile, 5)
#             # square1 = cropped_tile[20:25, 36:41] # up right
#             # square1plus = cropped_tile[12:17, 43:48]
#             # square2 = cropped_tile[17:22, 22:27] # up left
#             # square2plus = cropped_tile[12:17, 17:22]
#             # square3 = cropped_tile[35:40,40:45] # down right
#             # square3plus = cropped_tile[40:45, 45:50]
#             # square4 = cropped_tile[37:42,19:24] # down left
#             # square4plus = cropped_tile[41:46, 15:20]

#             # if (np.count_nonzero(square1) > 17.3) or (np.count_nonzero(square1plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 1 : down left")
#             #     ### # ## # # # # ##### # print(f"square 1 -------- up left {(i,j)}")
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'


#             # # elif np.all(square2 == 255):
#             # elif (np.count_nonzero(square2) > 17.3) or (np.count_nonzero(square2plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 2 : up left")
#             #     ### # ## # # # # ##### # print(f"square 2 -------- up left {(i,j)}")
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '0'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'

#             # # elif np.all(square3 == 255):
#             # elif (np.count_nonzero(square3) > 17.3) or (np.count_nonzero(square3plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 3 : down right")
#             #     ### # ## # # # # ##### # print(f"square 3 -------- up left {(i,j)}")
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'


#             # # elif np.all(square4 == 255):
#             # elif (np.count_nonzero(square4) > 17.3) or (np.count_nonzero(square4plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 4 : up right")
#             #     ### # ## # # # # ##### # print(f"square 4 -------- up left {(i,j)}")

#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '0'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'

#             # # up right
#             # cropped_tile = tile[:60, 60:120]
#             # cropped_tile = cv.medianBlur(cropped_tile, 5)
#             # square1 = cropped_tile[20:25, 36:41] # up right
#             # square1plus = cropped_tile[12:17, 43:48]
#             # square2 = cropped_tile[17:22, 22:27] # up left
#             # square2plus = cropped_tile[12:17, 17:22]
#             # square3 = cropped_tile[35:40,40:45] # down right
#             # square3plus = cropped_tile[40:45, 45:50]
#             # square4 = cropped_tile[37:42,19:24] # down left
#             # square4plus = cropped_tile[41:46, 15:20]
#             # #### # ## # # # # ##### # print(square1)
#             # # if np.all(square1 == 255):

#             # if (np.count_nonzero(square1) > 17.3) or (np.count_nonzero(square1plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 1 : down left")
#             #     ### # ## # # # # ##### # print(f"square 1 -------- up right {(i,j)}")
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '0'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'


#             # # elif np.all(square2 == 255):
#             # elif (np.count_nonzero(square2) > 17.3) or (np.count_nonzero(square2plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 2 : up left")
#             #     ### # ## # # # # ##### # print(f"square 2 -------- up right {(i,j)}")


#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'

#             # # elif np.all(square3 == 255):
#             # elif (np.count_nonzero(square3) > 17.3) or (np.count_nonzero(square3plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 3: down right")
#             #     ### # ## # # # # ##### # print(f"square 3 -------- up right {(i,j)}")

#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '0'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'

#             # # elif np.all(square4 == 255):
#             # elif (np.count_nonzero(square4) > 17.3) or (np.count_nonzero(square4plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 4 : up right")
#             #     ### # ## # # # # ##### # print(f"square 4 -------- up right {(i,j)}")

#             #     report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'


#             # # down left
#             # cropped_tile = tile[60:120, :60]
#             # cropped_tile = cv.medianBlur(cropped_tile, 5)
#             # square1 = cropped_tile[20:25, 36:41] # up right
#             # square1plus = cropped_tile[12:17, 43:48]
#             # square2 = cropped_tile[17:22, 22:27] # up left
#             # square2plus = cropped_tile[12:17, 17:22]
#             # square3 = cropped_tile[35:40,40:45] # down right
#             # square3plus = cropped_tile[40:45, 45:50]
#             # square4 = cropped_tile[37:42,19:24] # down left
#             # square4plus = cropped_tile[41:46, 15:20]

#             # if (np.count_nonzero(square1) > 17.3) or (np.count_nonzero(square1plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 1 : down left")
#             #     ### # ## # # # # ##### # print(f"square 1 -------- down left {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'

#             # # elif np.all(square2 == 255):
#             # elif (np.count_nonzero(square2) > 17.3) or (np.count_nonzero(square2plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 2 : up left")
#             #     ### # ## # # # # ##### # print(f"square 2 -------- down left {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '0'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '1'

#             # # elif np.all(square3 == 255):
#             # elif (np.count_nonzero(square3) > 17.3) or (np.count_nonzero(square3plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 3 : down right")
#             #     ### # ## # # # # ##### # print(f"square 3 -------- down left {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '1'
#             # # elif np.all(square4 == 255):
#             # elif (np.count_nonzero(square4) > 17.3) or (np.count_nonzero(square4plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 4 : up right")
#             #     ### # ## # # # # ##### # print(f"square 4 -------- down left {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '0'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+1] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'

#             # # down right
#             # cropped_tile = tile[60:120, 60:120]
#             # cropped_tile = cv.medianBlur(cropped_tile, 5)
#             # square1 = cropped_tile[20:25, 36:41] # up right
#             # square1plus = cropped_tile[12:17, 43:48]
#             # square2 = cropped_tile[17:22, 22:27] # up left
#             # square2plus = cropped_tile[12:17, 17:22]
#             # square3 = cropped_tile[35:40,40:45] # down right
#             # square3plus = cropped_tile[40:45, 45:50]
#             # square4 = cropped_tile[37:42,19:24] # down left
#             # square4plus = cropped_tile[41:46, 15:20]

#             # if (np.count_nonzero(square1) > 17.3) or (np.count_nonzero(square1plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 1 : down left")
#             #     ### # ## # # # # ##### # print(f"square 1 -------- down right {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '0'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '1'
#             # # elif np.all(square2 == 255):
#             # elif (np.count_nonzero(square2) > 17.3) or (np.count_nonzero(square2plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 2 : up left")
#             #     ### # ## # # # # ##### # print(f"square 2 -------- down right {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '0'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'
#             # # elif np.all(square3 == 255):
#             # elif (np.count_nonzero(square3) > 17.3) or (np.count_nonzero(square3plus) > 17.3):
#             #     #### # ## # # # # ##### # print("square 3 : down right")
#             #     ### # ## # # # # ##### # print(f"square 3 -------- down right {(i,j)}")

#             #     report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+4] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '0'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+3] = '1'
#             #     report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '1'

#             # elif np.all(square4 == 255):
#             # elif (np.count_nonzero(square4) > 17.3) or (np.count_nonzero(square4plus) > 17.3):
#                 #### # ## # # # # ##### # print("square 4 : up right")
#                 ### # ## # # # # ##### # print(f"square 4 -------- down right {(i,j)}")

#                 # report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '1'
#                 # report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '1'
#                 # report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '0'
#                 # report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+3] = '1'
#                 # report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '1'


#             # #### # ## # # # # ##### # print(square2)



#     # room 4
#     room4_wall_threshold = 320
#     for i in range(tile_up, tile_down+x, x):
#         for j in range(tile_left, tile_right+x, x):
#             # #### # ## # # # # ##### # print(is_colored_tile((i,j)))
#             map_ij = tile_to_map((i, j))
#             tile = Map_Bonus[map_ij[0]-60:map_ij[0]+60, map_ij[1]-60:map_ij[1]+60]

#             # in_room_4_flag = (Room_tile_array[i, j] == 4) or (Room_tile_array[i+1, j-1] == 4) or (Room_tile_array[i+1, j] == 4) or (Room_tile_array[i+1, j-1] == 4) or (Room_tile_array[i, j-1] == 4) or (Room_tile_array[i, j+1] == 4) or (Room_tile_array[i-1, j] == 4) or (Room_tile_array[i-1, j-1] == 4) or (Room_tile_array[i-1, j+1] == 4)

#             in_room_4_flag = False
#             for _iii, _jjj in [(0, 0), (0, 1), (0, -1), (-1, 0), (-1, 1), (-1, -1), (1, 0), (1, -1), (1, 1)]:
#                 if Room_tile_array[i + _iii, j + _jjj] == 4:
#                     in_room_4_flag = True
#                     break

#             # in_room_123_flag = ((Room_tile_array[i, j] == 1) or (Room_tile_array[i+1, j] == 1) or (Room_tile_array[i+1, j-1] == 1) or (Room_tile_array[i+1, j+1] == 1) or (Room_tile_array[i, j+1] == 1) or (Room_tile_array[i, j-1] == 1) or (Room_tile_array[i-1, j] == 1) or (Room_tile_array[i-1, j-1] == 1) or (Room_tile_array[i-1, j+1] == 1)) or ((Room_tile_array[i, j] == 2) or (Room_tile_array[i+1, j] == 2) or (Room_tile_array[i+1, j-1] == 2) or (Room_tile_array[i+1, j+1] == 2) or (Room_tile_array[i, j+1] == 2) or (Room_tile_array[i, j-1] == 2) or (Room_tile_array[i-1, j] == 2) or (Room_tile_array[i-1, j-1] == 2) or (Room_tile_array[i-1, j+1] == 2)) or ((Room_tile_array[i, j] == 3) or (Room_tile_array[i+1, j] == 3) or (Room_tile_array[i+1, j-1] == 3) or (Room_tile_array[i+1, j+1] == 3) or (Room_tile_array[i, j+1] == 3) or (Room_tile_array[i, j-1] == 3) or (Room_tile_array[i-1, j] == 3) or (Room_tile_array[i-1, j-1] == 3) or (Room_tile_array[i-1, j+1] == 3))
#             in_room_123_flag = False
#             # for _iii, _jjj in [(0, 0), (0, 1), (0, -1), (-1, 0), (-1, 1), (-1, -1), (1, 0), (1, -1), (1, 1)]:
#             for _iii, _jjj in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
#                 if (Room_tile_array[i + _iii, j + _jjj] == 1) or (Room_tile_array[i + _iii, j + _jjj] == 2) or (Room_tile_array[i + _iii, j + _jjj] == 3):
#                     in_room_123_flag = True
#                     break

#             if ((in_room_4_flag) and (not is_colored_tile((i,j))[0])) or ((np.count_nonzero(tile == 128) > room4_wall_threshold) and (not in_room_123_flag) and (not is_colored_tile((i,j))[0])):
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)] = '*'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+1] = '*'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+2] = '*'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+3] = '*'
#                 report_matrix[something*(i-tile_up)][something*(j-tile_left)+4] = '*'

#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)] = '*'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+1] = '*'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+2] = '*'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+3] = '*'
#                 report_matrix[something*(i-tile_up)+1][something*(j-tile_left)+4] = '*'

#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)] = '*'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+1] = '*'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+2] = '*'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+3] = '*'
#                 report_matrix[something*(i-tile_up)+2][something*(j-tile_left)+4] = '*'


#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)] = '*'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+1] = '*'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+2] = '*'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+3] = '*'
#                 report_matrix[something*(i-tile_up)+3][something*(j-tile_left)+4] = '*'

#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)] = '*'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+1] = '*'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+2] = '*'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+3] = '*'
#                 report_matrix[something*(i-tile_up)+4][something*(j-tile_left)+4] = '*'
#             #### # ## # # # # ##### # print(np.count_nonzero(tile == 128))
#             # np.savetxt("image.txt", tile, fmt="%d")
#             #### # ## # # # # ##### # print(tile)




#     # victims
#     for i in range(tile_up, tile_down+x, x):
#         for j in range(tile_left, tile_right+x, x):
#             # #### # ## # # # # ##### # print(is_colored_tile((i,j)))
#             # tile = Map_Bonus[map_ij[0]-60:map_ij[0]+60, map_ij[1]-60:map_ij[1]+60]
#             map_ij = tile_to_map((i, j))
#             # ## # ## # # # # ##### # print(i, j)
#             # ## # ## # # # # ##### # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
#             for vic_iter in victim_pos_list:
#                 # ## # ## # # # # ##### # print("vic iter: ", vic_iter)
#                 _gps_x_vic = vic_iter[0]
#                 _gps_y_vic = vic_iter[1]
#                 vic_tile = gps_to_tile((_gps_x_vic, _gps_y_vic))
#                 vic_tile = gps_to_tile((_gps_x_vic, _gps_y_vic))
#                 # ## # ## # # # # ##### # print("vic_tile: ", vic_tile)
#                 _dif = (vic_tile[0] - i, vic_tile[1] - j)
#                 # ## # ## # # # # ##### # print("dif: ", _dif)
#                 if _dif in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0), (-2, 0), (2, 0), (0, -2), (0, 2), (2, -2), (2, -1), (2, 1), (2, 2), (-2, -2), (-2, -1), (-2, 1), (-2, 2), (1, -2), (1, 2), (-1, -2), (-1, 2)]:
#                     # ## # ## # # # # ##### # print("in if 1: ", report_matrix[(something*(i-tile_up)) + 2 + _dif[0]][(something*(j-tile_left)) + 2 + _dif[1]])
#                     # ## # ## # # # # ##### # print("idx 0: ", (something*(i-tile_up)) + 2 + _dif[0], "     idx 1:", (something*(j-tile_left)) + 2 + _dif[1])
#                     if report_matrix[(something*(i-tile_up)) + 2 + _dif[0]][something*(j-tile_left) + 2 + _dif[1]] == '1':
#                         # ## # ## # # # # ##### # print("in if 2: ", vic_iter[4])
#                         report_matrix[(something*(i-tile_up)) + 2 + _dif[0]][something*(j-tile_left) + 2 + _dif[1]] = vision_to_map_bonus_dic[vic_iter[4]]
#                         victim_pos_list.remove(vic_iter)
#                     elif report_matrix[(something*(i-tile_up)) + 2 + _dif[0]][something*(j-tile_left) + 2 + _dif[1]] in ['H', 'S', 'U', 'P', 'C', 'F', 'O']:
#                         # ## # ## # # # # ##### # print("in elif")
#                         report_matrix[(something*(i-tile_up)) + 2 + _dif[0]][something*(j-tile_left) + 2 + _dif[1]] += vision_to_map_bonus_dic[vic_iter[4]]
#                         victim_pos_list.remove(vic_iter)
#             # cv.imshow("frame", tile)
#             # cv.waitKey(0)

#     # star correction
#     for i in range(_n):
#         for j in range(_m):
#             if report_matrix[i][j] == '0':
#                 up_check = False
#                 down_check = False
#                 left_check = False
#                 right_check = False

#                 for X in range(i, 0, -1):
#                     if report_matrix[X][j] != '0':
#                         if report_matrix[X][j] == '*':
#                             up_check = True
#                             break
#                         else:
#                             break

#                 for X in range(i, _n, 1):
#                     if report_matrix[X][j] != '0':
#                         if report_matrix[X][j] == '*':
#                             down_check = True
#                             break
#                         else:
#                             break

#                 for Y in range(j, _m, 1):
#                     if report_matrix[i][Y] != '0':
#                         if report_matrix[i][Y] == '*':
#                             right_check = True
#                             break
#                         else:
#                             break

#                 for Y in range(j, 0, -1):
#                     if report_matrix[i][Y] != '0':
#                         if report_matrix[i][Y] == '*':
#                             left_check = True
#                             break
#                         else:
#                             break

#                 if up_check and down_check and right_check and left_check:
#                     report_matrix[i][j] = '*'

#     # Making sure about start point
#     i = ARRAY_SIZE//2
#     j = ARRAY_SIZE//2
#     report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 1] = '5'
#     report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 1] = '5'
#     report_matrix[something*(i-tile_up) + 1][something*(j-tile_left) + 3] = '5'
#     report_matrix[something*(i-tile_up) + 3][something*(j-tile_left) + 3] = '5'

def rising_edge():
    before = is_colored_tile(recent_visited_tiles[2])
    after = is_colored_tile(recent_visited_tiles[3])
    if (not before[0]) and (after[0]):
        return True, after[1]
    return False, "None"

def falling_edge():
    before = is_colored_tile(recent_visited_tiles[2])
    after = is_colored_tile(recent_visited_tiles[3])
    if (before[0]) and (not after[0]):
        #### # print("before: ", before, "         after: ", after)
        #### # print("in falling edge: ", recent_visited_tiles[2])
        if (recent_visited_tiles[2][0] % 4 == 2) or (recent_visited_tiles[2][1] % 4 == 2) or True:
            return True, before[1]
    return False, "None"

def N(input):
    # # # ## # # # # ##### # print("---------------------------input:", input)
    result = []
    for (i, j) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1)]:
        # # # ## # # # # ##### # print(" input nei: ", (input[0]+i, input[1]+j))
        if not is_colored_tile((input[0]+i, input[1]+j))[0]:
            # # # ## # # # # ##### # print("not colored")
            if check_region(tile_to_map((input[0]+i, input[1]+j))):
                # # # ## # # # # ##### # print("check region ok")
                if Tile_array[input[0]+i, input[1]+j] != 2:
                    # # # ## # # # # ##### # print("not a hole")
                    result.append((input[0]+i, input[1]+j))
    return result

#eshterak
def find_unity(inp_A, inp_B):

    unity = []

    for i in inp_A:
        if i in inp_B:
            if i not in unity:
                unity.append(i)

    return unity

#ejtemah
def find_union(inp_A, inp_B):
    union = []
    c = inp_A + inp_B
    for i in c :
        if i not in union:
            union.append(i)

    return union

def detect_room():
    global A, B, room, mapping_in_colored_tile
    fe = falling_edge()
    re = rising_edge()
    #### # print("falling edge: ", falling_edge())
    #### # print("rising edge: ", rising_edge())
    if re[0]:
        if re[1] == "red" or re[1] == "green" or re[1] == "orange":
            mapping_in_colored_tile = True
        #### # print("rising edge in if: ", rising_edge())
        A = recent_visited_tiles[2]
        # # # ## # # # # ##### # print("A: ", A)
    elif fe[0]:
        mapping_in_colored_tile = False
        #### # print("falling edge: ", fe)
        B = recent_visited_tiles[3]
        #### # print("A was: ", A)
        #### # print("B: ", B)
        #### # print("NA: ", N(A))
        #### # print("NB: ", N(B))
        #### # print("unity: ", find_unity(N(A),N(B)))
        if find_unity(N(A),N(B)) == []:
            if fe[1] == "blue":
                if room == 1:
                    room = 2
                else:
                    room = 1
            elif fe[1] == "green":
                if room == 4:
                    room = 1
                else:
                    room = 4
            elif fe[1] == "orange":
                if room == 4:
                    room = 2
                else:
                    room = 4
            elif fe[1] == "red":
                if room == 4:
                    room = 3
                else:
                    room = 4
            elif fe[1] == "purple":
                if room == 3:
                    room = 2
                else:
                    room = 3
            elif fe[1] == "yellow":
                if room == 3:
                    room = 1
                else:
                    room = 3

def delay(t):
    global first_time_delay, first_Time

    if first_time_delay:
        first_Time = robot.getTime()
        first_time_delay = False

    if robot.getTime() - first_Time > t:
        return True
    else:
        return False

def detect_victim_coordinate(input_angle, D):
    x_robot_global = gps_x
    y_robot_global = gps_y
    theta = yaw
    theta = math.radians(theta)

    x_obstacle_local = D * math.cos(math.radians(-input_angle))
    y_obstacle_local = D * math.sin(math.radians(-input_angle))

    formula=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
    obstacle_cords_local=np.array([[x_obstacle_local], [y_obstacle_local]])
    rotation=np.matmul(formula,obstacle_cords_local)
    robot_cords=np.array([[x_robot_global], [y_robot_global]])
    result = robot_cords + rotation
    tempx = result[0][0]
    tempy = result[1][0]

    return tempx, tempy

def get_space(input_angle2):
    if input_angle2 < 0:
        input_angle2 = input_angle2 + 360
    elif input_angle2 > 360:
        input_angle2 = input_angle2 - 360
    i2 = (512/360) * input_angle2 + 1024
    rangeImage = LIDAR.getRangeImage()
    l2 = rangeImage[int(i2)]*100
    if math.isinf(l2):
        l2 = 99999
    return l2
# ____________ VISION FUNCS _____________
def distance_is_legal(side):
    if side == 'r':
        c = 90
    elif side == 'l':
        c = -90
    else:
        c = 0
    if (((get_space(c - 10) + get_space(c - 5)) / 2) + ((get_space(c + 5) + get_space(c + 10)) / 2) + get_space(c)) / 3 < 10.0:
        return True
    return False






# def yolo_model(frame):
#     # results = model.predict(source=frame, device=0 , imgsz=32, conf=0.77, max_det=1, half=True)
#     results = model.predict(frame, device=0, imgsz=32, conf=0.70, max_det=1, verbose = False)
#     return results[0]

# def get_yolo_data(result):

#     if result.boxes is None or len(result.boxes) == 0 : # if no object is detected
#         return None

#     keypoints = None
#     boxes = None
#     keypoint_x = 0
#     keypoint_y = 0
#     conf = 0
#     kpts_conf = 0
#     if result.keypoints is not None or result.keypoints.data.shape[0] != 0:
#         keypoints = result.keypoints.xy[0].cpu().numpy()
#         kpts_conf = result.keypoints.conf[0].cpu().numpy()
#         keypoints = keypoints[0]
#         keypoint_x, keypoint_y = keypoints

#     boxes = result.boxes

#     conf = float(boxes.conf[0])

#     x1, y1, x2, y2 = result.boxes.xyxy[0].cpu().numpy()

#     classes = boxes.cls.cpu().numpy()

#     classes_name = result.names[classes[0]]


#     return (classes_name, (x1, y1, x2, y2 ,keypoint_x , keypoint_y), conf, kpts_conf[0])



# def legal(lidar_ray):

#     range = rangeImage[lidar_ray]
#     if range < 8.0:
#         return True

#     return False


# src = np.float32([
# [0, 0],
# [31, 0],
# [31, 38],
# [0, 38]
# ])

# dst = np.float32([
#     [31, 0],
#     [63, 0],
#     [94, 76],
#     [0, 76]
# ])

# H = cv.getPerspectiveTransform(src, dst)




# def detect_circle(frame,keypoint_x,keypoint_y,box):
#     key_detect = False

#     x1,x2,y1,y2 = box
#     # print("KEYPOINT XY ========= > ", keypoint_x, keypoint_y)
#     if (keypoint_x <= 31 and keypoint_x >= 29) or (keypoint_x >= 0 and keypoint_x <= 2) :
#         return None

#     # Convert keypoint into coordinate format for transformation
#     pt = np.array([[[keypoint_x, keypoint_y]]], dtype=np.float32)

#     # Apply perspective transformation to map YOLO space to real-world space
#     warped_kp = cv.perspectiveTransform(pt, H)[0, 0]
#     warped_keypoint_x, warped_keypoint_y = warped_kp

#     # Adjust Y scaling due to mismatch between YOLO grid and real frame height
#     warped_keypoint_y = warped_keypoint_y * 39/32

#     keypoint_y = keypoint_y * 39/32
#     # ------------------------------------------------------------
#     # 6. CLASSIFY COLORS (BINARY MASKS)
#     # ------------------------------------------------------------

#     # Mask region below detected keypoint (darken area for separation)
#     # cv.imwrite(f"C:\\Users\\ARTIN\\Desktop\\a\\{time.time()}.png",frame)

#     frame[int(keypoint_y+2):, :] = (20,20,20)
#     frame[:, :int(keypoint_x - (keypoint_x - x1)/6)] = (20,20,20)
#     frame[:, int(keypoint_x + (x2 - keypoint_x)/6) : ] = (20,20,20)
#     # cv.imwrite(f"C:\\Users\\ARTIN\\Desktop\\a\\{time.time()}.png",frame)

#     # print(keypoint_x,keypoint_y,"||||",warped_keypoint_x,warped_keypoint_y)

#     # cv.imwrite(f"C:\\Users\\ARTIN\\Desktop\\a\\{time.time()}.png",frame)

#     # Create binary masks for each color range (BGR thresholds)
#     img_yellow = cv.inRange(frame, (0, 205, 205), (2, 209, 209))
#     img_blue   = cv.inRange(frame, (205, 0, 0), (209, 0, 0))
#     img_green  = cv.inRange(frame, (0, 205, 0), (0, 209, 0))
#     img_black  = cv.inRange(frame, (0, 0, 0), (2, 2, 2))
#     img_red    = cv.inRange(frame, (0, 0, 205), (0, 0, 209))

#     # Combine all color masks into a single mask
#     total_mask = img_yellow + img_blue + img_green + img_black + img_red

#     color_counter_black = not ((np.sum(img_black) //255) == 0)
#     color_counter_blue = not ((np.sum(img_blue) //255) == 0)
#     color_counter_yellow = not ((np.sum(img_yellow) //255) == 0)
#     color_counter_red = not ((np.sum(img_red) //255) == 0)
#     color_counter_green = not ((np.sum(img_green) //255) == 0)
#     sum_of_rings = int(color_counter_black) + int(color_counter_blue) + int(color_counter_yellow) + int(color_counter_red) + int(color_counter_green)
#     # print("sum of ring  = : ",sum_of_rings)


#     if sum_of_rings == 0:
#         return None
#     elif sum_of_rings == 1 :
#         if color_counter_yellow == 1 :
#             return "Flame"
#         else:
#             return None
#     elif sum_of_rings == 5:
#         return "Flame"
#     # cv.imshow("total mask ",total_mask)
#     # cv.waitKey(0)


#     # ------------------------------------------------------------
#     # 7. FIND ALL CONTOURS
#     # ------------------------------------------------------------

#     # Extract contours for each color mask separately and assign numeric labels
#     contours = {
#         0: cv.findContours(img_yellow, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)[0],
#         2: cv.findContours(img_blue,   cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)[0],
#         1: cv.findContours(img_green,  cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)[0],
#         -2: cv.findContours(img_black,  cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)[0],
#         -1: cv.findContours(img_red,    cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)[0],
#     }

#     # Find contours from combined mask
#     total_contour, _= cv.findContours(total_mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)

#     y_contour_top = 0
#     for cnt in total_contour:

#         if cv.contourArea(cnt) < 10:
#             continue

#         # Find top-most point of contour
#         top = cnt[np.argmin(cnt[:, 0, 1])][0]
#         x_contour_top, y_contour_top = top

#         # Convert to warped coordinate space
#         pt = np.array([[[x_contour_top, y_contour_top]]], dtype=np.float32)
#         x_contour_top, y_contour_top = cv.perspectiveTransform(pt, H)[0, 0]
#         # Compute reference height difference between contour system and keypoint
#     outer_ring_y = y_contour_top - warped_keypoint_y

#     # ------------------------------------------------------------
#     # 8. EXTRACT RING HEIGHTS (DISTANCES FROM TOP KEYPOINT)
#     # ------------------------------------------------------------

#     rings = []

#     for color_value, contour_list in contours.items():
#         for cnt in contour_list:
#             # if cv.contourArea(cnt) < 5:
#             #     continue

#             # Extract top-most point of contour
#             top = cnt[np.argmin(cnt[:, 0, 1])][0]
#             x_contour_top, y_contour_top = top

#             # Convert contour point to warped coordinate space
#             pt = np.array([[[x_contour_top, y_contour_top]]], dtype=np.float32)
#             x_contour_top, y_contour_top = cv.perspectiveTransform(pt, H)[0, 0]

#             # Store normalized vertical distance and associated color value
#             rings.append(((y_contour_top - warped_keypoint_y)/outer_ring_y, color_value))


#     # ------------------------------------------------------------
#     # 9. SORT RINGS FROM TOP TO BOTTOM
#     # ------------------------------------------------------------

#     # Sort rings based on vertical position
#     rings.sort(key=lambda x: x[0],reverse=True)

#     # counter = 0
#     # for j in rings:
#     #     if j[0] < 0 :
#     #         rings.pop(counter)
#     #     counter += 1


#     if len(rings) > 5:
#         math_rings = len(rings) - 5
#         for i in range(math_rings):
#             rings.remove(rings[-1])
#             # print("remove : ",rings[-1])


#     # print("Rings (distance, color):", rings)

#     rings.reverse()

#     # ------------------------------------------------------------
#     # 10. COMPUTE SCORE BASED ON RING ORDER
#     # ------------------------------------------------------------

#     total = 0
#     last_y = 0
#     total_steps = 0
#     # max_dist = []
#     for dist, color in rings:
#         # Compute spacing-based step value (requires calibration)
#         step = int(1 + abs(dist - last_y) / 0.28)
#         # max_dist.append((abs(dist - last_y), color))
#         total_steps += step  # spacing logic # must be calibrated
#         # print("step : ",step)
#         # print("abs(dist - last_y) / 0.28 : ",abs(dist - last_y) / 0.28)
#         total += step * color
#         last_y = dist
#         key_detect = True
#     else:
#         if total_steps > 5 :
#             return None
#         elif total_steps < 5 :

#             # max_dist.sort(key=lambda x: x[0])
#             # dist_max = max_dist[-1]


#             # print("TOTAL ======> ", total, (5 - total_steps) * rings[0][1])
#             # print("++++++++++ IM IN STEP IF  < 5++++++++++++")
#             total += int((5 - total_steps) * rings[0][1])
#             # total += int((5 - total_steps) * dist_max[1])
#             # print("TOTAL AFTER ==========> ", total)

#     # print("SUM =", total)

#     if total == 0 and key_detect :
#         return "Flame"
#     elif total == 1 :
#         return "Poison"
#     elif total == 2:
#         return "Corrosive"
#     elif total == 3 :
#         return "Organic"
#     else:
#         RCAM.setFov(fov)
#         FCAM.setFov(fov)
#         LCAM.setFov(fov)
#         return None




# def vision(frame, cam):
#     # #print('------------------------------------------------------------------------------------------------------------')
#     global token_croped, chrono, live_mean, live_sum, loop_counter

#     frame = frame[ :39 ,:]
#     frame_yolo = cv.resize(frame,(32,32))
#     results = yolo_model(frame_yolo)
#     result = get_yolo_data(results) # (classes_name, (x1, y1, x2, y2 ,keypoint_x , keypoint_y), conf, kpts_conf)

#     if result is not None:

#         conf = result[2]
#         victim_class = result[0]
#         keypoint_x,keypoint_y = result[1][4:]
#         kpt_conf = result[3]
#         x1 = result[1][0]
#         x2 = result[1][2]
#         y1 = result[1][1]
#         y2 = result[1][3]

#         token_croped = frame[int(y1):int(y2),int(x1):int(x2)]
#         # print("CLASS VICTIM : " ,victim_class)
#         # print("CONF VICTIM ====== > ", conf )

#         if victim_class != "target":


#             # RCAM.setFov(fov)
#             # FCAM.setFov(fov)
#             # LCAM.setFov(fov)
#             if victim_class == "phi" and conf > 0.84:
#                 victim_class = "H"

#             elif victim_class == "psi" and conf > 0.84:
#                 victim_class = "S"

#             elif victim_class == "omg" and conf > 0.84:
#                 victim_class = "U"
#             else:
#                 # print("+++++++ CLASS NOT FOUND ++++++++++++++ ")
#                 return None


#             acpect = abs((x1-x2)/(y1-y2))

#             if 0.6 > acpect and acpect > 1.5 :
#                 # print(f"---------- ACPECT IS NONE ACPECT : {acpect}--------")
#                 return None


#             mean_x = (x1 + x2) / 2

#             image_ratio = ((mean_x - 16) / 16) * 30

#             box_area = (x2 - x1) * (y2 - y1)
#             area_ratio = box_area/(32*32)

#             lidar_ratio = (image_ratio * area_ratio * 6)

#             # print("LIDAR RATIO ========> " ,lidar_ratio)
#             # print("RAIO ========> ",area_ratio)

#             return ("Final prediction:", victim_class, "Confidence:", conf  , "Camera:", cam , "ratio", lidar_ratio)

#         elif victim_class == "target":
#             # print("CONF BOX TARGET === > ",conf )
#             # print("CONF KEYPOINT : ", kpt_conf)
#             RCAM.setFov(1.5)
#             FCAM.setFov(1.5)
#             LCAM.setFov(1.5)
#             if conf < 0.8 or kpt_conf < 0.7:
#                 # print("CONF IS NONE TARGET")
#                 return None

#             victim_class = detect_circle(frame,keypoint_x,keypoint_y,(x1,x2,y1,y2))


#             # if int(x1)-int(x2) < 6:
#             #     return None

#             if victim_class is not None :

#                 image_ratio = ((keypoint_x - 16) / 16) * 30
#                 # box_area = (x2 - x1) * (y2 - y1)
#                 # area_ratio = box_area / (32*32)
#                 lidar_ratio = (image_ratio * 0.5)

#                 # print("LIDAR RATIO ========> " ,lidar_ratio)
#                 # print("RAIO ========> ",area_ratio)
#                 # print(f"CLASS : {victim_class} - I GO TO REPORT 👍👍",)
#                 return("Final prediction:", victim_class, "Confidence:", conf  , "Camera:", cam ,"ratio", lidar_ratio)
#     # RCAM.setFov(fov)
#     # FCAM.setFov(fov)
#     # LCAM.setFov(fov)

#     return None


def report_token(_type, _pos_x, _pos_y):
    victimType = '?'
    RCAM.setFov(fov)
    FCAM.setFov(fov)
    LCAM.setFov(fov)
    if _type == "Corrosive":
        victimType = bytes('C', "utf-8")
    elif _type == "Poison":
        victimType = bytes('P', "utf-8")
    elif _type == "Organic":
        victimType = bytes('O', "utf-8")
    elif _type == "Flame":
        victimType = bytes('F', "utf-8")
    elif _type == "H":
        victimType = bytes('H', "utf-8")
    elif _type == "S":
        victimType = bytes('S', "utf-8")
    elif _type == "U":
        victimType = bytes('U', "utf-8")
    else:
        pass
    # ## # ## # # # # # # print(_pos_x, _pos_y, victimType, _type)
    message = struct.pack("i i c", _pos_x, _pos_y, victimType)
    emitter.send(message)
    robot.step(timeStep)


def calculate_victim(_cam, _class, lidar_ra):

    # # print("LIDAR RAY : ",lidar_ra)
    # # print("LIDAR DISTANCE : ",rangeImage[lidar_ra])

    if _cam == "l":
        # # print("CAL IAMGE")
        d = rangeImage[lidar_ra]
        if not math.isinf(d) and d < 43:
            # # print("IM IN IF")
            theta = (1024 - lidar_ra) * (360 / 512)
            rad = math.radians(theta)
            x1 = d * math.cos(rad)
            y1 = d * math.sin(rad)
            alpha = math.radians(yaw)
            a, b = localToGlobal(alpha, [x1, y1])
            return (a, b, gps_x, gps_y, _class)

    elif _cam == "r":
        # # print("CAL IAMGE")
        d = rangeImage[lidar_ra]
        if not math.isinf(d) and d < 43:
            # # print("IM IN IF")
            theta = (1024 - lidar_ra) * (360 / 512)
            rad = math.radians(theta)
            x1 = d * math.cos(rad)
            y1 = d * math.sin(rad)
            alpha = math.radians(yaw)
            a, b = localToGlobal(alpha, [x1, y1])
            return (a, b, gps_x, gps_y, _class)

    elif _cam == "f":
        # # print("CAL IAMGE")
        d = rangeImage[lidar_ra]
        if not math.isinf(d) and d < 43:
            # # print("IM IN IF")
            theta = (1024 - lidar_ra) * (360 / 512)
            rad = math.radians(theta)
            x1 = d * math.cos(rad)
            y1 = d * math.sin(rad)
            alpha = math.radians(yaw)
            a, b = localToGlobal(alpha, [x1, y1])
            return (a, b, gps_x, gps_y, _class)


def add_victim_pos(_new):
    global victim_pos_list

    ok_key = True
    for i in victim_pos_list:
        if victim_is_same(i, _new):
            ok_key = False

    if ok_key:
        victim_pos_list.append(_new)

def is_in_vic_pos_list(_input):
    global victim_pos_list

    for i in victim_pos_list:
        if victim_is_same(i, _input):
            return True

    return False


def victim_is_same(_vic1, _vic2):
    # if _vic1[-1] == _vic2[-1]:
    #     if math.sqrt((_vic1[0] - _vic2[0]) ** 2 + (_vic1[1] - _vic2[1]) ** 2) < 2:
    #         if math.sqrt((_vic1[2] - _vic2[2]) ** 2 + (_vic1[3] - _vic2[3]) ** 2) < 7:
    #             return True

    if math.sqrt((_vic1[0] - _vic2[0]) ** 2 + (_vic1[1] - _vic2[1]) ** 2) < 4:
        return True

    return False

def histogram_contrast(img):
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    p5, p95 = np.percentile(gray, (5, 95))
    return p95 - p5

def is_victim_off(img):
    score = histogram_contrast(img[3:15, 3:15])
    # ## # ## # # # # ##### # print("SCORE OF GPTS CODE: ", score)
    if score > 60:
        return False
    else:
        return True

def is_in_off(input_):
    k=0
    for i in  victim_off:

        if victim_is_same(i[0], input_):

            return True , k
        k=k+1
    return False , None




def light_victim(_warp):
    image_hls=cv.cvtColor(_warp,cv.COLOR_BGR2HLS)
    light=image_hls[:,:,1]
    light_mean=np.mean(light)
    return light_mean



def victim_off_add(_frame,_class,_temp,gps):

    if  is_in_vic_pos_list(_temp)==False:


        light=light_victim(_frame)

        br=brightness_level(_frame)

        victim_off.append([_temp,light,_class,1 , br ,gps])
        return True
    return False


def brightness_level(image):
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    return np.mean(gray)






def detect_victim_off(_temp,_victim_list_off,light,_class,warp ,br , gps):
    ## # ## # # # # ##### # print("class :",_class)
    ## # ## # # # # ##### # print(" light ", light)
    ## # ## # # # # ##### # print(_temp)

    if is_in_off(_temp)[0]:
        ## # ## # # # # ##### # print("is in ")
        ik=is_in_off(_temp)[1]
        ## # ## # # # # ##### # print("gps:",math.sqrt(abs((_victim_list_off[ik][5][0] - gps[0])**2 + (_victim_list_off[ik][5][1]-gps[1])**2)))

        ## # ## # # # # ##### # print("class _ on",_victim_list_off[ik][2])
        if  _victim_list_off[ik][3]==1:
            ## # ## # # # # ##### # print(" one is oky")
            if  _victim_list_off[ik][2]==_class:
                ## # ## # # # # ##### # print(" class is ==")
                if abs(_victim_list_off[ik][1]-light)>5:

                    ## # ## # # # # ##### # print("light mean : ",abs(_victim_list_off[ik][1]-light))
                    return True

                elif is_victim_off(warp):
                    ## # ## # # # # ##### # print("is amirsam")
                    return True

                elif abs(br-_victim_list_off[ik][4])>5:
                    ## # ## # # # # ##### # print(" br ")
                    return True


            else:
                if math.sqrt(abs((_victim_list_off[ik][5][0] - gps[0])**2 + (_victim_list_off[ik][5][1]-gps[1])**2))<10:
                    ## # ## # # # # ##### # print(" i am gps")
                    # _victim_list_off[ik][3]=2
                    return True
                _victim_list_off[ik][3]=2

        else:
            ## # ## # # # # ##### # print("is not one and off")
            return True
    ### # ## # # # # ##### # print" is on")
    return False

def time_to_end():
    message = struct.pack('c', 'G'.encode())
    emitter.send(message)

    if receiver.getQueueLength() > 0:
        receivedData = receiver.getBytes()
        tup = struct.unpack('c f i i', receivedData)
        if tup[0].decode("utf-8") == 'G':
            receiver.nextPacket()
            Time_Left = tup[2]
            return Time_Left

def check_emergency_exit():
    global time_key, target_list, state, swamp_target_list

    if ((time_left < 33) and (not time_key)) or ((time_left_real < 33) and (not time_key)):
        target_list = []
        swamp_target_list = []
        state = "choose"
        time_key = True

def is_near(_node):
    # for i in gone_secondary_targets:
    #     if get_distance(_node[0], _node[1], i[0], i[1]) < 1.3:
    #         return True
    for j in secondary_target_list:
        if get_distance(_node[0], _node[1], j[0], j[1]) < 1.69:
            return True

    return False


def game_info():
    global Time_left , key_detect_lop , time_left_counter , time_left_key , Time_left_real

    if time_left_key :
        message = struct.pack('c', 'G'.encode())
        emitter.send(message)

    if receiver.getQueueLength() > 0:


        if time_left_key :

            receivedData = receiver.getBytes()
            rDataLen = len(receivedData)
            if rDataLen == 16:
                tup = struct.unpack('c f i i', receivedData)
                if tup[0].decode("utf-8") == 'G':
                    Time_left = tup[2]
                    Time_left_real = tup[3]
                    time_left_key = False

        # receiver.nextPacket()




        lastRequestTime = robot.getTime()
        receivedData = receiver.getBytes()
        rDataLen = len(receivedData)
        if rDataLen == 1:
            tup = struct.unpack('c', receivedData)
            if tup[0].decode("utf-8") == 'L':
                key_detect_lop = True
        receiver.nextPacket() # Discard the current data packet


def detect_rotation_for_IveJustReported():
    global Ivejustreported_front, Ivejustreported_left, Ivejustreported_right, reportation_angle_front, reportation_angle_left, reportation_angle_right

    if Ivejustreported_front:
        if abs(reportation_angle_front-yaw)<=180 and reportation_angle_front>=yaw:
            error=reportation_angle_front-yaw
        elif abs(reportation_angle_front-yaw)>180 and reportation_angle_front>=yaw:
            error=reportation_angle_front-yaw-360
        elif abs(reportation_angle_front-yaw)<=180 and reportation_angle_front<yaw:
            error=reportation_angle_front-yaw
        else:
            error=reportation_angle_front-yaw+360

        if abs(error) > 60:
            Ivejustreported_front = False


    if Ivejustreported_left:
        if abs(reportation_angle_left-yaw)<=180 and reportation_angle_left>=yaw:
            error=reportation_angle_left-yaw
        elif abs(reportation_angle_left-yaw)>180 and reportation_angle_left>=yaw:
            error=reportation_angle_left-yaw-360
        elif abs(reportation_angle_left-yaw)<=180 and reportation_angle_left<yaw:
            error=reportation_angle_left-yaw
        else:
            error=reportation_angle_left-yaw+360

        if abs(error) > 60:
            Ivejustreported_left = False

    if Ivejustreported_right:
        if abs(reportation_angle_right-yaw)<=180 and reportation_angle_right>=yaw:
            error=reportation_angle_right-yaw
        elif abs(reportation_angle_right-yaw)>180 and reportation_angle_right>=yaw:
            error=reportation_angle_right-yaw-360
        elif abs(reportation_angle_right-yaw)<=180 and reportation_angle_right<yaw:
            error=reportation_angle_right-yaw
        else:
            error=reportation_angle_right-yaw+360

        if abs(error) > 60:
            Ivejustreported_right = False

last_gps_x = 0.0
last_gps_y = 0.0

last_point_cloud_x = []
last_point_cloud_y = []

last_enc_r = 0.0
last_enc_l = 0.0

last_t_data = 0.0

last_yaw_data = 0

first_time_data = True

def save_slam_data():
    global last_gps_x, last_gps_y, delta_x_label, delta_y_label, last_point_cloud_x, last_point_cloud_y, last_enc_r, last_enc_l, last_t_data, last_yaw_data

    sample = []

    delta_x_label = gps_x - last_gps_x
    delta_y_label = gps_y - last_gps_y


    now_point_cloud_x = []
    now_point_cloud_y = []

    difference_point_cloud_x = []
    difference_point_cloud_y = []
    for i in range(1024, 1536):
        d = rangeImage[i]
        if not math.isinf(d):
            d = d * math.cos(0.069045/2)
            theta = (1024 - i) * (360.0 / 512.0)
            rad = math.radians(theta)
            x1 = d * math.cos(rad)
            y1 = d * math.sin(rad)
            now_point_cloud_x.append(x1)
            now_point_cloud_y.append(y1)
            if len(last_point_cloud_x) == 512:
                difference_point_cloud_x.append(x1 - last_point_cloud_x[i-1024])
                difference_point_cloud_y.append(y1 - last_point_cloud_y[i-1024])
        else:
            now_point_cloud_x.append(200.0)
            now_point_cloud_y.append(200.0)
            if len(last_point_cloud_x) == 512:
                difference_point_cloud_x.append(200.0 - last_point_cloud_x[i-1024])
                difference_point_cloud_y.append(200.0 - last_point_cloud_y[i-1024])

    enc_r = encoder_right.getValue()
    enc_l = encoder_left.getValue()

    delta_enc_r = (enc_r - last_enc_r) * 2.0
    delta_enc_l = (enc_l - last_enc_l) * 2.0

    delta_t_data = robot.getTime() - last_t_data

    delta_yaw = yaw - last_yaw_data

    if first_time_data:
        first_time_data = False
    else:
        sample = [delta_x_label] + [delta_y_label] + now_point_cloud_x + now_point_cloud_y + last_point_cloud_x + last_point_cloud_y + difference_point_cloud_x + difference_point_cloud_y + [yaw] + [delta_enc_r] + [delta_enc_l] + [speed_right.getVelocity()] + [speed_left.getVelocity()] + [robot.getTime()] + [delta_t_data] + [gps_x] + [gps_y]

    with open(csv_filename, 'a') as f:
        np.savetxt(f, [sample], delimiter=',', fmt='%f')
    # # # ##### # print("Data Saved: ", loop_counter)

    last_t_data = robot.getTime()

    last_gps_x = gps_x
    last_gps_y = gps_y

    last_point_cloud_x = now_point_cloud_x
    last_point_cloud_y = now_point_cloud_y

    last_enc_r = enc_r
    last_enc_l = enc_l

    last_yaw_data = yaw


def angle_to_lidar_ray(angle, cam):
    # angle = math.degrees(angle)

    if cam == "r":
        angle += 90
    elif cam == "l":
        angle -= 90

    if angle < 0:
        angle += 360
    elif angle >= 360:
        angle -= 360

    # # print("....MY ANGLE IN PROBLEMS....")
    index = int(angle/360 * 512)

    # # print("LIDAR RY : ",index + 1024)
    return (index + 1024)


def detect_obs_vision(cam):
    global Map_Obstacle
    counter_obs_right = 0
    counter_obs_left = 0
    counter_obs_front = 0
    if cam == "l" and rangeImage[1408] < 18:
        for i in range(38):
            for j in range(2):

                if  np.array_equal(detect_color('l', i,16+j), [134, 134 ,134]) or np.array_equal(detect_color('l', i,16+j), [29, 29 ,29]) or np.array_equal(detect_color('l', i,16+j), [95, 95 ,95]) or np.array_equal(detect_color('l', i,16+j), [122, 122 ,122]) or np.array_equal(detect_color('l', i,16+j), [127, 127 ,127]) or np.array_equal(detect_color('l', i,16+j), [81, 81 ,81]) or np.array_equal(detect_color('l', i,16+j), [112, 112 ,112]) or np.array_equal(detect_color('l', i,16+j), [132, 132  ,132]) or np.array_equal(detect_color('l', i,16+j), [182, 182 ,182]):
                    counter_obs_left += 1

    if cam == "r" and rangeImage[1152] < 18:
        for i in range(38):
            for j in range(2):
                if  np.array_equal(detect_color('r', i,16+j), [134, 134 ,134]) or np.array_equal(detect_color('r', i,16+j), [29, 29 ,29]) or np.array_equal(detect_color('r', i,16+j), [95, 95 ,95]) or np.array_equal(detect_color('r', i,16+j), [122, 122 ,122]) or np.array_equal(detect_color('r', i,16+j), [127, 127 ,127]) or np.array_equal(detect_color('r', i,16+j), [81, 81 ,81]) or np.array_equal(detect_color('r', i,16+j), [112, 112 ,112]) or np.array_equal(detect_color('r', i,16+j), [132, 132  ,132]) or np.array_equal(detect_color('r', i,16+j), [182, 182 ,182]):
                    counter_obs_right += 1

    if cam == "f" and rangeImage[1024] < 18:
        for i in range(38):
            for j in range(2):
                if  np.array_equal(detect_color('f', i,16+j), [134, 134 ,134]) or np.array_equal(detect_color('f', i,16+j), [29, 29 ,29]) or np.array_equal(detect_color('f', i,16+j), [95, 95 ,95]) or np.array_equal(detect_color('f', i,16+j), [122, 122 ,122]) or np.array_equal(detect_color('f', i,16+j), [127, 127 ,127]) or np.array_equal(detect_color('f', i,16+j), [81, 81 ,81]) or np.array_equal(detect_color('f', i,16+j), [112, 112 ,112]) or np.array_equal(detect_color('f', i,16+j), [132, 132  ,132]) or np.array_equal(detect_color('f', i,16+j), [182, 182 ,182]):
                    counter_obs_front += 1
                # ##### # print("i : ",i,16+j)
    # ##### # print(counter_abs)
    # ##### # print("👍 counter right ==> ", counter_obs_right)
    # ##### # print("👍 counter left ==> ", counter_obs_left)
    # ##### # print("👍 counter front ==> ", counter_obs_front)
    if counter_obs_right >= 10:
        d = rangeImage[1152]
        d = d * math.cos( (0.2 / 3.0) / 2)
        theta = ((1024 - 1152) * (360.0 / 512.0)) - 0.3515625 - (0.3515625 / 2.0)
        rad = math.radians(theta)
        x1 = d * math.cos(rad)
        y1 = d * math.sin(rad)
        a, b = localToGlobal(math.radians(yaw), [x1, y1])
        Map_Obstacle[gps_to_map((a,b))[0]][gps_to_map((a,b))[1]] = 255

    if counter_obs_left >= 10:
            d = rangeImage[1408]
            d = d * math.cos( (0.2 / 3.0) / 2)
            theta = ((1024 - 1408) * (360.0 / 512.0)) - 0.3515625 - (0.3515625 / 2.0)
            rad = math.radians(theta)
            x1 = d * math.cos(rad)
            y1 = d * math.sin(rad)
            a, b = localToGlobal(math.radians(yaw), [x1, y1])
            Map_Obstacle[gps_to_map((a,b))[0]][gps_to_map((a,b))[1]] = 255

    if counter_obs_front >= 10:
            d = rangeImage[1024]
            d = d * math.cos( (0.2 / 3.0) / 2)
            theta = ((1024 - 1024) * (360.0 / 512.0)) - 0.3515625 - (0.3515625 / 2.0)
            rad = math.radians(theta)
            x1 = d * math.cos(rad)
            y1 = d * math.sin(rad)
            a, b = localToGlobal(math.radians(yaw), [x1, y1])
            Map_Obstacle[gps_to_map((a,b))[0]][gps_to_map((a,b))[1]] = 255

fov = 1
start = robot.getTime()
while robot.step(timeStep) != -1:
    chrono = time.time()

    # ## # ## # # # # ##### # print("state: ", state)

    if first_time:
        fov = FCAM.getFov()
        stop()
        start_gps()
        for i in range(order):
            gps_filtered_x.append(0.0)
            gps_filtered_y.append(0.0)
            gps_filtered_z.append(0.0)
            gps_list_x.append(0.0)
            gps_list_y.append(0.0)
            gps_list_z.append(0.0)


        update_data()
        lidar(yaw)
        append_targets()
        append_nodes()
        # vision(frame_f, "f")
        first_time = 0
        Tile_array[gps_to_tile((gps_x, gps_y))[0]][gps_to_tile((gps_x, gps_y))[1]] = 1
        for i in range(recent_size):
            recent_visited_tiles.append((ARRAY_SIZE // 2, ARRAY_SIZE // 2))
            recent_visited_nodes.append((ARRAY_SIZE // 2, ARRAY_SIZE // 2))
    if (state != "report_victim") and (state != "report map bonus"):
        game_info()
        LOP()
        # get_left_time()
    update_data()


    check_emergency_exit()

    detect_obs_vision("f")
    detect_obs_vision("l")
    detect_obs_vision("r")


    if (abs(roll - 180) < 0.5) and (abs(pitch - 180) < 0.5):
        lidar(yaw)

    # # print("state: ", state)

    if state == "append" :
        state = "pop"
        if not time_key:
            append_targets()
            append_nodes()
        # # print("Target List: ", target_list)

    elif state == "choose" :
        Key_LOP = True
        if target_list:
            global_target = target_list[-1]
            # # print("choose: ", global_target)
            state = "a-star"
        else:
            if not swamp_target_list:
                target_list.append((ARRAY_SIZE//2, ARRAY_SIZE//2))
                exit_key = True
            else:
                target_list.append(swamp_target_list.pop())

    elif state == "a-star":
        # # print("in Astar")
        planned_path = A_star(my_node, global_target)
        # # print("planned path: ", planned_path)
        if planned_path == []:
            # # print("NO PATH! target ", global_target, " has been removed")
            target_list.remove(global_target)
        state = "pop"

    elif state == "pop":
        # # print("in pop planned path: ", planned_path)
        if planned_path:
            node_local_target = planned_path[-1]
            if type(planned_path[-1][0]) == int or type(planned_path[-1][1]) == int :
                local_target = tile_to_gps(planned_path.pop())
            else :
                local_target = planned_path.pop()
            # # print("local target: ", gps_to_tile(local_target), "     current place: ", gps_to_tile((gps_x, gps_y)))
            state = "gotoXY"
        else :
            state = "choose"
            # append_targets()
            # ## # ## # # # # ####("_________________________________", target_list, "______________________________")
            if exit_key:
                #
                state = "exit"

    elif state == "gotoXY":
        ("...........going to", gps_to_tile(local_target))

        colored_tile()
        detect_rotation_for_IveJustReported()
        if go_to_xy(local_target):
            if type(my_node[0]) == float or type(my_node[1]) == float:
                gone_secondary_targets.append(my_node)
            my_node = node_local_target
            ("I reached ", gps_to_tile(local_target))
            update_FIFO(gps_to_tile(local_target))
            update_recent_nodes(my_node)
            detect_room()
            Room_tile_array[recent_visited_tiles[3][0], recent_visited_tiles[3][1]] = room
            state = "append"
            # state = "pop"
            Ivejustreported_left = False
            Ivejustreported_right = False
            if my_node in target_list :
                target_list.remove(my_node)
            Tile_array[gps_to_tile((gps_x, gps_y))[0]][gps_to_tile((gps_x, gps_y))[1]] = 1

        hole()

        if detect_stuck():
            # # print("stuck detected!")
            state = "stuck"

    elif state == "exit":
        emitter.send(bytes('E', "utf-8"))

    elif state == "avoid hole":
        # # ## # # # # ##### # print("in avoid hole state")
        stop()
        planned_path = []
        state = "choose"

    elif state == "stuck":
        stop()
        planned_path = []
        # print("I want to remove edge:  ", my_node, "  To:  ", node_local_target)
        if G.has_edge(my_node, node_local_target):
            # G.remove_edge(my_node, node_local_target)
            weight = G[my_node][node_local_target]["weight"]
            G.add_edge(my_node, node_local_target, weight=weight * 999999999)
        # print("STUCK! I removed ", node_local_target)
        if node_local_target in target_list:
            # print("I removed:  ", node_local_target)
            target_list.remove(node_local_target) #TODO: Pay attention this truely do not solve the problem
        if len(recent_visited_nodes) > 2:
            global_target = recent_visited_nodes[-2]
        # # print("I want to go back to ", global_target)
        # state = "a-star"
        state = "go_to_xy backward"

    elif state == "go_to_xy backward":
        # # print("in backward")
        if type(global_target[0]) == int or type(global_target[1]) == int:
            # # # print("INT")
            if go_to_xy_backward(tile_to_gps(global_target)):
                stop()
                state = "choose"
        else:
            ### # ## # # # # ##### # print"FLOAT")
            if go_to_xy_backward(global_target):
                stop()
                state = "choose"

    elif state == "remote":
        if keyboard.is_pressed("p"):
            RCAM.setFov(1.5)
            FCAM.setFov(1.5)
            LCAM.setFov(1.5)


        if keyboard.is_pressed("o"):
            RCAM.setFov(0.5)
            FCAM.setFov(0.5)
            LCAM.setFov(0.5)

        # if keyboard.is_pressed("l"):
        #     # LCAM.setExposure(0.1)
        #     # FCAM.setExposure(0.1)
        #     # RCAM.setExposure(0.1)



        if detect_stuck():
            # # # # ##### # print("STUCK")
            pass
        remote_control(1.0)
        # ## # ## # # # # ##### # print("pixel: ", frame_f[39][20], "     lidar: ", rangeImage[1024])

    # elif state == "secondaryTarget":
    #     secondary_pos = secondary_target_list.pop()
    #     if go_to_xy(secondary_pos):




    # if delay(2):
    #     first_time_delay = True
    #     first_Time = 0
    #     Ivejustreported = False
    # Map2 = Map[up:down, left:right]
    # Map2 = Map_Bonus[up:down, left:right]
    Map2 = color_array[up:down, left:right]


    if Map2.size != 0:
        # Map3=cv.GaussianBlur(Map2,(3,3),20)
        # Map3=cv.Canny(Map3,0,255)
        Map3 = cv.resize(Map2, (700, 700))
        cv.imshow("frame", Map3)
        cv.waitKey(1)
    else:
        cv.imshow("frame", Map)
        cv.waitKey(1)

    # cv.imshow("fr", frame_r)
    # cv.imshow("ff", frame_f)
    # cv.imshow("fl", frame_l)
    # cv.waitKey(1)


    find_up_left()
    find_down_right()

    # ## # ## # # # # ##### # print("loop time: ", (time.time() - chrono) * 1000)
    loop_counter += 1
    live_sum += ((time.time() - chrono) * 1000)
    live_mean = live_sum / loop_counter
    # ## # ## # # # # ##### # print(victim_off)
    # ## # ## # # # # ##### # print("live mean: ", live_mean)
    # ## # ## # # # # ##### # print("state : ", state)
    # ##### # print("loop time : ", ((time.time() - chrono) * 1000))
    # ##### # print("STATE =====>", state)
    # ##### # print((time.time() - chrono) * 1000, "\t", live_mean)
    # # ## # ## # # # # ##### # print(victim_pos_list)
    # # ## # # # # ##### # print("room: ", room)
    # ##### # print((victim_pos_list))
    # # ## # ## # # # # ##### # print("Secondary: ", secondary_target_list)

    # # ## # ## # # # # ##### # print("recent visited tiles: ", recent_visited_tiles)
    # # ## # ## # # # # ##### # print("oranges: ", orange_list)
    # # ## # ## # # # # ##### # print("pixel: ", frame_f[39][20])
    # # 1024 : front - 1152: right - 1280: back - 1408: left
    # ##### # print("lidar: ", rangeImage[1024])
    # # # ## # # # # ##### # print(target_list)

    # # ## # ## # # # # ##### # print("green list: ", green_list)
    # ## # ## # # # # ##### # print("time left : " , Time_left)
    # # # ## # # # # ##### # print("red list: ", red_list)
    # # # ## # # # # ##### # print("orange list: ", orange_list)
    # # ## # # # # ##### # print(Tile_array[394:399, 398:403])
    # # ## # # # # ##### # print("state: ", state)
    # # ## # # # # ##### # print("target_list: ", target_list)
    # # ## # # # # ##### # print("tareget_list: ", target_list)
    # IIII = Map[12180: 12180+240, 12000-420: 12000-420+120]
    # cv.imshow("part", IIII)
    # cv.waitKey(1)
    # # ## # # # # ##### # print(hole_check_region_counter)
    # # # # # # ##### # print("ارتین شما ")
    # # # # # # ##### # print("list_x : ", gps_list_x[-1])
    # # # # # # ##### # print("list_y : ", gps_list_y[-1])
    # # # # # # ##### # print("list_z : ", gps_list_z[-1])
    # # # # # # ##### # print("x : ", startx)
    # # # # # # ##### # print("y : ", starty)
    # # # # # # ##### # print("z : ", startz)
    # # # # # # ##### # print("x : ", gps_x, "\t", "y : ", gps_y)
    # # # # # # ##### # print(gps_x, "\t", gps_y)
    # # # # # ##### # print("MM X : ", x_motion_model , "\t", "MM Y : ", y_motion_model)
    # # # # # ##### # print("GPS X : ", (gps_x, gps_y))
    # # # # ##### # print("stuck detector: ", stuck_counter)
    # # # # ##### # print("truth score: ", truth_score)
    # # # # ##### # print(encoder_right.getValue(), '\t', encoder_left.getValue())
    # # # # ##### # print(x_motion_model, '\t', y_motion_model)
    # # # # ##### # print(min(rangeImage[1024 : 1536]) * math.cos(0.069045/2))
    # # # # ##### # print(gps_x, '\t', gps_y)
    # lidarPoints = LIDAR.getPointCloud()
    # # # # ##### # print(lidarPoints[1024].x * 100.0, '\t', lidarPoints[1024].y * 100.0, '\t', lidarPoints[1024].z * 100.0)
    # loop_cnt += 1
    # if (loop_cnt > 2):
    #     loop_cnt = 0
    #     # # # ##### # print("yaw: ", yaw)
    #     for i in range(1024, 1536):
    #         # # # # ##### # print(lidarPoints[i].x * 100.0, '\t', lidarPoints[i].y * 100.0)
    #         d = rangeImage[i]
    #         if not math.isinf(d):
    #             d = d * math.cos(0.069045/2)
    #             theta = (1024 - i) * (360 / 512)
    #             rad = math.radians(theta)
    #             x1 = d * math.cos(rad)
    #             y1 = d * math.sin(rad)
    #             # # # ##### # print(x1, '\t', y1)
    #         else:
    #             # # # ##### # print("inf", '\t', "inf")
    #     # # # ##### # print("######################################")
    # save_slam_data()
    # # # # ##### # print(GPS.getSpeedVector())
    # # # ##### # print("LiDAR: ", rangeImage[1024])
    # # # ##### # print("Cam: ", frame_f[0][16])
    # ##### # print(swamp_list)
    # ##### # print("👍 lidar ==> ", rangeImage[1408])
    # ##### # print("camera left[20][16] ==> ", frame_l[20][16])
    #### # print("room: ", room)
    #### # print("red list: ", red_list)
    #### # print("check point list: ", checkpoint_list)
    # ## # print("center of first swamp: ", Colored_tile_array[144][140], "       center of second swamp: ", Colored_tile_array[152][156])
    # ## # print("swamp_list: ", swamp_list)
    # ## # print(rangeImage[1408], '\t', frame_l[15][16])
    # print(global_target)
