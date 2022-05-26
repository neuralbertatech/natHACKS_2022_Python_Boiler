'''
This is the oddball task
- it displays either a blue or green circle and records when user hits space
it pumps data about what happens when to an lsl stream
it also receive eeg data from a muse, or simulates it
This data is recorder along with events

EVENT KEY:
0 - Begin trial
1 - normal color displayed (blue)
2 - oddball color displayed (green)
3 - user pressed space
11 - end trial

It contains partially complete code to graph ERP afterwards.
The data is stored with tines normalized (timestamp 0 when stim first displayed, for each trial)
so setting up an ERP graph should be reasonably simple

Project ideas: any project where the user sees something displayed and interacts with it, while eeg is recorded

'''

import sys
import time
import csv
import random
import pdb

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPainter, QBrush, QPen, QPolygon

import pyqtgraph as pg
# from pyqtgraph import MultiPlotWidget
# from pyqtgraph.Qt import QtWidgets
from pyqtgraph.Qt import QtCore

# try:
#     from pyqtgraph.metaarray import *
# except:
#     print("MultiPlot is only used with MetaArray for now (and you do not have the metaarray package)")
#     exit()

# from pyqtgraph.Qt import QtGui, QtCore
from random import randint

import numpy as np
import statistics as stats
from multiprocessing import Process, Queue

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations
import brainflow

SIMULATE = 0
FILE = 1
LIVESTREAM = 2

###########################################################

class graph_win(QWidget):
    def __init__(self, hardware = None, model = None, sim_type = None, \
            data_type = None, serial_port = None, save_file = None, parent = None, board_id = None):
        super().__init__()
        self.parent = parent
        self.sim_type = sim_type
        self.hardware = hardware
        self.model = model
        self.data_type = data_type
        # save file should be an ok file name to save to with approriate ending ('.csv')
        self.save_file = save_file

        # Brainflow Init
        self.params = BrainFlowInputParams()
        self.params.serial_port = serial_port


        if self.parent.debug == True:
            BoardShim.enable_dev_board_logger()

        # set baord id based on parameters only if it wasn't given to us
        if board_id == None:
            if self.data_type == 'Task live':
                if self.hardware == 'openBCI':
                    if self.model == 'Ganglion':
                        self.board_id = 1
                    elif self.model == 'Cyton':
                        self.board_id = 0
                    elif self.model == 'Cyton-Daisy':
                        self.board_id = 2
                elif self.hardware == 'Muse':
                    if self.model == 'Muse 2':
                        self.board_id = 22
                    elif self.model == 'Muse S':
                        self.board_id = 21
            elif self.data_type == 'Task simulate':
                self.board_id = -1
        else:
            self.board_id = board_id


        for i in range(10):
            self.params.serial_port = 'COM'+str(i)
            self.board = BoardShim(self.board_id, self.params)
            try:
                self.board.prepare_session()
            except brainflow.board_shim.BrainFlowError as e:
                pass
            else:
                # didn't have the bad com port exeption
                break

        print('init hardware is running with hardware',self.hardware,'model',self.model)
        self.board.start_stream()
        self.hardware_connected = True

        self.exg_channels = BoardShim.get_exg_channels(self.board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 50
        self.window_size = 4
        self.num_points = self.window_size * self.sampling_rate

        self.chan_num = len(self.exg_channels)
        self.exg_channels = np.array(self.exg_channels)

        # set up stuff to save our data
        # just a numpy array for now
        # 10 minutes of data
        # init a cursor to keep track of where we are in the data
        self.data_max_len = self.sampling_rate*600
        self.data = np.zeros((self.data_max_len,self.chan_num))
        self.cur_line = 0
        


        self.graphWidget = pg.GraphicsLayoutWidget()

        layout = QVBoxLayout()
        self.label = QLabel("Real Time Plot")
        layout.addWidget(self.label)
        self.setLayout(layout)
        layout.addWidget(self.graphWidget)

        self._init_timeseries()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def _init_timeseries(self):
        self.plots = list()
        self.curves = list()
        for i in range(self.chan_num):
            p = self.graphWidget.addPlot(row=i,col=0)
            p.showAxis('left', False)
            p.setMenuEnabled('left', False)
            p.showAxis('bottom', False)
            p.setMenuEnabled('bottom', False)
            if i == 0:
                p.setTitle('TimeSeries Plot')
            self.plots.append(p)
            curve = p.plot()
            self.curves.append(curve)

    def update(self):
        data = self.board.get_current_board_data(self.num_points)
        # note that the data objectwill porbably contain lots of dattathat isn't eeg
        # how much and what it is depends on the board. exg_channels contains the key for
        # what is and isn't eeg. We will ignore non eeg and not save it
        data_len = data.shape[1]
        if data_len + self.cur_line >= self.data_max_len:
            # we need to roll over and start at the beginning of the file
            self.data[self.cur_line:self.data_max_len,:] = data[self.exg_channels,:self.data_max_len-self.cur_line].T
            self.data[0:data_len-(self.data_max_len-self.cur_line),:] = data[self.exg_channels,self.data_max_len-self.cur_line:].T
            self.cur_line = data_len-(self.data_max_len-self.cur_line)
        else:
            self.data[self.cur_line:self.cur_line+data.shape[1],:] = data[self.exg_channels,:].T
        self.cur_line = self.cur_line + data.shape[1]

        for count, channel in enumerate(self.exg_channels):
            # plot timeseries
            DataFilter.detrend(data[channel], DetrendOperations.CONSTANT.value)
            DataFilter.perform_bandpass(data[channel], self.sampling_rate, 51.0, 100.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandpass(data[channel], self.sampling_rate, 51.0, 100.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 50.0, 4.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 60.0, 4.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            self.curves[count].setData(data[channel].tolist())
        
    
    def closeEvent(self,event):
        self.timer.stop()
        print('close event runs')
        self.board.stop_stream()
        self.board.release_session()
        print(self.data.shape)
        print(self.data)
        self.close()

    

if __name__ == '__main__':    
    app = pg.mkQApp("MultiPlot Widget Example")
    win = graph_win() 
    win.show() 
    # sys.exit(app.exec())
    pg.exec()
