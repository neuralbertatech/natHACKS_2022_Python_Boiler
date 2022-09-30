"""
This is the right task
- it displays either a blue or green circle and records when user hits space
it pumps data about what happens when to an lsl stream
it also receive eeg data from a muse, or simulates it
This data is recorder along with events
EVENT KEY:
0 - Begin trial
1 - left color displayed (blue)
2 - right color displayed (green)
3 - user pressed space
11 - end trial
It contains partially complete code to graph ERP afterwards.
The data is stored with tines leftized (timestamp 0 when stim first displayed, for each trial)
so setting up an ERP graph should be reasonably simple
Project ideas: any project where the user sees something displayed and interacts with it, while eeg is recorded

Madeleine
65/66 init param object

110-114 init board object + begin stream

214 - get data from board at end of baseline

220 - write data to file

"""

import csv
import logging
import random
import sys
import time

from functools import partial

import pygatt
# import collections
import struct

import numpy as np
from PyQt5 import Qt, QtCore, QtGui
from PyQt5.QtCore import QTimer  # Qt,
from PyQt5.QtGui import QBrush, QFont, QPainter, QPen, QPolygon, QMovie
from PyQt5.QtOpenGL import *
from PyQt5.QtWidgets import *

log_file = "boiler.log"
logging.basicConfig(level=logging.INFO, filemode="a")

f = logging.Formatter(
    "Logger: %(name)s: %(levelname)s at: %(asctime)s, line %(lineno)d: %(message)s"
)
stdout = logging.StreamHandler(sys.stdout)
boiler_log = logging.FileHandler(log_file)
stdout.setFormatter(f)
boiler_log.setFormatter(f)

logger = logging.getLogger("BaselineWindow")
logger.addHandler(boiler_log)
logger.addHandler(stdout)
logger.info("Program started at {}".format(time.time()))


