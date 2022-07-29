"""
This graphs EEG data, live. 
"""

from dataclasses import dataclass
import sys
import time
import csv
import random
import pdb
import logging
from utils.save_to_csv import save_to_csv

log_file = "boiler.log"
logging.basicConfig(level=logging.INFO, filemode="a")

f = logging.Formatter(
    "Logger: %(name)s: %(levelname)s at: %(asctime)s, line %(lineno)d: %(message)s"
)
stdout = logging.StreamHandler(sys.stdout)
boiler_log = logging.FileHandler(log_file)
stdout.setFormatter(f)
boiler_log.setFormatter(f)

logger = logging.getLogger("GraphWindow")
logger.addHandler(boiler_log)
logger.addHandler(stdout)
logger.info("Program started at {}".format(time.time()))

from PyQt5.QtOpenGL import *
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *

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

from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations
import brainflow

from Board import PILL

SIMULATE = 0
FILE = 1
LIVESTREAM = 2

###########################################################


class GraphExg(QWidget):
    def __init__(self, number_of_channels, update_callback, update_object):
        super().__init__()
        logger.info("Initializing graph_win (Graph window)")
        
        self.number_of_channels = number_of_channels
        self.update_callback = update_callback
        self.update_object = update_object
        self.exg_channels = [1, 2, 3, 4, 5]
        self.marker_channels = 6
        self.sampling_rate = 125
        self.update_speed_ms = 50
        self.window_size = 5
        self.num_points = self.window_size * self.sampling_rate

        self.hardware_connected = True
        logger.info("Hardware connected; stream started.")

        self.exg_channels = np.array(self.exg_channels)
        self.marker_channels = np.array(self.marker_channels)

        logger.debug('EXG channels is {}'.format(self.exg_channels))

        # set up stuff to save our data
        # just a numpy array for now
        # 10 minutes of data
        # init a cursor to keep track of where we are in the data
        self.data_max_len = self.sampling_rate * 600
        self.data = np.zeros((self.data_max_len, self.number_of_channels))
        self.cur_line = 0

        self.graphWidget = pg.GraphicsLayoutWidget()

        layout = QVBoxLayout()
        self.label = QLabel("Real Time Plot")
        layout.addWidget(self.label)
        self.setLayout(layout)
        layout.addWidget(self.graphWidget)

        self._init_timeseries()

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def _init_timeseries(self):
        self.plots = list()
        self.curves = list()
        for i in range(self.number_of_channels+1):
            p = self.graphWidget.addPlot(row=i, col=0)
            p.showAxis("left", False)
            p.setMenuEnabled("left", False)
            p.showAxis("bottom", False)
            p.setMenuEnabled("bottom", False)
            if i == 0:
                p.setTitle("TimeSeries Plot")
            self.plots.append(p)
            curve = p.plot()
            self.curves.append(curve)

    def update(self):
        logger.debug("Graph window is updating")

        # this is data to be saved. It is only new data since our last call
        data = self.update_callback(self.update_object);
        # note that the data objectwill porbably contain lots of dattathat isn't eeg
        # how much and what it is depends on the board. exg_channels contains the key for
        # what is and isn't eeg. We will ignore non eeg and not save it
        

        data_len = data.shape[1]
        if data_len + self.cur_line >= self.data_max_len:
            # we need to roll over and start at the beginning of the file
            self.data[self.cur_line : self.data_max_len, :] = data[
                self.exg_channels, : self.data_max_len - self.cur_line
            ].T
            self.data[0 : data_len - (self.data_max_len - self.cur_line), :] = data[
                self.exg_channels, self.data_max_len - self.cur_line :
            ].T
            self.cur_line = data_len - (self.data_max_len - self.cur_line)
        else:
            self.data[self.cur_line : self.cur_line + data.shape[1], :] = data[
                self.exg_channels, :
            ].T
            self.cur_line = self.cur_line + data.shape[1]

        # this is data to be graphed. It is the most recent data, of the length that we want to graph
        #data = self.board.get_data_quantity(self.num_points)
        for count, channel in enumerate(self.exg_channels):
            # plot timeseries
            DataFilter.detrend(data[channel], DetrendOperations.CONSTANT.value)
            DataFilter.perform_bandpass(
                data[channel],
                self.sampling_rate,
                51.0,
                100.0,
                2,
                FilterTypes.BUTTERWORTH.value,
                0,
            )
            DataFilter.perform_bandpass(
                data[channel],
                self.sampling_rate,
                51.0,
                100.0,
                2,
                FilterTypes.BUTTERWORTH.value,
                0,
            )
            DataFilter.perform_bandstop(
                data[channel],
                self.sampling_rate,
                50.0,
                4.0,
                2,
                FilterTypes.BUTTERWORTH.value,
                0,
            )
            DataFilter.perform_bandstop(
                data[channel],
                self.sampling_rate,
                60.0,
                4.0,
                2,
                FilterTypes.BUTTERWORTH.value,
                0,
            )
            self.curves[count].setData(data[channel].tolist())
        self.curves[len(self.exg_channels)].setData(data[self.marker_channels].tolist())
        logger.debug('Marker channel data was {}'.format(data[self.marker_channels].tolist()))
        logger.debug('Graph window finished updating (successfully got data from board and applied it to graphs)')

    def closeEvent(self, event):
        self.timer.stop()
        logger.info(self.data.shape)
        logger.info(self.data)
        logger.info("Now closing graph window")
        self.close()


