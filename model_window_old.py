import time
import csv
import random

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QMovie, QPainter, QBrush, QPen, QPolygon
import numpy as np
import statistics as stats

import sys
from io import StringIO
from scipy import signal
import numpy as np
from Board import BCI, CYTON, CYTON_DAISY, GANGLION
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Dropout, Activation
import tensorflow as tf
import pandas as pd
from sklearn.model_selection import train_test_split

import argparse
import time
import brainflow
import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels, BoardIds
from brainflow.data_filter import (
    DataFilter,
    FilterTypes,
    AggOperations,
    WindowFunctions,
    DetrendOperations,
)

###########################################################


class model_win(QWidget):
    def __init__(self, hardware=None, model=None, parent=None, targ_limb=None):
        super().__init__()

        self.setFixedSize(200, 200)
        # self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)

        self.label_animation = QLabel(self)

        self.movie = QMovie("utils/Loading_2.gif")
        self.label_animation.setMovie(self.movie)
        self.targ = targ_limb

        timer = QTimer(self)

        self.startAnimation()
        timer.singleShot(5000, self.stopAnimation)

        #### might not need
        self.show()

        self.parent = parent
        self.hardware = hardware
        self.model = model

        intra_epoch_num = 5

        # Init boardshim early on for sampling rate
        BoardShim.enable_dev_board_logger()
        # use synthetic board for demo
        # params = BrainFlowInputParams ()
        board_id = BoardIds.SYNTHETIC_BOARD.value
        sampling_rate = BoardShim.get_sampling_rate(board_id)
        print("sampling rate: {}".format(sampling_rate))

        intra_epoch_ind = np.zeros((intra_epoch_num, 2), dtype=int)

        for cur_intra in range(intra_epoch_num):
            low_bound = (
                int(sampling_rate / intra_epoch_num) * cur_intra
            ) - sampling_rate / intra_epoch_num
            high_bound = int(sampling_rate / intra_epoch_num) * cur_intra
            intra_epoch_ind[cur_intra][0] = low_bound
            intra_epoch_ind[cur_intra][1] = high_bound

        bands = {
            # 'theta' : (4.0, 7.0),
            # 'low_alpha' : (8.0, 10.0),
            # 'high_alpha' : (10.0, 13.0),
            "alpha": (7.0, 13.0),
            "low_beta": (13.0, 20.0),
            "high_beta": (20.0, 30.0),
        }

        self.file_name = parent.csv_name
        self.csv_name_final = self.file_name + ".csv"

        if self.hardware == BCI:
            if self.model == GANGLION:
                self.chan_num = 4
                self.drop_col = [0, *range(5, 31)]
                self.col_names = [*("chan_{}".format(i) for i in range(1, 5)), "trig"]
            elif self.model == CYTON:
                self.chan_num = 8
                self.drop_col = [0, *range(9, 31)]
                self.col_names = [*("chan_{}".format(i) for i in range(1, 9)), "trig"]
            elif self.model == CYTON_DAISY:
                self.chan_num = 16
                self.drop_col = [0, *range(17, 31)]
                self.col_names = [*("chan_{}".format(i) for i in range(1, 17)), "trig"]

        X = []
        y = []

        #############################################################

        # ### Combining brainflows examples - a) Python Read Write File + b) Band Power

        #         '''
        #         Python Read Write File
        #         '''
        #         BoardShim.enable_dev_board_logger ()
        #         # use synthetic board for demo
        #         params = BrainFlowInputParams ()
        #         board = BoardShim (BoardIds.SYNTHETIC_BOARD.value, params)
        #         board.prepare_session ()
        #         board.start_stream ()
        #         BoardShim.log_message (LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')
        #         time.sleep (10)
        #         data = board.get_current_board_data (20) # get 20 latest data points dont remove them from internal buffer
        #         board.stop_stream ()
        #         board.release_session ()
        #         # demo how to convert it to pandas DF and plot data
        #         eeg_channels = BoardShim.get_eeg_channels (BoardIds.SYNTHETIC_BOARD.value)
        #         df = pd.DataFrame (np.transpose (data))
        #         print ('Data From the Board')
        #         print (df.head (10))
        #         # demo for data serialization using brainflow API, we recommend to use it instead pandas.to_csv()
        #         DataFilter.write_file (data, 'test.csv', 'w') # use 'a' for append mode
        #         restored_data = DataFilter.read_file ('test.csv')
        #         restored_df = pd.DataFrame (np.transpose (restored_data))
        #         print ('Data From the File')
        #         print (restored_df.head (10))

        #         '''
        #         Band Power
        #         '''
        #         BoardShim.enable_dev_board_logger ()
        #         # use synthetic board for demo
        #         params = BrainFlowInputParams ()
        #         board_id = BoardIds.SYNTHETIC_BOARD.value
        #         sampling_rate = BoardShim.get_sampling_rate (board_id)
        #         board = BoardShim (board_id, params)
        #         board.prepare_session ()
        #         board.start_stream ()
        #         BoardShim.log_message (LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')
        #         time.sleep (10)
        #         nfft = DataFilter.get_nearest_power_of_two (sampling_rate)
        #         data = board.get_board_data ()
        #         board.stop_stream ()
        #         board.release_session ()
        #         eeg_channels = BoardShim.get_eeg_channels (board_id)
        #         # second eeg channel of synthetic board is a sine wave at 10Hz, should see huge alpha
        #         eeg_channel = eeg_channels[1]
        #         # optional detrend
        #         DataFilter.detrend (data[eeg_channel], DetrendOperations.LINEAR.value)
        #         psd = DataFilter.get_psd_welch (data[eeg_channel], nfft, nfft // 2, sampling_rate, WindowFunctions.BLACKMAN_HARRIS.value)
        #         band_power_alpha = DataFilter.get_band_power (psd, 7.0, 13.0)
        #         band_power_beta = DataFilter.get_band_power (psd, 14.0, 30.0)
        #         print ("alpha/beta:%f", band_power_alpha / band_power_beta)
        #         # fail test if ratio is not smth we expect
        #         if (band_power_alpha / band_power_beta < 100):
        #             raise ValueError ('Wrong Ratio')

        # ################################################################

        # demo how to convert it to pandas DF and plot data
        restored_data = DataFilter.read_file(self.csv_name_final)

        restored_df = pd.DataFrame(np.transpose(restored_data))

        # print("restored data head: \n {} \nrestored_data.shape{}".format(restored_data, restored_data.shape))

        BoardShim.log_message(
            LogLevels.LEVEL_INFO.value, "start sleeping in the main thread"
        )
        time.sleep(2)
        nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
        print(nfft)
        nfft = 32

        restored_df.drop(restored_df.columns[self.drop_col], axis=1, inplace=True)

        restored_df.columns = self.col_names

        targ_trigs = restored_df[
            (restored_df["trig"] == 1) | (restored_df["trig"] == 2)
        ].index

        """
        need some across session detrending
        """

        temp_targ = []
        temp_chan = []
        temp_intra_epoch = []
        temp_bands = []

        for targ in range(len(targ_trigs)):
            for chan in range(self.chan_num):
                """
                still need to add in within epoch baseline subtraction
                """
                for intra_epoch in range(intra_epoch_num):  # range(len(intra_epoch_ind)
                    psd = DataFilter.get_psd_welch(
                        restored_data[chan][
                            targ_trigs[targ]
                            + intra_epoch_ind[intra_epoch][0] : targ_trigs[targ]
                            + intra_epoch_ind[intra_epoch][1]
                        ],
                        nfft,
                        nfft // 2,
                        sampling_rate,
                        WindowFunctions.BLACKMAN_HARRIS.value,
                    )
                    for (
                        band
                    ) in (
                        bands
                    ):  # iteration through the target bands and grab the average over the time bucket
                        temp_chan_spec_buc = DataFilter.get_band_power(
                            psd, bands[band][0], bands[band][1]
                        )  # temporary channel spectral bucket
                        temp_bands.append(temp_chan_spec_buc)
                    temp_intra_epoch.append(temp_bands)
                    temp_bands = []
                    temp_chan.append(temp_intra_epoch)
                    temp_intra_epoch = []
                temp_targ.append(temp_chan)
                temp_chan = []
            temp_targ = np.array(temp_targ)
            temp_targ = np.squeeze(temp_targ, axis=2)

            """
            Outputs here as:

            16 channels
            5 intra epoch buckets
            3 bandwidths

            """
            X.append(temp_targ)
            y.append(restored_df.iloc[targ_trigs[targ]]["trig"])
            print(restored_df.iloc[targ_trigs[targ]]["trig"])
            temp_targ = []
        y = np.array(y)
        X = np.array(X)

        #################################
        # Define Model Architecture

        dropout = 0.2
        input_shape = (16, 5, 3)

        eeg_model = Sequential()
        eeg_model.add(
            Flatten(input_shape=input_shape)
        )  # flatten 7 freqs by 16 channels array to (112,) shape array

        eeg_model.add(Dense(224))
        eeg_model.add(Activation("relu"))
        eeg_model.add(Dropout(dropout))

        eeg_model.add(Dense(448))
        eeg_model.add(Activation("relu"))
        eeg_model.add(Dropout(dropout))

        eeg_model.add(Dense(224))
        eeg_model.add(Activation("relu"))
        eeg_model.add(Dropout(dropout))

        eeg_model.add(Dense(112))
        eeg_model.add(Activation("relu"))
        eeg_model.add(Dropout(dropout))

        eeg_model.add(Dense(56))
        eeg_model.add(Activation("relu"))
        eeg_model.add(Dropout(dropout))

        eeg_model.add(Dense(1))
        eeg_model.add(Activation("sigmoid"))

        opt = tf.keras.optimizers.Adam(
            learning_rate=0.001,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=10e-8,
            decay=0.0,
            amsgrad=False,
        )

        eeg_model.compile(
            optimizer=opt, loss="binary_crossentropy", metrics=["accuracy"]
        )

        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2)
        history = eeg_model.fit(
            X_train,
            y_train,
            batch_size=64,
            epochs=200,
            validation_data=(X_val, y_val),
            shuffle=True,
        )

        self.model = eeg_model

        for i in range(9):
            temp_x_subset = X[i][:][:][:]
            print(i)

            temp_x_subset = np.expand_dims(temp_x_subset, axis=0)

            output = self.model.predict(temp_x_subset)

            print(output)

        self.model.save("saved_models/{}_model".format(self.file_name))
        # self.model.save('saved_model/my_model')

        self.stopAnimation()

    def startAnimation(self):
        self.movie.start()

    def stopAnimation(self):
        self.parent.session_window_button.setEnabled(True)
        self.parent.title.setText("Start a Session to try out the Model")
        self.parent.ml_model = self.model
        self.movie.stop()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = model_win()
    win.show()
    sys.exit(app.exec())
