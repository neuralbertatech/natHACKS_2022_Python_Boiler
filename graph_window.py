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
from Board import Board, get_board_id
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

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations
import brainflow

SIMULATE = 0
FILE = 1
LIVESTREAM = 2

###########################################################


class graph_win(QWidget):
    def __init__(
        self,
        hardware=None,
        model=None,
        sim_type=None,
        data_type=None,
        serial_port=None,
        save_file=None,
        parent=None,
        board_id=None,
    ):
        super().__init__()
        logger.info("Initializing graph_win (Graph window)")
        self.parent = parent
        self.sim_type = sim_type
        self.hardware = hardware
        self.model = model
        self.data_type = data_type
        # save file should be an ok file name to save to with approriate ending ('.csv')
        self.save_file = save_file
        self.board_id = get_board_id(data_type, hardware, model)
        self.exg_channels = BoardShim.get_exg_channels(self.board_id)

        # by default, not using this (turn back on if you have most recent brainflow)
        # in the most recent version of brainflow, you can access an additional muse channel,
        # correponding to the aux port. However, this update breaks that bandstop filter, 
        # so make sure to turn that off (in self.update)
        if self.board_id in (21,22,42) and True:
            # muse devices have an extra eeg channel. We need to configure th board
            # to include it before we strat the stream, so we'll make our Board in
            # manual mode so we can start the stream ourselves.
            # if we are using muse hardware get a channel for the device's aux port
            self.aux_channels = BoardShim.get_other_channels(self.board_id)
            self.using_aux_channels = True
        else:
            self.using_aux_channels = False

        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 50
        self.window_size = 5
        self.num_points = self.window_size * self.sampling_rate

        if self.board_id in (21,22,42) and True:
            # muse devices have an extra eeg channel. We need to configure th board
            # to include it before we strat the stream, so we'll make our Board in
            # manual mode so we can start the stream ourselves.
            manual_mode = True
            # if we are using muse hardware get a channel for the device's aux port
            self.aux_channels = BoardShim.get_other_channels(self.board_id)
            self.using_aux_channels = False
        else:
            manual_mode = False
            self.using_aux_channels = False
        self.board = Board(data_type, hardware, model, board_id, serial_port=serial_port, num_points = self.num_points,manual_mode = manual_mode)

        if manual_mode:
            logger.info('manual mode section ran')
            # using muse. configure so we get 5h eeg channel, and start stream
            self.board.board.config_board("p50")
            self.board.board.start_stream()

        self.hardware_connected = True
        logger.info("Hardware connected; stream started.")

        self.chan_num = len(self.exg_channels)
        self.exg_channels = np.array(self.exg_channels)
        if self.using_aux_channels:
            self.aux_channels = np.array(self.aux_channels)
        print('board decription {}'.format(BoardShim.get_board_descr(board_id)))

        logger.debug('EXG channels is {}'.format(self.exg_channels))

        # set up stuff to save our data
        # just a numpy array for now
        # 10 minutes of data
        # init a cursor to keep track of where we are in the data
        self.data_max_len = self.sampling_rate * 600
        self.data = np.zeros((self.data_max_len, self.chan_num))
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
        if self.using_aux_channels:
            num_curves = self.chan_num + len(self.aux_channels)
        else:
            num_curves = self.chan_num
        for i in range(num_curves):
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
        data = self.board.get_new_data()
        # save data to our csv super quick
        save_to_csv(data,self.save_file,BoardShim.get_exg_channels(self.board_id),logger)
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
        data = self.board.get_data_quantity(self.num_points)
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
            logging.info(' channel, data[channel] before bandstop {}\n {}'.format(channel,data[channel]))
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
        if self.using_aux_channels:
            for count, channel in enumerate(self.aux_channels):
                self.curves[len(self.exg_channels)+count].setData(data[channel].tolist())
            logger.debug('AUX channel data was {}'.format(data[self.aux_channels].tolist()))
        logger.debug('Graph window finished updating (successfully got data from board and applied it to graphs)')

    def closeEvent(self, event):
        self.timer.stop()
        self.board.stop()
        logger.info(self.data.shape)
        logger.info(self.data)
        logger.info("Now closing graph window")
        self.close()


if __name__ == "__main__":
    app = pg.mkQApp("MultiPlot Widget Example")
    win = graph_win()
    win.show()
    # sys.exit(app.exec())
    pg.exec()
