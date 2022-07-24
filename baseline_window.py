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

import numpy as np
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
from brainflow.data_filter import DataFilter, FilterTypes
from PyQt5 import Qt, QtCore, QtGui
from PyQt5.QtCore import QTimer  # Qt,
from PyQt5.QtGui import QBrush, QFont, QPainter, QPen, QPolygon
from PyQt5.QtOpenGL import *
from PyQt5.QtWidgets import *

from Board import CONNECT, Board, get_board_id

# from PyQt5 import QWidget


# from multiprocessing import Process, Queue
# from utils.pyqt5_widgets import MplCanvas


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


class baseline_win(QWidget):
    def __init__(
        self,
        hardware=None,
        model=None,
        sim_type=None,
        data_type=None,
        csv_name=None,
        parent=None,
        serial_port=None,
        board_id=None,
    ):
        super().__init__()

        self.parent = parent
        self.sim_type = sim_type
        self.hardware = hardware
        self.model = model
        self.data_type = data_type

        self.csv_name = csv_name[:-4] + "_" + str(int(time.time())) + ".csv"

        parent.csv_name_final = self.csv_name

        # Brainflow Init
        self.params = BrainFlowInputParams()
        self.params.serial_port = serial_port

        self.data = []

        if self.parent.debug == True:
            BoardShim.enable_dev_board_logger()

        self.com_port = None

        if board_id == None:
            self.board_id = get_board_id(self.data_type, self.hardware, self.model)
        else:
            self.board_id = board_id

        self.setMinimumSize(600, 600)
        self.setWindowIcon(QtGui.QIcon("utils/logo_icon.jpg"))

        # setting window title
        self.setWindowTitle("Baseline Window")

        # init layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.stim_type = {"left": 1, "right": 2}

        # whether to actually display a stimulus of specified color
        self.show_stim = False

        # by default we are going to have the classifier predict Right Arm as the correct
        # give a graded - provide stimulation when the probability is above a set threshold of 90%
        # need to save model and then reload when starting session

        self.stim_str = ["Left Arm", "Right Arm"]

        # let's start eeg receiving!
        self.board = Board(board_id=self.board_id)
        self.hardware_connected = True

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
        self.end_trig = 11

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

    def start_stim(self):
        logging.info("starting stim")
        self.show_stim = True
        stim_wait = time.time()
        self.responding_time = True
        self.board.insert_marker(self.stim_code)
        logging.info("debug")
        self.stim_timer.timeout.disconnect()
        self.stim_timer.timeout.connect(self.end_stim)
        self.stim_timer.start(1000)
        self.update()

    def end_stim(self):
        logging.info("ending stim")
        self.responding_time = False
        self.show_stim = False
        self.board.insert_marker(self.end_trig)
        self.update()

        self.stim_timer.timeout.disconnect()
        self.stim_timer.timeout.connect(self.start_trial)
        self.stim_timer.start(1000)

    def on_end(self, closed=False):
        logging.info("stop eeg stream ran")
        self.stim_timer.stop()
        if self.data_type != "SIMULATE":
            self.board.stop()

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
            self.board.insert_marker(self.end_trig)
            self.on_end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Qt.Key_Space:
            if self.responding_time == True:
                logging.info("received user input during correct time")
                self.board.insert_marker(3)
            else:
                logging.info("received user input during incorrect time")

        elif event.key() == Qt.Qt.Key_Return or event.key == Qt.Qt.Key_Enter:
            logging.info(
                "hardware {} running trial {}".format(
                    self.hardware_connected, self.running_trial
                )
            )
            if self.hardware_connected and not self.running_trial:
                self.label.setVisible(False)
                self.start_trial()

    def paintEvent(self, event):
        # here is where we draw stuff on the screen
        # you give drawing instructions in pixels - here I'm getting pixel values based on window size
        logging.info("paint event runs")
        painter = QPainter(self)
        if self.show_stim:
            logging.info("painting stim")
            center = self.geometry().width() // 2
            textWidth = 200
            textHeight = 100
            font = QFont()
            font.setFamily("Tahoma")
            font.setPixelSize(32)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                center - textWidth // 2,
                center - textHeight // 2,
                textWidth,
                textHeight,
                QtCore.Qt.AlignCenter,
                self.stim_str[self.stim_code - 1],
            )

        elif self.running_trial and not self.finished:
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
    win.show(csv_name="baseline.csv", board_id=1, serial_port="COM3")
    sys.exit(app.exec())
