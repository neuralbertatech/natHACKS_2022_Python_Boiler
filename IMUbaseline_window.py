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

from threading import Thread
import serial

# from functools import partial
# import pygatt
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
        imu_serial_port=None
    ):
        super().__init__()
        self.csv_name = csv_name[:-4] + "_" + str(int(time.time())) + ".csv"
        # self.csv_name = csv_name
        self.parent = parent
        self.par = self.parent.par
        self.imu = self.parent.imu

        self.imu_serial_port=imu_serial_port

        self.imu_csv_order = self.parent.imu_csv_order

        self.imu_count = 0

        self.thread = None

        self.data_types = ['orient_data','accel_data','gyro_data']
        self.count_types = ['orient_count','accel_count','gyro_count']

        self.imu_dict = {
            0: {
                'is_connected' : False,
                'is_read' : False,
                'local_start_time' : None,
                'local_end_time' : None,

                'orient_count' : 0,
                'orient_data' : [],

                'accel_count' : 0,
                'accel_data' : [],

                'gyro_count' : 0,
                'gyro_data' : [],

                'count' : 0,
                'data': []
            },   
            1: {
                'is_connected' : False,
                'is_read' : False,
                'local_start_time' : None,
                'local_end_time' : None,

                'orient_count' : 0,
                'orient_data' : [],

                'accel_count' : 0,
                'accel_data' : [],

                'gyro_count' : 0,
                'gyro_data' : [],

                'count' : 0,
                'data': []
            },
        }

        self.is_receiving = False

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
            5 : {
                'movie_file' : 'touch_nose.gif',
                'stim_str' : 'Touch Nose',
                'trigger' : 1005
            },
        }

        # now we can init stuff for our trials
        self.trials_per_move = 1
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

        ################ Connecting to serial port ##########################

        self.port = 'COM27'
        self.baud = 9600

        self.recieve_address = False
        self.address_wait_time = 10

        # self.dataNumBytes = 16
        self.dataAddressNumBytes = 17
        # self.addressData = bytearray(self.dataAddressNumBytes)

        self.dataNumBytes = 49
        self.rawData = bytearray(self.dataNumBytes)

        self.imu_address_order = [] # the order that the peripherial IMUs are indexed as on the Central

        print('Trying to connect to: ' + str(self.port) + ' at ' + str(self.baud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(self.port, self.baud, timeout=4)
            print('Connected to ' + str(self.port) + ' at ' + str(self.baud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(self.port) + ' at ' + str(self.baud) + ' BAUD.')

        self.readSerialStart()

    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.is_receiving != True:
                time.sleep(0.1)

    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        recieve_address_time_start = time.time()
        while (self.is_end == False):
            #######################
            ### add a self.imu_init == False: then wait for some bytes to be send to 
            ### arrive expect a short (0,1)
            ### then set a self.imu_ready = True
            ### then send a 1

            ### should eventually throw an error if the incorrect number of IMUs addresses are sent back

            cur_bytes = self.serialConnection.inWaiting()
            # print("Number of bytes in the queue: " + str(cur_bytes))
            if not self.recieve_address:
                print("Number of bytes in the queue: " + str(cur_bytes))
                if cur_bytes >= self.dataAddressNumBytes:
                    line = self.serialConnection.readline().decode('utf-8').rstrip()
                    # print(line)
                    self.imu_address_order.append(line)
                    time.sleep(0.5)
                time_now = time.time()
                time_waited = time_now - recieve_address_time_start
                remaining_wait_time = self.address_wait_time - (time_waited)
                print("the time spent waiting for ble addresses to be passed: {} \n time remaining: {}".format(str(time_waited),str(remaining_wait_time)))
                if time_now - recieve_address_time_start > self.address_wait_time:
                    self.recieve_address = True
                    self.serialConnection.reset_input_buffer()
                    print("final index list of IMUs found and subscribed to:")
                    print(self.imu_address_order)
                time.sleep(0.2)
                ### Need to move the IMU count to here
            else:
                if cur_bytes >= self.dataNumBytes:
                    bytes_read = self.serialConnection.readinto(self.rawData)
                    # print("bytes read:" + str(bytes_read)) # a boolean of how many recieved form the last line
                    
                    # Stop the block in the readSerialStart
                    if self.is_receiving == False:
                        self.is_receiving = True 

                    # val = struct.unpack('hfffffffffhbbbbbf', self.rawData)
                    val = struct.unpack('=h9fh5bf', self.rawData)
                    imu = val[0]

                    # The first time we get data from a new board - we flip boolean for that board's subdict in 
                    # imu_dict, save the time of the first read i.e. start time, and increment the imu_count so
                    if self.imu_dict[imu]['is_read'] == False:
                        self.imu_dict[imu]['local_start_time'] = time.time()
                        self.imu_dict[imu]['is_read'] = True
                        self.imu_count += 1

                    # print("-------------------------")
                    # print(val)
                    # print(len(val))

                    # print("imu index:" + str(imu))
                    # print("characteristic index:" + str(char))
                    # print(self.data_types[char])

                    val = list(val)
                    val = [0] + [self.imu_dict[imu]['count']] + val[1:]
                    self.imu_dict[imu]['data'].append(val)

                    # if char == 0: # if the first characteristic of the first device - add a empty trigger AND a count to the list
                    #     val = [0] + [self.imu_dict[imu][self.count_types[char]]] + val[2:]
                    #     self.imu_dict[imu][self.data_types[char]].append(val)
                    # else:
                    #     self.imu_dict[imu][self.data_types[char]].append(val[2:]) # for all other imu/char combo - only save the float values

                    # print(val)
                    # print(len(val))
                    # print("-------------------------")

                    # self.imu_dict[imu][self.count_types[char]] += 1 # shift the count pointer to the new entry
                    self.imu_dict[imu]['count'] += 1 # shift the count pointer to the new entry

    def set_movie(self):
        print(self.stim_dict[self.stim_code]['movie_file'])
        self.movie = QMovie(self.stim_dict[self.stim_code]['movie_file'])
        self.movieLabel.setMovie(self.movie)
        self.movieLabel.show()
        self.movie.start()

    def start_trial(self):
        print("start trial")
        print("self.curr_trial: " + str(self.curr_trial))

        logging.info("starting trial")
        self.running_trial = True
        # setting current color and stim code based on value for current trial
        logging.info(self.curr_trial)
        time.sleep(1)

        if self.curr_trial < self.total_trials:
            self.start_stim()
        else:
            logging.info("all trials done")
            self.finished = True
            self.on_end()

    def start_stim(self):
        print("start stim")
        print("self.curr_trial: " + str(self.curr_trial))

        self.stim_code = self.trials[self.curr_trial]\

        self.show_stim = True
        self.responding_time = True
        self.set_movie()

        for imu in range(self.imu_count):
            self.imu_dict[imu]['data'][-1][0] = self.stim_dict[self.stim_code]['trigger'] # replace the blank trigger

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
        
        self.is_end == True

        # serial_open = self.serialConnection.is_open
        # print("serial open: ")
        # print(serial_open)
        for imu in range(self.imu_count):
            self.imu_dict[imu]['local_end_time'] = time.time()

        try:
            print("closing serial connection in on_end")
            serial_open = self.serialConnection.is_open
            print("serial open: ")
            print(serial_open)
            if serial_open == True:
                self.serialConnection.close()
            serial_open = self.serialConnection.is_open
            print("serial open: ")
            print(serial_open)
        except:
            print("closing serialConnection threw an error")

        self.stim_timer.stop()

        imu_data_size = []

        for i in range(self.imu_count):
            ### from here forth cna assume that the data sent is consistent across each type
            # orient_data = np.array(self.imu_dict[i]['orient_data'])
            # accel_data = np.array(self.imu_dict[i]['accel_data'])
            # gyro_data = np.array(self.imu_dict[i]['gyro_data'])

            # print("orient data from board {}:".format(str(i)))
            # print(orient_data[0:10])
            # print("accel data from board {}:".format(str(i)))
            # print(accel_data[0:10])
            # print("gyro data from board {}:".format(str(i)))
            # print(gyro_data[0:10])

            # min_size = min(np.shape(orient_data)[0],np.shape(accel_data)[0],np.shape(gyro_data)[0])

            # print("orient len from board " + str(i) + ":" + str(np.shape(orient_data)[0]))
            # print("accel len from board " + str(i) + ":" +  str(np.shape(accel_data)[0]))
            # print("gyro len from board " + str(i) + ":" +  str(np.shape(gyro_data)[0]))


            data = np.array(self.imu_dict[i]['data'])

            print("data from board {}:".format(str(i)))
            print(data[0:10])
            min_size = np.shape(data)[0]

            print(min_size)
            imu_data_size.append(min_size)

            start_time = self.imu_dict[imu]['local_start_time']
            print(start_time)
            end_time = self.imu_dict[imu]['local_end_time']
            print(end_time)
            time_delta = end_time - start_time
            print(time_delta)
            sampling_rate = min_size/time_delta
            print("For board #" + str(i) + "the sampling rate was " + str(sampling_rate))

        print("The imu data size for each board is:")
        print(imu_data_size)
        min_size_boards = min(imu_data_size)
        print("The imu data size for the smallest board is:")
        print(min_size_boards)

        if self.imu_count == 1:
            # data = np.concatenate((orient_data[0:min_size],accel_data[0:min_size],gyro_data[0:min_size]),axis=1)

            df = pd.DataFrame(data)
            df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond'] 
            # df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az'] 
            # df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az'] 
        elif self.imu_count == 2:
            ### can find the MAX value (instead of min) and zero pad - 
            ### then iteratively add together sensor (all 3 char vals concated) 
            data = np.concatenate(
                (
                    # self.imu_dict[0]['orient_data'][0:min_size_boards],
                    # self.imu_dict[0]['accel_data'][0:min_size_boards],
                    # self.imu_dict[0]['gyro_data'][0:min_size_boards],  
                    # self.imu_dict[1]['orient_data'][0:min_size_boards],
                    # self.imu_dict[1]['accel_data'][0:min_size_boards],
                    # self.imu_dict[1]['gyro_data'][0:min_size_boards],  
                    self.imu_dict[0]['data'][0:min_size_boards],  
                    self.imu_dict[1]['data'][0:min_size_boards],
                ),
                axis=1)
            df = pd.DataFrame(data)
            df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond','trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond'] 

        elif self.imu_count == 2:
            ### can find the MAX value (instead of min) and zero pad - 
            ### then iteratively add together sensor (all 3 char vals concated) 
            data = np.concatenate(
                (
                    # self.imu_dict[0]['orient_data'][0:min_size_boards],
                    # self.imu_dict[0]['accel_data'][0:min_size_boards],
                    # self.imu_dict[0]['gyro_data'][0:min_size_boards],  
                    # self.imu_dict[1]['orient_data'][0:min_size_boards],
                    # self.imu_dict[1]['accel_data'][0:min_size_boards],
                    # self.imu_dict[1]['gyro_data'][0:min_size_boards],  
                    self.imu_dict[0]['data'][0:min_size_boards],  
                    self.imu_dict[1]['data'][0:min_size_boards],
                    self.imu_dict[2]['data'][0:min_size_boards],

                ),
                axis=1)
            df = pd.DataFrame(data)
            df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond','trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond','trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond'] 


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
            "Mirror the movements on the screen \n Press enter to begin"
        )
        self.layout.addWidget(self.label)

    def keyPressEvent(self, event):
        if event.key() == Qt.Qt.Key_Space:
            if self.responding_time == True:
                logging.info("received user input during correct time")
            else:
                logging.info("received user input during incorrect time")

        elif event.key() == Qt.Qt.Key_Return or event.key == Qt.Qt.Key_Enter:
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
            print("closing serial connection in closeEvent")
            serial_open = self.serialConnection.is_open
            print("serial open: ")
            print(serial_open)
            if serial_open == True:
                self.serialConnection.close()
            serial_open = self.serialConnection.is_open
            print("serial open: ")
            print(serial_open)
        except:
            print("closing serialConnection threw an error")

        # try:
        #     print("closing serial connection in closeEvent")
        #     serial_open = self.serialConnection.is_open
        #     if serial_open == True:
        #         self.serialConnection.close()
        # except:
        #     pass
        # return

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = baseline_win()
    # win.show(csv_name="baseline.csv", board_id=1, serial_port="COM3")
    sys.exit(app.exec())
