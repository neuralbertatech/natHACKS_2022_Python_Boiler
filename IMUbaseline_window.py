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
import pandas as pd

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

# log_file = "boiler.log"
# logging.basicConfig(level=logging.INFO, filemode="a")

# f = logging.Formatter(
#     "Logger: %(name)s: %(levelname)s at: %(asctime)s, line %(lineno)d: %(message)s"
# )
# stdout = logging.StreamHandler(sys.stdout)
# boiler_log = logging.FileHandler(log_file)
# stdout.setFormatter(f)
# boiler_log.setFormatter(f)

# logger = logging.getLogger("BaselineWindow")
# logger.addHandler(boiler_log)
# logger.addHandler(stdout)
# logger.info("Program started at {}".format(time.time()))


class IMUbaseline_win(QWidget):
    def __init__(
        self,
        parent=None,
        csv_name=None,
        arduino_serial_port=None
    ):
        super().__init__()
        # self.csv_name = csv_name[:-4] + "_" + str(int(time.time())) + ".csv"
        self.csv_name = csv_name
        self.parent = parent
        self.arduino_serial_port=arduino_serial_port

        self.imu_count = 1

        self.data = [[] for x in range(self.imu_count)]
        # self.data = []

        '''
        
        with the move to async - the programmatic event marker will need to be based on an IMU specific sample count. 
        marker can be appended to a a given incoming data packet - will then want to add each packet to not just be appended, but appended as a list 

        '''

        self.imu_dict = {
            0: {
                'address' : '0A:54:F1:E2:B3:C1',
                'is_connected' : False,
                'is_full_subscribed' : False,

                'orient_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D68',
                'is_subscribed_orient' : False,
                'orient_count' : 0,
                'orient_data' : [],

                'accel_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D24',
                'is_subscribed_accel' : False,
                'accel_count' : 0,
                'accel_data' : [],

                'gyro_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D32',
                'is_subscribed_gyro' : False,
                'gyro_count' : 0,
                'gyro_data' : [],

            },   
            1: {
                'address' : 'C8:87:39:14:AC:BF',
                'read_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D69',
                'is_connected' : False,
                'is_subscribed' : False,
                'data' : [],
                'count' : 0
            },
            2: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : '917649A1-D98E-11E5-9EEC-0002A5D5C51B',
                'is_connected' : False,
                'is_subscribed' : False,
                'data' : [],
                'count' : 0
            },   
            3: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : 'C8F88594-2217-0CA6-8F06-A4270B675D69',
                'is_connected' : False,
                'is_subscribed' : False,
                'data' : [],
                'count' : 0
            },
            4: {
                'address' : '0A:54:F1:E2:B3:C1',
                'read_UUID' : '917649A1-D98E-11E5-9EEC-0002A5D5C51B',
                'is_connected' : False,
                'is_subscribed' : False,
                'data' : [],
                'count' : 0
            },   
        }

        self.is_receiving = False

        self.count = 0

        if self.parent.debug == True:
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
                'trigger' : 1000,
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
            # 5 : {
            #     'movie_file' : 'touch_nose.gif',
            #     'stim_str' : 'Touch Nose',
            #     'trigger' : 1005
            # },
        }

        # now we can init stuff for our trials
        self.trials_per_move = 2
        self.moves = self.parent.action_num
        self.total_trials = self.moves * self.trials_per_move

        self.trials = []
        for move in range(self.moves):
            self.trials = self.trials + [move] * self.trials_per_move

        random.shuffle(self.trials)
        logging.info("trials {}".format(self.trials))

        self.curr_trial = 0
        
        self.finished = False # this is whether or not we've gone through all our trials yet
        self.stim_code = self.trials[0] # need to prime the first without moving index up incase the paint event is too quick

        print("self.curr_trial: " + str(self.curr_trial))

        # now we display the instructions
        self.running_trial = False
        self.display_instructions()

        # state for if the user is current in a responding period
        self.responding_time = False

        # the timer is an object that creates timeout events at regular intervals after it's started with timer.start(# ms to run for)
        self.stim_timer = QTimer() # in this case, it's a single shot timer and we start it manually

        # making it a precision timer
        self.stim_timer.setTimerType(0)
        self.stim_timer.setSingleShot(True)

        # setting the function to call when it times out
        # IMPORTANT: to change the function it calls, must first use timer.disconnect() to remove the previous one
        # otherwise will call both new and old fucntions
        self.stim_timer.timeout.connect(self.start_trial)

        # To ensure we dont try to close the object a second time
        self.is_end = False

        self.com_list = ['COM5','COM6']

        for x in range(self.imu_count):
            print("init loop on cycle: " + str(x))

            self.adapter = pygatt.BGAPIBackend(serial_port=self.com_list[x]) #virtual COM port for the BlueGiga dongle
            print('Trying to connect to: ' + str(self.arduino_serial_port) + ' at ' + str(self.imu_dict[x]['address']))
            # Attempt to connect to the device
            try:
                self.adapter.start()
                self.device = self.adapter.connect(self.imu_dict[x]['address']) 
                print(self.device)
                print('Connected!')
                self.imu_dict[x]['is_connected'] = True
            except(pygatt.exceptions.NotConnectedError):
                print('Failed to connect to: ' + str(self.arduino_serial_port) + ' at ' + str(self.imu_dict[x]['address']))

            #### subscribe to orient
            try:
                self.device.subscribe(self.imu_dict[x]['orient_UUID'], callback=self.subscribeCallback_orient, indication=False, wait_for_response=True)
                print("successfully to subscribe to orient_UUID")
            except:
                print("failed to subscribe to orient_UUID")

            #### subscribe to accel
            try:
                self.device.subscribe(self.imu_dict[x]['accel_UUID'], callback=self.subscribeCallback_accel, indication=False, wait_for_response=True)
                print("successfully to subscribe to accel_UUID")
            except:
                print("failed to subscribe to accel_UUID")

            #### subscribe to gyro
            try:
                self.device.subscribe(self.imu_dict[x]['gyro_UUID'], callback=self.subscribeCallback_gyro, indication=False, wait_for_response=True)
                print("successfully to subscribe to gyro_UUID")
            except:
                print("failed to subscribe to gyro_UUID")

        while self.is_receiving == False:
            print("waiting for subscribtions to finish")
            if self.imu_dict[0]['is_subscribed_orient'] == True and self.imu_dict[0]['is_subscribed_accel'] == True and self.imu_dict[0]['is_subscribed_gyro'] == True:
                self.is_receiving = True
            time.sleep(0.5)

    def subscribeCallback_orient(self, handle, value):
        if self.imu_dict[0]['is_subscribed_orient'] == False:
            self.imu_dict[0]['is_subscribed_orient'] = True
        elif self.is_receiving == True:
            self.value = struct.unpack('3f', value)    
            fdata = [0] + [self.imu_dict[0]['orient_count']] + list(self.value) # concat a blank trigger list to the incoming list (changed from tuple form)
            self.imu_dict[0]['orient_data'].append(fdata)    # we get the latest data point and append it to our array
        self.imu_dict[0]['orient_count'] += 1 # shift the count pointer to the new entry

    def subscribeCallback_accel(self, handle, value):
        if self.imu_dict[0]['is_subscribed_accel'] == False:
            self.imu_dict[0]['is_subscribed_accel'] = True
        elif self.is_receiving == True:
            self.value = struct.unpack('3f', value)    
            # fdata = [0] + [self.imu_dict[0]['accel_count']] + list(self.value) # concat a blank trigger list to the incoming list (changed from tuple form)
            fdata = list(self.value) # concat a blank trigger list to the incoming list (changed from tuple form)
            self.imu_dict[0]['accel_data'].append(fdata)    # we get the latest data point and append it to our array
        self.imu_dict[0]['accel_count'] += 1 # shift the count pointer to the new entry

    def subscribeCallback_gyro(self, handle, value):
        if self.imu_dict[0]['is_subscribed_gyro'] == False:
            self.imu_dict[0]['is_subscribed_gyro'] = True
        elif self.is_receiving == True:
            self.value = struct.unpack('3f', value)    
            # fdata = [0] + [self.imu_dict[0]['gyro_count']] + list(self.value) # concat a blank trigger list to the incoming list (changed from tuple form)
            fdata = list(self.value) # concat a blank trigger list to the incoming list (changed from tuple form)
            self.imu_dict[0]['gyro_data'].append(fdata)    # we get the latest data point and append it to our array
        self.imu_dict[0]['gyro_count'] += 1 # shift the count pointer to the new entry

    def set_movie(self):
        print(self.stim_dict[self.stim_code]['movie_file'])
        self.movie = QMovie(self.stim_dict[self.stim_code]['movie_file'])
        self.movieLabel.setMovie(self.movie)
        self.movieLabel.show()
        self.movie.start()

    def start_trial(self):
        print("start trial")
        print("self.curr_trial: " + str(self.curr_trial))

        # starts trial - starts timers.
        logging.info("starting trial")
        self.running_trial = True
        # setting current color and stim code based on value for current trial
        logging.info(self.curr_trial)
        time.sleep(1)

        if self.curr_trial < self.total_trials:
            print(self.curr_trial)
            print("self.curr_trial")
            print(self.total_trials)
            print("self.total_trials")
            self.start_stim()
        else:
            logging.info("all trials done")
            self.finished = True
            # self.board.insert_marker(self.end_trig)
            self.on_end()

    def start_stim(self):
        print("start stim")
        print("self.curr_trial: " + str(self.curr_trial))

        self.stim_code = self.trials[self.curr_trial]\

        logging.info("starting stim")
        self.show_stim = True
        # stim_wait = time.time()
        self.responding_time = True
        self.set_movie()

        self.imu_dict[0]['orient_data'][-1][0] = self.stim_dict[self.stim_code]['trigger'] # replace the blank trigger

        self.stim_timer.timeout.disconnect()
        self.stim_timer.timeout.connect(self.end_stim)
        self.stim_timer.start(3000)
        self.update()

    def end_stim(self):
        print("end stim")
        print("self.curr_trial: " + str(self.curr_trial))
        logging.info("ending stim")
        self.responding_time = False
        self.show_stim = False
        self.curr_trial += 1
        self.update()

        self.movie.stop()
        self.movieLabel.hide()

        self.stim_timer.timeout.disconnect()
        self.stim_timer.timeout.connect(self.start_trial)
        self.stim_timer.start(3000)

    def on_end(self, closed=False):
        self.stim_timer.stop()

        orient_data = np.array(self.imu_dict[0]['orient_data'])
        accel_data = np.array(self.imu_dict[0]['accel_data'])
        gyro_data = np.array(self.imu_dict[0]['gyro_data'])

        print("orient data:")
        print(orient_data[0:10])
        print("accel data:")
        print(accel_data[0:10])
        print("gyro data:")
        print(gyro_data[0:10])

        min_size = min(np.shape(orient_data)[0],np.shape(accel_data)[0],np.shape(gyro_data)[0])

        print("orient len:" + str(np.shape(orient_data)[0]))
        print("accel len:" + str(np.shape(accel_data)[0]))
        print("gyro len:" + str(np.shape(gyro_data)[0]))

        print(min_size)

        data = np.concatenate((orient_data[0:min_size],accel_data[0:min_size],gyro_data[0:min_size]),axis=1)

        df = pd.DataFrame(data)
        df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az'] 
        # df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az'] 

        df.to_csv(self.csv_name,index=False)
        
        print("trying to enable model window")
        self.parent.model_window_button.setEnabled(True)
        time.sleep(1)
        
        if not closed:
            self.close()

    def display_instructions(self):
        # this will run at the beginning and needs a button press before anything else will happen

        self.label = QLabel()
        self.label.setFont(QtGui.QFont("Arial", 14))
        self.label.setText(
            # "Look at the fixation cross.\n right moving either the left arm or the right arm\nPress enter to begin"
            "Mirror the movements on the screen"
        )
        self.layout.addWidget(self.label)

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
        # logging.info("paint event runs")
        painter = QPainter(self)

        if self.show_stim:
            # pass
            # logging.info("painting stim")
            # center = self.geometry().width() // 2
            textWidth = 200
            textHeight = 100
            font = QFont()
            font.setFamily("Tahoma")
            font.setPixelSize(32)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                25,
                25, 
                # QtCore.Qt.AlignTop,
                'Please:' + self.stim_dict[self.stim_code]['stim_str'],
            )

        elif self.running_trial and not self.finished:
            # painter = QPainter(self)
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

        try:
            self.device.unsubscribe(self.imu_dict[0]['orient_UUID'], wait_for_response=False)
        except:
            print("threw error on orient unsub")

        time.sleep(0.5)

        try:
            self.device.unsubscribe(self.imu_dict[0]['accel_UUID'], wait_for_response=False)
        except:
            print("threw error on accel unsub")

        time.sleep(0.5)

        try:
            self.device.unsubscribe(self.imu_dict[0]['gyro_UUID'], wait_for_response=False)
        except:
            print("threw error on gyro unsub")

        print("past unsub")
        # self.on_end(closed=True)
        return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = baseline_win()
    # win.show(csv_name="baseline.csv", board_id=1, serial_port="COM3")
    sys.exit(app.exec())
