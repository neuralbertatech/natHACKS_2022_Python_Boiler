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

log_file = "boiler.log"
logging.basicConfig(level=logging.INFO, filemode="a", filename = log_file, format = 'Logger: %(name)s: %(levelname)s at: %(asctime)s, line %(lineno)d: %(message)s')
logger = logging.getLogger("GraphWindow")
logger.addHandler(logging.FileHandler(log_file))
logger.info("Graph window imported at {}".format(time.time()))

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
        log_file = 'graph_win'+str(time.time())+'.log'
    ):
        super().__init__()
        logger.info('Initializing graph_win (Graph window)')
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
            logger.warning('Board id was not proved to graph window. Attempting to set based on hardware, model, and data type.')
            if self.data_type == "Task live":
                if self.hardware == "openBCI":
                    if self.model == "Ganglion":
                        self.board_id = 1
                    elif self.model == "Cyton":
                        self.board_id = 0
                    elif self.model == "Cyton-Daisy":
                        self.board_id = 2
                elif self.hardware == "Muse":
                    if self.model == "Muse 2":
                        self.board_id = 22
                    elif self.model == "Muse S":
                        self.board_id = 21
            elif self.data_type == "Task simulate":
                self.board_id = -1
        else:
            self.board_id = board_id

        logger.info('Graph window is starting to connect to hardware with board id {}. \n \
        Board ID key: https://brainflow.readthedocs.io/en/stable/SupportedBoards.html'.format(self.board_id))

        if self.params.serial_port == None:

            logger.warning('COM port was not provided. Graph window is trying COM ports for board connection')
            connected_yet = False
            i = 0
            search_num = 25
            while i <= search_num and connected_yet == False:
                self.params.serial_port = 'COM'+str(i)
                self.board = BoardShim(self.board_id, self.params)
                try:
                    self.board.prepare_session()
                except brainflow.board_shim.BrainFlowError as e:
                    pass
                else:
                    logger.info('Graph window connected using com port COM{}'.format(i))
                    # didn't have the bad com port exeption
                    connected_yet = True
                    break
                i+=1
            if connected_yet == False:
                # if we're here, it didn't connect and we're out of COM ports
                logger.error('Graph window failed to find a COM port for given hardware (board id: {}). \
                    Please specify COM port manually or increase the number of COM ports searched (Currently {}).'.format(self.board_id,search_num))
                raise Exception('Unable to find COM port to connect to hardware.')
        else:
            logger.info('Graph window is using {} port for board connection'.format(self.params.serial_port))
            self.board = BoardShim(self.board_id, self.params)
            self.board.prepare_session()

        self.board.start_stream()
        self.hardware_connected = True
        logger.info('Hardware connected; stream started.')

        self.exg_channels = BoardShim.get_exg_channels(self.board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 50
        self.window_size = 4
        self.num_points = self.window_size * self.sampling_rate

        self.chan_num = len(self.exg_channels)
        self.exg_channels = np.array(self.exg_channels)
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

        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def _init_timeseries(self):
        self.plots = list()
        self.curves = list()
        for i in range(self.chan_num):
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
        logger.debug('Graph window is updating')
        data = self.board.get_current_board_data(self.num_points)
        # save data to our csv super quick
        with open(self.save_file,'a') as csvfile:
            data_to_save = data[BoardShim.get_exg_channels(self.board_id),:].T
            logger.debug('data size {}'.format(data_to_save.shape))
            logger.debug(data_to_save)
            np.savetxt(csvfile,data_to_save,delimiter = ',')
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
        logger.debug('Graph window finished updating (successfully got data from board and applied it to graphs)')

    def closeEvent(self, event):
        self.timer.stop()
        print("close event runs")
        self.board.stop_stream()
        self.board.release_session()
        print(self.data.shape)
        print(self.data)
        logger.info('Now closing graph window')
        self.close()


if __name__ == "__main__":
    app = pg.mkQApp("MultiPlot Widget Example")
    win = graph_win()
    win.show()
    # sys.exit(app.exec())
    pg.exec()
