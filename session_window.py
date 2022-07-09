"""
This is the imagine task
- it displays either a blue or green circle and records when user hits space
it pumps data about what happens when to an lsl stream
it also receive eeg data from a muse, or simulates it
This data is recorder along with events
EVENT KEY:
0 - Begin trial
1 - normal color displayed (blue)
2 - imagine color displayed (green)
3 - user pressed space
11 - end trial
It contains partially complete code to graph ERP afterwards.
The data is stored with tines normalized (timestamp 0 when stim first displayed, for each trial)
so setting up an ERP graph should be reasonably simple
Project ideas: any project where the user sees something displayed and interacts with it, while eeg is recorded
"""

import sys
import time
import csv
import random

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPainter, QBrush, QPen, QPolygon

# from PyQt5 import QWidget

import numpy as np

# from multiprocessing import Process, Queue
# from utils.pyqt5_widgets import MplCanvas

from brainflow.data_filter import (
    DataFilter,
    FilterTypes,
    AggOperations,
    WindowFunctions,
    DetrendOperations,
)
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

import sys
from io import StringIO
from scipy import signal, interpolate
import numpy as np

# from tensorflow.keras.models import Sequential
# from tensorflow.keras.layers import Dense, Flatten, Dropout, Activation
# import tensorflow as tf
import pandas as pd
from sklearn.model_selection import train_test_split
from statsmodels.tsa.ar_model import AutoReg

import serial
import pygatt
from binascii import hexlify
import asyncio

from scipy.signal import butter, lfilter, freqz, hilbert, chirp

from Board import get_board_id

SIMULATE = 0
FILE = 1
LIVESTREAM = 2