class IMUbaseline_win(QWidget):
    def __init__(
        self,
        parent=None,
        csv_name=None,
        arduino_serial_port=None
    ):
        super().__init__()
        self.csv_name = csv_name[:-4] + "_" + str(int(time.time())) + ".csv"
        self.parent = parent
        self.arduino_serial_port=arduino_serial_port

        self.imu_count = 1

        self.data = [[] for x in range(self.imu_count)]
        # self.data = []

        self.imu_dict = {
            0: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : '917649A1-D98E-11E5-9EEC-0002A5D5C51B'
            },   
            1: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D69'
            },
            2: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : '917649A1-D98E-11E5-9EEC-0002A5D5C51B'
            },   
            3: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D69'
            },
            4: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : '917649A1-D98E-11E5-9EEC-0002A5D5C51B'
            },   
        }


        # self.address = '0A:54:F1:E2:B3:C1'

        # self.address = []

        self.rawData = bytearray(4)
        self.value = None
        self.is_subscribed = False
        self.is_receiving = False
        # self.previousTimer = 0
        self.read_UUID = "C8F88594-2217-0CA6-8F06-A4270B675D69"
        self.prevTime = time.time()

        self.count = 0

        if self.parent.debug == True:
            # BoardShim.enable_dev_board_logger()
            print("DEBUG == True")

        self.setMinimumSize(600, 600)
        self.setWindowIcon(QtGui.QIcon("utils/logo_icon.jpg"))

        # setting window title
        self.setWindowTitle("Baseline Window")

        # init layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # Define widget for the gif movie
        self.movieLabel = QLabel(self)
        self.movieLabel.setGeometry(QtCore.QRect(25, 25, 512, 512))
        self.movieLabel.setMinimumSize(QtCore.QSize(512, 512))
        self.movieLabel.setMaximumSize(QtCore.QSize(512, 512))
        self.movieLabel.setObjectName("lb1")
        self.layout.addWidget(self.movieLabel)  

        # self.movie = QMovie("curl_in.gif")
        # self.movieLabel.setMovie(self.movie)

        self.stim_type = {"left": 1, "right": 2}

        # whether to actually display a stimulus of specified color
        self.show_stim = False

        # by default we are going to have the classifier predict Right Arm as the correct
        # give a graded - provide stimulation when the probability is above a set threshold of 90%
        # need to save model and then reload when starting session

        self.stim_str = ["Left Arm", "Right Arm"]

        self.stim_dict = {
            0 : {
                'movie_file' : 'curl_in.gif',
                'stim_str' : 'Curl In',
                'trigger' : 1000
            },
            1 : {
                'movie_file' : 'forward_reach.gif',
                'stim_str' : 'Forward Reach',
                'trigger' : 1001
            },
            2 : {
                'movie_file' : 'lift_in.gif',
                'stim_str' : 'Lift In',
                'trigger' : 1002
            },
            3 : {
                'movie_file' : 'raise_outside.gif',
                'stim_str' : 'Raise Outside',
                'trigger' : 1003
            },
            4 : {
                'movie_file' : 'reach_up.gif',
                'stim_str' : 'Reach Up',
                'trigger' : 1004
            },
            5 : {
                'movie_file' : 'touch_nose.gif',
                'stim_str' : 'Touch Nose',
                'trigger' : 1005
            },
        }

        # let's start eeg receiving!
        # self.board = Board(board_id=self.board_id)
        # self.hardware_connected = True

        # now we can init stuff for our trials
        # trials is a list of random or addball in the order that we will use them (randomized, 50% right)
        self.total_trials = 10
        right_trials = self.total_trials // 2
        left_trials = self.total_trials - right_trials
        self.trials = [self.stim_type["left"]] * left_trials + [
            self.stim_type["right"]
        ] * right_trials
        random.shuffle(self.trials)
        logging.info("trials {}".format(self.trials))
        self.curr_trial = 0
        # this is whether or not we've gone through all our trials yet
        self.finished = False
        # need to prime the first without moving index up incase the paint event is too quick
        self.stim_code = self.trials[0]

        # now we display the instructions
        self.running_trial = False
        self.display_instructions()

        # state for if the user is current in a responding period
        self.responding_time = False

        # max time window for participants to respond
        self.stim_wait_max = 2

        # end trigger
        # self.end_trig = 11

        # since we can't capture the evnt loop while displaying stimulus we will use a timer

        # the timer is an object that creates timeout events at regular intervals after it's started with timer.start(# ms to run for)
        # in this case, it's a single shot timer and we start it manually
        self.stim_timer = QTimer()
        # making it a precision timer
        self.stim_timer.setTimerType(0)
        self.stim_timer.setSingleShot(True)
        # setting the function to call when it times out
        # IMPORTANT: to change the function it calls, must first use timer.disconnect() to remove the previous one
        # otherwise will call both new and old fucntions
        self.stim_timer.timeout.connect(self.end_stim)

        # To ensure we dont try to close the object a second time
        self.is_end = False


        '''
        Need to turn IMU init into an iterative process to go through connecting and subscribing to each of the x number of IMUs (self.imu_count)
        
            You can't define a function using a variable but you can rebind the function to the variable name. Here is an example to add them to the module's global namespace.

            def callback(handle, data, extra_arg):
                    pass

            sausage_callback = partial(callback, 'new_argument')
            backend.subscribe(uuid, callback=sausage_callback)


            Would first need to iteratively define all the subscribeCallback_x to plug data into different parts of the data list and put all those functions into a list

            Then iterate through and connect + subscribe (with grab the specific callbacks for the given device)
            

        '''

        for x in range(self.imu_count):
            self.adapter = pygatt.BGAPIBackend(serial_port=self.arduino_serial_port) #virtual COM port for the BlueGiga dongle
            print('Trying to connect to: ' + str(self.arduino_serial_port) + ' at ' + str(self.imu_dict[x]['address']))
            # Attempt to connect to the device
            try:
                self.adapter.start()
                self.device = self.adapter.connect(self.imu_dict[x]['address']) 
                print(self.device)
                print('Connected!')
            except(pygatt.exceptions.NotConnectedError):
                print('Failed to connect to: ' + str(self.arduino_serial_port) + ' at ' + str(self.imu_dict[x]['address']))

            # def readStart(self):
            # try:
            self.device.subscribe(self.imu_dict[x]['read_UUID'], callback=self.subscribeCallback(x), indication=False, wait_for_response=True)
            print("successfully to subscribe to read_UUID")
            self.is_subscribed = True
            # except:
            #     print("failed to subscribe to read_UUID")

    def subscribeCallback(self, handle, value):
        print("value passed to {}".format(x))
        self.count += 1
        if self.is_receiving == False:
            time.sleep(1)
            print(handle)
            print(value)
            self.is_receiving = True
            print("self.is_receiving == True")
        else:
            self.value = struct.unpack('3f', value)    # use 'h' for a 2 byte integer, 'f' for four
            self.data.append(self.value)    # we get the latest data point and append it to our array
        
            if self.count % 200 == 0:
                print(self.data)

    def set_movie(self):
        # Loading the GIF
        # self.movie = QMovie(self.stim_dict[self.stim_code]['movie_file'])
        print(self.stim_dict[self.stim_code]['movie_file'] * 100)
        self.movie = QMovie("curl_in.gif")
        self.movieLabel.setMovie(self.movie)
        self.movieLabel.show()
        self.movie.start()


    def start_stim(self):
        logging.info("starting stim")
        self.show_stim = True
        # stim_wait = time.time()
        self.responding_time = True

        self.set_movie()

        # self.board.insert_marker(self.stim_code)
        logging.info("debug")
        self.stim_timer.timeout.disconnect()
        self.stim_timer.timeout.connect(self.end_stim)
        self.stim_timer.start(3000)
        self.update()

    def end_stim(self):
        logging.info("ending stim")
        self.responding_time = False
        self.show_stim = False
        # self.board.insert_marker(self.end_trig)
        self.update()

        self.movie.stop()
        self.movieLabel.hide()

        self.stim_timer.timeout.disconnect()
        self.stim_timer.timeout.connect(self.start_trial)
        self.stim_timer.start(1000)

    def on_end(self, closed=False):
        # logging.info("stop eeg stream ran")
        self.stim_timer.stop()
        # if self.data_type != "SIMULATE":
            # self.board.stop()

        if not closed:
            self.close()

    def display_instructions(self):
        # this will run at the beginning and needs a button press before anything else will happen

        self.label = QLabel()
        self.label.setFont(QtGui.QFont("Arial", 14))
        self.label.setText(
            "Look at the fixation cross.\nright moving either the left arm or the right arm\nPress enter to begin"
        )
        self.layout.addWidget(self.label)

    def start_trial(self):
        # starts trial - starts timers.
        logging.info("starting trial")
        self.running_trial = True
        # setting current color and stim code based on value for current trial
        logging.info(self.curr_trial)
        self.stim_code = self.trials[self.curr_trial]
        time.sleep(0.5)

        if self.curr_trial < self.total_trials - 1:
            self.curr_trial += 1
            self.start_stim()
        else:
            logging.info("all trials done")
            self.finished = True
            # self.board.insert_marker(self.end_trig)
            self.on_end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Qt.Key_Space:
            if self.responding_time == True:
                logging.info("received user input during correct time")
                # self.board.insert_marker(3)
            else:
                logging.info("received user input during incorrect time")

        elif event.key() == Qt.Qt.Key_Return or event.key == Qt.Qt.Key_Enter:
            # logging.info(
            #     "hardware {} running trial {}".format(
            #         self.hardware_connected, self.running_trial
            #     )
            # )
            if self.is_receiving and not self.running_trial:
                self.label.setVisible(False)
                self.start_trial()

    def paintEvent(self, event):
        # here is where we draw stuff on the screen
        # you give drawing instructions in pixels - here I'm getting pixel values based on window size
        logging.info("paint event runs")
        if self.show_stim:
            pass
            # logging.info("painting stim")
            # center = self.geometry().width() // 2
            # textWidth = 200
            # textHeight = 100
            # font = QFont()
            # font.setFamily("Tahoma")
            # font.setPixelSize(32)
            # font.setBold(True)
            # painter.setFont(font)
            # painter.drawText(
            #     center - textWidth // 2,
            #     center - textHeight // 2,
            #     textWidth,
            #     textHeight,
            #     QtCore.Qt.AlignCenter,
            #     self.stim_str[self.stim_code - 1],
            # )

        elif self.running_trial and not self.finished:
            painter = QPainter(self)
            painter.setBrush(QBrush(QtCore.Qt.black, QtCore.Qt.SolidPattern))
            cross_width = 100
            line_width = 20
            center = self.geometry().width() // 2
            painter.drawRect(
                center - line_width // 2,
                center - cross_width // 2,
                line_width,
                cross_width,
            )
            painter.drawRect(
                center - cross_width // 2,
                center - line_width // 2,
                cross_width,
                line_width,
            )
        elif self.finished:
            # no need to paint anything specifically
            pass

    def closeEvent(self, ev):
        self.curr_trial = self.total_trials
        self.on_end(closed=True)
        return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = baseline_win()
    # win.show(csv_name="baseline.csv", board_id=1, serial_port="COM3")
    sys.exit(app.exec())
