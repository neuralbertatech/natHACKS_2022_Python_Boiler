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
from __future__ import print_function

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

### mbientlabs packages - also requires time and threading (previously imported here - refer to )
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *

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
        # self.imu = self.parent.imu

        self.imu_hardware = self.parent.imu_hardware
        self.imu_model = self.parent.imu_model

        self.imu_serial_port = imu_serial_port

        self.imu_order = self.parent.imu_order

        self.imu_count = 0

        self.thread = None

        self.data_types = ['orient_data','accel_data','gyro_data']
        self.count_types = ['orient_count','accel_count','gyro_count']

        # shift to iteratively creating imu_dict based on number of IMUs expected
        self.imu_dict = {
            0: {
                'is_connected' : False,
                'is_read' : False,
                'local_start_time' : None,
                'local_end_time' : None,
                'count' : 0,
                'data': []
            },   
            1: {
                'is_connected' : False,
                'is_read' : False,
                'local_start_time' : None,
                'local_end_time' : None,
                'count' : 0,
                'data': []
            },
            2: {
                'is_connected' : False,
                'is_read' : False,
                'local_start_time' : None,
                'local_end_time' : None,
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
        self.trials_per_move = self.parent.trials_per_move
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

        # self.com_list = ['COM5','COM6']

        ################ Connecting to serial port ##########################

        if self.imu_hardware == "arduino":
            if self.imu_model == "BLE33":

                self.port = 'COM27'
                self.baud = 9600

                self.recieve_address = False
                self.address_wait_time = 5

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
        elif self.imu_hardware == "mbientlabs":
            if self.imu_model == "MMS":
                sibling = self
                class State:
                        # init
                    def __init__(self, device):
                        self.device = device
                        self.samples = 0
                        self.callback = FnVoid_VoidP_DataP(self.data_handler)
                    # callback
                    def data_handler(self, ctx, data):
                        print("%s -> %s" % (self.device.address, parse_value(data)))
                        self.samples+= 1 
                        ### Need to add saving to imu_dict
                        print(self.device.address)
                        print(type(self.device.address))
                        
                        print("-------")

                        for x in range(len(sibling.imu_order)):
                            print(sibling.imu_order[x])

                        # print(sibling.imu_order[0])

                        imu = sibling.imu_order.index(self.device.address)

                        if sibling.imu_dict[imu]['is_read'] == False:
                            sibling.imu_dict[imu]['local_start_time'] = time.time() # save the time of the first read i.e. start time
                            sibling.imu_dict[imu]['is_read'] = True # tie off this init flow
                            sibling.imu_count += 1 # increment the imu_count so
                            print("IMU count has been increased to: {}".format(str(self.imu_count)))

                        # print("imu index:" + str(imu))
                        # print("-------------------------")
                        # print(val)
                        # print(len(val))

                        val = parse_value(data)
                        print(type(val))
                        val = [0] + [self.imu_dict[imu]['count']] + val[1:] # concat a blank trig, count, and full data sample from imu (minus the IMU serial identifier)
                        self.imu_dict[imu]['data'].append(val)

                        # print(val)
                        # print(len(val))
                        # print("-------------------------")

                        self.imu_dict[imu]['count'] += 1 # shift the count pointer to the new entry
 
                self.states = []

                # connect
                for i in range(len(self.imu_order)):
                    d = MetaWear(self.imu_order[i])
                    d.connect()
                    print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
                    self.states.append(State(d))

                # configure
                for s in self.states:
                    print("Configuring device")
                    # setup ble
                    libmetawear.mbl_mw_settings_set_connection_parameters(s.device.board, 7.5, 7.5, 0, 10000)
                    time.sleep(1.5)
                    # setup acc
                    libmetawear.mbl_mw_acc_set_odr(s.device.board, 100.0)
                    libmetawear.mbl_mw_acc_set_range(s.device.board, 16.0)
                    libmetawear.mbl_mw_acc_write_acceleration_config(s.device.board)
                    # get acc and subscribe
                    signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(s.device.board)
                    libmetawear.mbl_mw_datasignal_subscribe(signal, None, s.callback)
                    # start acc
                    libmetawear.mbl_mw_acc_enable_acceleration_sampling(s.device.board)
                    libmetawear.mbl_mw_acc_start(s.device.board)

    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            while self.is_receiving != True: # Block baseline running until we start actually receiving values from Arduino
                time.sleep(0.1)

    def backgroundThread(self): 
        if self.imu_hardware == "arduino":
            if self.imu_model == "BLE33":
                self.serialConnection.reset_input_buffer()
                time.sleep(1.0)  # give some buffer time for retrieving data
                recieve_address_time_start = time.time() # start timer for waiting to recieve Peripheral BLE Addresses from Central
                while (self.is_end == False):
                    cur_bytes = self.serialConnection.inWaiting()
                    # print("Number of bytes in the queue: " + str(cur_bytes))

                    '''
                    The following is for the inital connection to each Arduino BLE 33 - grabbing the addresses in the order they were discovered
                    '''
                    if not self.recieve_address:
                        print("Number of bytes in the queue: " + str(cur_bytes))
                        if cur_bytes >= self.dataAddressNumBytes:
                            line = self.serialConnection.readline().decode('utf-8').rstrip()
                            self.imu_address_order.append(line)
                            time.sleep(0.2)
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
                        ### Throw error here if mismatch to -- self.imu_order = ['2e:2e:b1:17:3e:25','0a:54:f1:e2:b3:c1']
                        ### Should have a second clause here to send current date/time info to central to distribute to 
                    
                        '''
                        The following is for the main loop after connection has been established and the readSerialStart block has been lifted + PyQt5 has been allowed to continue
                        '''
                    else:
                        if cur_bytes >= self.dataNumBytes:
                            self.serialConnection.readinto(self.rawData)
                            # bytes_read = self.serialConnection.readinto(self.rawData)
                            # print("bytes read:" + str(bytes_read)) # a boolean of how many recieved form the last line
                            
                            if self.is_receiving == False: # Stop the block in the readSerialStart
                                self.is_receiving = True 

                            val = struct.unpack('=h9fh5bf', self.rawData)
                            imu = val[0]

                            # The first time we get data from a new board - we flip boolean for that board's subdict in 
                            if self.imu_dict[imu]['is_read'] == False:
                                self.imu_dict[imu]['local_start_time'] = time.time() # save the time of the first read i.e. start time
                                self.imu_dict[imu]['is_read'] = True # tie off this init flow
                                self.imu_count += 1 # increment the imu_count so
                                print("IMU count has been increased to: {}".format(str(self.imu_count)))

                            # print("imu index:" + str(imu))

                            # print("-------------------------")
                            # print(val)
                            # print(len(val))

                            val = list(val)
                            val = [0] + [self.imu_dict[imu]['count']] + val[1:] # concat a blank trig, count, and full data sample from imu (minus the IMU serial identifier)
                            self.imu_dict[imu]['data'].append(val)

                            # print(val)
                            # print(len(val))
                            # print("-------------------------")

                            self.imu_dict[imu]['count'] += 1 # shift the count pointer to the new entry
 
        # elif self.imu_hardware == "mbientlabs":
        #     if self.imu_model == "MMS":

                    # else:
                    #     pass

    def set_movie(self):
        print(self.stim_dict[self.stim_code]['movie_file'])
        self.movie = QMovie("animations/" + self.stim_dict[self.stim_code]['movie_file'])
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

        ### the next line is injecting trigger - currently not for mbientlabs
        if self.imu_model == "BLE33":
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

        for imu in range(self.imu_count):
            self.imu_dict[imu]['local_end_time'] = time.time()

        if self.imu_hardware == "arduino":
            if self.imu_model == "BLE33":
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
        elif self.imu_hardware == "mbientlabs":
            if self.imu_model == "MMS":
                for s in self.states:
                        # stop acc
                    libmetawear.mbl_mw_acc_stop(s.device.board)
                    libmetawear.mbl_mw_acc_disable_acceleration_sampling(s.device.board)
                    # unsubscribe
                    signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(s.device.board)
                    libmetawear.mbl_mw_datasignal_unsubscribe(signal)
                    # disconnect
                    libmetawear.mbl_mw_debug_disconnect(s.device.board)

        self.stim_timer.stop()

        imu_data_size = []

        for i in range(self.imu_count):
            data = np.array(self.imu_dict[i]['data'])

            print("data from board {}:".format(str(i)))
            print(data[0:3])
            min_size = np.shape(data)[0]

            imu_data_size.append(min_size)

            start_time = self.imu_dict[imu]['local_start_time']
            print(start_time)
            end_time = self.imu_dict[imu]['local_end_time']
            print(end_time)
            time_delta = end_time - start_time
            print(time_delta)
            sampling_rate = min_size/time_delta
            print("For board #" + str(i) + " the sampling rate was " + str(sampling_rate))

        print("The imu data size for each board is:")
        print(imu_data_size)
        min_size_boards = min(imu_data_size)
        print("The smallest data size for any board is:")
        print(min_size_boards)

        if self.imu_count == 1:
            # data = np.concatenate((orient_data[0:min_size],accel_data[0:min_size],gyro_data[0:min_size]),axis=1)

            df = pd.DataFrame(data)
            df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond'] 
        elif self.imu_count == 2:
            ### can find the MAX value (instead of min) and zero pad - 
            ### then iteratively add together sensor (all 3 char vals concated) 
                # self.imu_order = ['2e:2e:b1:17:3e:25','0a:54:f1:e2:b3:c1'] ### from their defined order in parent 
                # self.imu_address_order                                         ### from their order being identified/indexed by Central
            if self.imu_order[0] == self.imu_address_order[0]:
                print("\n")
                print("imu_order and imu_address_order match! Keeping current order for saving to csv!")
                data = np.concatenate(
                    ( 
                        self.imu_dict[0]['data'][0:min_size_boards],  
                        self.imu_dict[1]['data'][0:min_size_boards],
                    ),axis=1)
            else:
                print("\n")
                print("imu_order and imu_address_order don't match! Changing order that they are saved to csv!")
                data = np.concatenate(
                    (
                        self.imu_dict[1]['data'][0:min_size_boards],  
                        self.imu_dict[0]['data'][0:min_size_boards],
                    ),axis=1)
            df = pd.DataFrame(data)
            df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond','trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond'] 

        # elif self.imu_count == 3:
        #     ### can find the MAX value (instead of min) and zero pad - 
        #     ### then iteratively add together sensor (all 3 char vals concated) 
        #     data = np.concatenate(
        #         (
        #             self.imu_dict[0]['data'][0:min_size_boards],  
        #             self.imu_dict[1]['data'][0:min_size_boards],
        #             self.imu_dict[2]['data'][0:min_size_boards],

        #         ),
        #         axis=1)
        #     df = pd.DataFrame(data)
        #     df.columns = ['trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond','trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond','trigger','count','euler_1','euler_2','euler_3','gx','gy','gz','ax','ay','az','year','month','day','hour','minute','second','millisecond'] 

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