class session_win(QWidget):
    def __init__(
        self,
        hardware=None,
        model=None,
        sim_type=None,
        data_type=None,
        csv_name=None,
        parent=None,
        serial_port=None,
        arduino_port=None,
        arduino_con=None,
        targ_limb=None,
        board_id=None,
    ):
        super().__init__()

        self.parent = parent
        self.sim_type = sim_type
        self.hardware = hardware
        self.model = model
        self.data_type = data_type
        self.targ_limb = targ_limb
        timestamp = str(int(time.time()))
        self.csv_name = csv_name[:-4] + "_" + timestamp + ".csv"
        self.running_checks = False

        ### Arduino parameters
        self.arduino_port = arduino_port
        self.arduino_con = arduino_con

        if self.parent.debug == True:
            BoardShim.enable_dev_board_logger()
            serial_port = "COM1"

        # Brainflow Initialization
        self.params = BrainFlowInputParams()
        self.params.serial_port = serial_port
        # self.params.serial_port = 'COM15'

        self.data = []

        self.board_id = board_id
        if self.board_id is None:
            self.board_id = get_board_id(self.data_type, self.hardware, self.model)

        self.setMinimumSize(600, 600)
        self.setWindowIcon(QtGui.QIcon("utils/logo_icon.jpg"))

        # setting window title
        self.setWindowTitle("imagine Window")

        # init layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        # self.layout.setContentsMargins(100,100,100,100)

        self.stim_type = {"left": 1, "right": 2}

        # whether to actually display a stimulus of specified color
        self.show_stim = False

        # by default we are going to have the classifier predict Right Arm as the correct
        # give a graded - provide stimulation when the probability is above a set threshold of 90%
        # need to save model and then reload when starting session

        self.stim_str = ["Left Arm", "Right Arm"]

        # let's start eeg receiving!
        # self.start_data_stream()
        self.board = BoardShim(self.board_id, self.params)
        self.board.prepare_session()
        print(
            "init hardware is running with hardware", self.hardware, "model", self.model
        )
        self.board.start_stream()
        time.sleep(1)
        self.board.insert_marker(1)
        self.hardware_connected = True

        time.sleep(2)

        # the timer is an object that creates timeout events at regular intervals after it's started with timer.start(# ms to run for)
        # in this case, it's a single shot timer and we start it manually
        self.check_timer = QTimer()
        # making it a precision timer
        self.check_timer.setTimerType(0)
        self.check_timer.setSingleShot(True)
        # setting the function to call when it times out
        # IMPORTANT: to change the function it calls, must first use timer.disconnect() to remove the previous one
        # otherwise will call both new and old fucntions
        self.check_timer.timeout.connect(self.classify)

        # To ensure we dont try to close the object a second time
        self.is_end = False

        self.total_trials = 10
        self.curr_trial = 0

        self.display_instructions()
        self.finished = False

        ####################
        # Init signal processing

        self.intra_epoch_num = 5

        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        print("sampling rate: {}".format(self.sampling_rate))

        self.intra_epoch_ind = np.zeros((self.intra_epoch_num, 2), dtype=int)

        for cur_intra in range(self.intra_epoch_num):
            low_bound = (
                int(self.sampling_rate / self.intra_epoch_num) * cur_intra
            ) - self.sampling_rate / self.intra_epoch_num
            high_bound = int(self.sampling_rate / self.intra_epoch_num) * cur_intra
            self.intra_epoch_ind[cur_intra][0] = low_bound
            self.intra_epoch_ind[cur_intra][1] = high_bound

        # print(self.intra_epoch_ind)

        self.bands = {
            # 'theta' : (4.0, 7.0),
            # 'low_alpha' : (8.0, 10.0),
            # 'high_alpha' : (10.0, 13.0),
            "alpha": (7.0, 13.0),
            "low_beta": (13.0, 20.0),
            "high_beta": (20.0, 30.0),
        }

        #############################
        # Init advanced signal processing

        # BoardShim.log_message(LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')
        # time.sleep(2)
        self.nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
        # print(nfft)
        self.nfft = 32

        self.chan_num = 16
        self.drop_col = [0, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
        self.col_names = [
            "chan_1",
            "chan_2",
            "chan_3",
            "chan_4",
            "chan_5",
            "chan_6",
            "chan_7",
            "chan_8",
            "chan_9",
            "chan_10",
            "chan_11",
            "chan_12",
            "chan_13",
            "chan_14",
            "chan_15",
            "chan_16",
            "trig",
        ]

        self.model = self.parent.ml_model

        #######################
        # Preprocessing params
        self.butter_cutoff = 50
        self.butter_order = 6
        self.bandpass_center = 10
        self.bandpass_width = 4

        ####################
        # Phase estimation
        self.targ_elec = 5
        self.ref_elec = [6, 7, 8, 9]
        self.desired_phase = 0
        self.technical_delay = 8
        self.delay_tolerance = 5

        ################
        # Stimulation init
        self.ard_wait = 0.5
        self.channel = 1
        self.stim_ampl = 5
        self.stim_freq = 10
        self.stim_dur = 1

        ### Conditional Connection Initialization

        def read(arduino):
            try:
                msg = arduino.read(
                    arduino.inWaiting()
                ).decode()  # read everything in the input buffer
                print(msg)
                return msg
            except:
                pass

        print("setting up arduino")
        if self.arduino_con == "Wireless":
            self.TDCS_UUID = "00001101-0000-1000-8000-00805f9b34fb"
            self.on_value = bytearray([0x01])
            self.off_value = bytearray([0x00])
            print("Arduino Nano BLE LED Peripheral Central Service")
            print("Looking for Arduino Nano 33 BLE Sense Peripheral Device...")
            self.arduino = pygatt.BGAPIBackend(
                serial_port=self.arduino_port
            )  # virtual COM port for the BlueGiga dongle
            try:
                self.arduino.start()
                device = self.arduino.connect(
                    "C8:87:39:14:AC:BF"
                )  # MAC address of the Arduino
                print(device)
            except (pygatt.exceptions.NotConnectedError):
                print("Could not find Arduino Nano 33 BLE Sense Peripheral")
        elif self.arduino_con == "Wired":
            self.arduino = serial.Serial(
                port=self.arduino_port, baudrate=9600, timeout=0.1
            )
        elif self.arduino_con == "NeuroStimDuino":
            self.arduino = serial.Serial(
                port=self.arduino_port, baudrate=115200, timeout=0.1
            )

            time.sleep(self.ard_wait)  # wait for arduino init on serial connection
            read(self.arduino)  # get initial starting message

            cmd_string = ("RSET 1" + "\r\n").encode(
                "ascii"
            )  # create encoded string to set amplitude of channel 1
            self.arduino.write(cmd_string)  # write

            time.sleep(self.ard_wait)  # wait for arduino init on serial connection
            read(self.arduino)  # get initial starting message

            cmd_string = ("AMPL 1 {}".format(self.stim_ampl) + "\r\n").encode(
                "ascii"
            )  # create encoded string to set amplitude of channel 1
            self.arduino.write(cmd_string)  # write
            time.sleep(self.ard_wait)
            read(self.arduino)  # confirm amp set correctly

            cmd_string = ("FREQ 1 {}".format(self.stim_freq) + "\r\n").encode(
                "ascii"
            )  # create encoded string to set amplitude of channel 1
            self.arduino.write(cmd_string)  # write
            time.sleep(self.ard_wait)
            read(self.arduino)  # confirm amp set correctly
        elif self.arduino_con == "Debug":
            pass

    def read(self, arduino):
        try:
            msg = arduino.read(
                arduino.inWaiting()
            ).decode()  # read everything in the input buffer
            print(msg)
            return msg
        except:
            pass

    def activate_arduino(self):
        print("activating arduino")
        if self.arduino_con == "Wireless":
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(self.run())
            except KeyboardInterrupt:
                print("\nReceived Keyboard Interrupt")
            finally:
                print("Program finished")
        elif self.arduino_con == "Wired":
            if self.arduino_button.text() == "Activate Arduino":
                self.arduino.write(b"0")
                self.arduino_button.setText("Deactivate Arduino")
            else:
                self.arduino.write(b"1")
                self.arduino_button.setText("Activate Arduino")
        elif self.arduino_con == "NeuroStimDuino":
            cmd_string = (
                "STIM {} {} 0".format(self.channel, self.stim_dur) + "\r\n"
            ).encode("ascii")
            self.arduino.write(cmd_string)  # write
            time.sleep(self.ard_wait)
            self.read(self.arduino)  # confirm amp set correctly

        elif self.arduino_con == "Debug":
            pass

    def start_stim(self):
        print("starting pulse train")

    def start_check_timer(self):
        print("starting check")
        self.check_timer.timeout.disconnect()
        self.check_timer.timeout.connect(self.classify)
        self.check_timer.start(5000)
        self.update()

    def grab_board_data(self):
        self.data = self.board.get_board_data()
        print(self.data.shape)
        for chan in range(self.chan_num):
            DataFilter.perform_lowpass(
                self.data[chan],
                self.sampling_rate,
                self.butter_cutoff,
                self.butter_order,
                FilterTypes.BUTTERWORTH.value,
                0,
            )

        df = pd.DataFrame(np.transpose(self.data))

        df.drop(df.columns[self.drop_col], axis=1, inplace=True)
        df.columns = self.col_names

        return df

    def get_model_input(self, df):
        targ_trigs = df[(df["trig"] == 1) | (df["trig"] == 2)].index

        temp_targ = []
        temp_chan = []
        temp_intra_epoch = []
        temp_bands = []
        targ = 0

        for chan in range(self.chan_num):
            """
            still need to add in within epoch baseline subtraction
            """
            for intra_epoch in range(
                self.intra_epoch_num
            ):  # range(len(intra_epoch_ind)
                targ_win_low = targ_trigs[targ] + self.intra_epoch_ind[intra_epoch][0]
                targ_win_high = targ_trigs[targ] + self.intra_epoch_ind[intra_epoch][1]
                psd = DataFilter.get_psd_welch(
                    df.iloc[targ_win_low:targ_win_high, chan].to_numpy(),
                    self.nfft,
                    self.nfft // 2,
                    self.sampling_rate,
                    WindowFunctions.BLACKMAN_HARRIS.value,
                )
                for (
                    band
                ) in (
                    self.bands
                ):  # iteration through the target bands and grab the average over the time bucket
                    temp_chan_spec_buc = DataFilter.get_band_power(
                        psd, self.bands[band][0], self.bands[band][1]
                    )  # temporary channel spectral bucket
                    temp_bands.append(temp_chan_spec_buc)
                temp_intra_epoch.append(temp_bands)
                temp_bands = []
            temp_chan.append(temp_intra_epoch)
            temp_intra_epoch = []
        temp_targ.append(temp_chan)
        temp_targ = np.array(temp_targ)
        # print(temp_targ.shape)

        return temp_targ

    def find_phase(self, df):
        start_comp = time.now()
        df = self.grab_board_data()

        df["Hjorth"] = df.iloc[:, self.targ_elec] - df.iloc[:, self.ref_elec].mean(
            axis=1
        )
        Hjorth = df["Hjorth"].to_numpy()

        DataFilter.perform_bandpass(
            Hjorth,
            self.sampling_rate,
            self.bandpass_center,
            self.bandpass_width,
            self.butter_order,
            FilterTypes.BUTTERWORTH.value,
            1,
        )

        phase_target = df["Hjorth"][-101:-1].to_numpy()

        #### Hilbert and get amplitude envelope, instantaneous phase/frequency, and average frequency
        analytic_signal = hilbert(phase_target)
        # inst_phase = np.unwrap(np.angle(analytic_signal))#inst phase
        amplitude_envelope = np.abs(analytic_signal)
        inst_phase_series = np.angle(analytic_signal, deg=False)

        inst_freq_series = (
            np.diff(np.unwrap(inst_phase_series)) / (2.0 * np.pi) * self.sampling_rate
        )

        # take the average frequency of the signal (exculding the very beginning and very end)
        avg_inst_freq = np.mean(
            inst_freq_series[
                int(len(inst_freq_series) * 0.2) : -np.int(len(inst_freq_series) * 0.2)
            ]
        )
        print(avg_inst_freq)

        x = np.arange(0, len(phase_target)) * (1 / self.sampling_rate)

        ### Putting it all together

        ### Ground truth autoregression prediction and comparison
        phase_len = len(phase_target)
        predict_len = int(phase_len / 2)
        predict_x = np.linspace(phase_len, phase_len + predict_len, predict_len)

        # Create training and test data
        train_data = phase_target[: len(phase_target) - predict_len]
        test_data = phase_target[len(phase_target) - predict_len :]

        # Instantiate and fit the AR model with training data
        ar_model = AutoReg(train_data, lags=5).fit()

        # Print Summary
        # print(ar_model.summary())

        # Make the predictions
        pred_groud_truth_y = ar_model.predict(
            start=len(train_data), end=phase_len, dynamic=False
        )
        pred_ground_truth_x = (
            np.arange(0, np.ceil(predict_len) + 1) * (1 / self.sampling_rate) + x[50]
        )

        ### Novel autoregression prediction
        train_data = phase_target

        # predict_len = np.ceil(samples_required) * 2
        predict_len = int(phase_len / 2)

        # Instantiate and fit the AR model with training data
        ar_model = AutoReg(train_data, lags=5).fit()

        # Print Summary
        # print(ar_model.summary())

        # Make the predictions
        pred_new_y = ar_model.predict(
            start=len(train_data),
            end=int(len(train_data) - 1 + predict_len),
            dynamic=False,
        )
        pred_new_x = (
            np.arange(0, np.ceil(predict_len)) * (1 / self.sampling_rate)
            + pred_ground_truth_x[-1]
        )

        # ### Combining the original signal and the prediction into a single time series
        # hybrid_signal_x = np.append(x[int(len(phase_target)/2):],pred_new_x)
        # hybrid_signal_y = np.append(phase_target[int(len(phase_target)/2):],pred_new_y)

        ### Move over prediction to match the autoregression intersect of phase 0
        ### Start from just the autoregression

        last_ascent = False
        false_peak = False
        is_upward = True
        ascent_narrow = 0
        # error_narrow = 4

        ascent_begin, ascent_end = None, None
        # error_margin_begin, error_margin_end = None, None

        for i in range(len(pred_new_y) - 1):
            print(i)
            if pred_new_y[i] - pred_new_y[i + 1] < 0:
                is_upward = True
                print("is_upward")
            else:
                is_upward = False
            if is_upward:
                if last_ascent == False and pred_new_y[i] > 0:
                    false_peak = True
                    print("false_peak")
                elif not last_ascent:
                    last_ascent = True
                    print("last_ascent " + str(last_ascent))
                    ascent_begin = i + ascent_narrow
                    # error_margin_begin = i + error_narrow
            if not is_upward and last_ascent and ascent_end == None:
                ascent_end = i - ascent_narrow
                # error_margin_end = i - error_narrow

        final_ascent_x = pred_new_x[ascent_begin:ascent_end]
        final_ascent_y = pred_new_y[ascent_begin:ascent_end]

        f = interpolate.interp1d(final_ascent_y, final_ascent_x)
        stim_time = f(0)
        stim_time = float(stim_time)
        # error_margin_begin = stim_time - self.delay_tolerance/2/1000
        # error_margin_end = stim_time + self.delay_tolerance/2/1000

        # def find_nearest(array, value):
        #     array = np.asarray(array)
        #     idx = (np.abs(array - value)).argmin()
        #     return idx #array[idx]

        # nearest_point_idx = find_nearest(final_ascent_x, stim_time)+ascent_begin

        return start_comp, stim_time

    def classify(self):
        print("ending stim")
        self.responding_time = False
        self.show_stim = False
        # self.data = self.board.get_board_data()
        print(self.curr_trial)

        df = self.grab_board_data()

        temp_targ = self.get_model_input(df)

        predict = self.model.predict(temp_targ)
        print(predict)

        if predict == self.targ_limb:
            start_comp, stim_time = self.find_phase()

            # # https://www.gaussianwaves.com/2017/04/extract-envelope-instantaneous-phase-frequency-hilbert-transform/

            """
            skip making noise floor consistent for now
                can implement later
                https://github.com/Existentialist-Robot/py_eegepe/blob/master/py_eegepe/data_loader.py

            Get good with FOOOF to be able to paramaterize and pick the alpha peak, i.e. the IAF ( individual alpha frequency )
            Grabs peaks and then we can grab biggest peak between 8 and 13, then do a 3Hz bandpass filter around the IAF
            """

        self.activate_arduino()

        self.update()

        """
        Need to get the ping of the arduino (for technical delay)
            - perhaps writing in a response in the .ino file

        BASIC non-ML MATLAB implementation for phase estimation
            https://github.com/OpitzLab/CL-phase

            re-reference to surrounding electrodes (Hjorth)

            https://www.daanmichiels.com/blog/2017/10/filtering-eeg-signals-using-scipy/

        hilbert transform

            http://www.rdgao.com/roemerhasit_Hilbert_Transform/

            https://www.youtube.com/watch?v=VyLU8hlhI-I&list=PLn0OLiymPak3jjr0hHI9OFXuQyPBQlFdk&ab_channel=MikeXCohen

        simple using scipy

            https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.hilbert.html
        
        """

        self.check_timer.timeout.disconnect()
        self.check_timer.timeout.connect(self.iteration_start)
        self.check_timer.start(2000)

    def on_end(self):

        print("stop eeg stream ran")

        if self.data_type != "SIMULATE":
            self.board.stop_stream()
            self.board.release_session()

        self.parent.results_window_button.setEnabled(True)
        self.parent.title.setText("Check out your Stats through the Results Window")

        self.close()

    def display_instructions(self):
        # this will run at the beginning and needs a button press before anything else will happen

        self.label = QLabel()
        self.label.setFont(QtGui.QFont("Arial", 14))
        self.label.setText(
            "Look at the fixation cross. \nWhenever you feel like it, imagine moving your stroke affected limb. \nPress the Enter button to start."
        )
        self.layout.addWidget(self.label)

    def iteration_start(self):
        time.sleep(0.5)
        if self.curr_trial < self.total_trials - 1:
            self.curr_trial += 1
            self.start_check_timer()
            self.board.insert_marker(1)
        else:
            print("Finished Session")
            self.finished = True
            self.on_end()

    def closeEvent(self, event):
        # this code will autorun just before the window closes
        # we will check whether streams are running, if they are we will close them
        print("close event works")
        # self.on_end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Qt.Key_Space:
            print("received user input during incorrect time")

        elif event.key() == Qt.Qt.Key_Return or event.key == Qt.Qt.Key_Enter:
            print(
                "hardware {} running trial {}".format(
                    self.hardware_connected, self.running_checks
                )
            )
            if self.hardware_connected and not self.running_checks:
                self.running_checks = True
                self.label.setVisible(False)
                self.iteration_start()

    def paintEvent(self, event):
        # here is where we draw stuff on the screen
        # you give drawing instructions in pixels - here I'm getting pixel values based on window size
        print("paint event runs")
        painter = QPainter(self)
        if self.running_checks and not self.finished:
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = session_win()
    win.show()
    sys.exit(app.exec())
