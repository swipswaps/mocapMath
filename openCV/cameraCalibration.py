import os
import sys
import csv
import tkinter as tk
from tkinter import filedialog
import lox
import cv2
import numpy

# Configure Tkinter
root = tk.Tk()
root.withdraw()

# File Management
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Import Sensor Database
SENSORS = []
with open(resource_path("./sensors.csv"), newline='') as database:
    data = csv.reader(database)
    for sensor in data:
        SENSORS.append(sensor)
SENSORS.pop(0)

imageDir = filedialog.askdirectory(title="Select Directory")

COUNT = 0
QUENE = len(os.listdir(imageDir))
PATTERN = (9, 7)

def makeChessboard(col, row):
    x = 0
    y = 0
    chessboard = []

    while y < row:
        while x < col:
            chessboard.append((x, y, 0))
            x = x + 1
        y = y + 1
        x = 0

    return chessboard

thread = int(os.cpu_count() / 2)

@lox.thread(thread)
def detectCorners(imagePath, imgFile):
    global COUNT

    imgC = cv2.imread(imagePath)
    found, intersects = cv2.findChessboardCorners(imgC, PATTERN, flags=cv2.CALIB_CB_FAST_CHECK)

    corners = []

    if found is True:
        for group in intersects:
            for intersect in group:
                corners.append((intersect[0], intersect[1]))
        COUNT += 1
        sys.stdout.write("\r{:02d} of {} | {} Processed        ".format(COUNT, QUENE, imgFile))
        sys.stdout.flush()
        return corners
    else:
        COUNT += 1
        sys.stdout.write("\r{:02d} of {} | {} Failed        ".format(COUNT, QUENE, imgFile))
        sys.stdout.flush()
        return [False, imgFile]

# Variables for Camera Calibration from Corner Detection
BOARD = makeChessboard(PATTERN[0], PATTERN[1])
objectPoints = []
imgPoints = []
success = 0
errors = 0

# Start Threads for Corner Detection
for image in os.listdir(imageDir):
    img = os.path.join(imageDir, image)
    detectCorners.scatter(img, image)

# Collect and Verify Corner Data from Threads
imgProcess = detectCorners.gather()

print("")

for result in imgProcess:
    if result[0] is not False:
        imgPoints.append(result)
        objectPoints.append(BOARD)
        success += 1
    else:
        errors += 1
        print("{} failed.".format(result[1]))

print("\n--- Corner Detection Results ---\nSuccess: {}\nFail: {}\n".format(success, errors))

# Convert to Numpy Arrays
oPts = numpy.array(objectPoints)
iPts = numpy.array(imgPoints)
objects = oPts.astype('float32')
images = iPts.astype('float32')

# User Selects Camera Sensor
print("\n--- Camera Sensor Sizes ---")
print("## |  Width | Height | Cameras")
for config in SENSORS:
    print("{: 2d} | {: 6.2f} | {: 6.2f} | {}".format(int(config[0]), float(config[1]), float(config[2]), config[3]))
sensorSelection = input("\nWhich ## corresponds to your camera's sensor? ")
while True:
    try:
        SENSORS[int(sensorSelection)]
        break
    except IndexError:
        sensorSelection = input("[!] (Invalid Input) Which ## corresponds to your camera's sensor? ")

if int(sensorSelection) != 0:
    SENSOR = (float(SENSORS[int(sensorSelection) - 1][1]), float(SENSORS[int(sensorSelection) - 1][2]))
else:
    customSensorX = input("Custom Sensor Size Width in mm: ")
    while True:
        try:
            customSensorX = float(customSensorX)
            break
        except ValueError:
            customSensorX = input("[!] (Invalid Input) Custom Sensor Size Width in mm: ")
    customSensorY = input("Custom Sensor Size Height in mm: ")
    while True:
        try:
            customSensorY = float(customSensorY)
            break
        except ValueError:
            customSensorY = input("[!] (Invalid Input) Custom Sensor Size Height in mm: ")
    SENSOR = (customSensorX, customSensorY)

# Detect Image Dimensions and Adjust Sensor if Neccessary
sizeImg = cv2.imread(os.path.join(imageDir, os.listdir(imageDir)[0]))
size = sizeImg.shape
dimensions = (size[1], size[0])
rawSensor = SENSOR
if size[1] / size[0] != SENSOR[0] / SENSOR[1]:
    SENSOR = (SENSOR[0], (size[0] * SENSOR[0]) / size[1])
    if SENSOR[1] > rawSensor[1]:
        sensorH = rawSensor[1]
        SENSOR = ((sensorH * size[1]) / size[0], sensorH)
    print("Effective Sensor Size Calculated as {:4.2f} mm x {:4.2f} mm".format(SENSOR[0], SENSOR[1]))

# Camera Matrix Calculations
initialMatrix = cv2.initCameraMatrix2D(objects, images, dimensions)
error, matrix, distortion, rotation, translation = cv2.calibrateCamera(objects, images,
                                                                       dimensions, initialMatrix,
                                                                       None)

print("\n\n--- Camera Matrix Calculations ---\nError: {:.4f} px".format(error))

fov = [None, None]
fov[0], fov[1], focal, principal, ratio = cv2.calibrationMatrixValues(matrix, dimensions,
                                                                      SENSOR[0], SENSOR[1])

print("Focal Length: {:.4f} mm\n".format(focal))
