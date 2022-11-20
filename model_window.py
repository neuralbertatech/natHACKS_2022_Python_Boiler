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

import time
import numpy as np

import os
###########################################################

class model_win(QWidget):
    def __init__(
        self,
        parent=None,
        csv_name=None,
    ):
        super().__init__()
        # self.csv_name = csv_name
        # self.csv_name = "C:\\Users\\eredm\\Documents\\GitHub\\natHACKS_2022_Python_Boiler\\data\\1001\\imu_boiler_1.csv"
        self.parent = parent

        self.setFixedSize(200, 200)

        #####################
        ##### Animation #####
        #####################

        self.label_animation = QLabel(self)

        self.movie = QMovie("utils/Loading_2.gif")
        self.label_animation.setMovie(self.movie)

        timer = QTimer(self)

        self.startAnimation()
        timer.singleShot(10000, self.stopAnimation)

        #### might not need
        self.show()

        X = []
        y = []

        # import data
        # restored_df = pd.DataFrame(np.transpose(restored_data))

        '''
        Need to add in a loop here that checks if the directory of the current csv_name
        query the 

        dirname = os.path.dirname(filepath)

        def find_csv_filenames( path_to_dir, suffix=".csv" ):
            filenames = listdir(path_to_dir)
            return [ filename for filename in filenames if filename.endswith( suffix ) ]

        filenames = find_csv_filenames("my/directory")
        for name in filenames:
        print name

        # then get full path for each with 

        path = os.path.join('dir', 'subdir', 'filename.ext')

        add each to the y and X

        '''

        dirname = os.path.dirname(self.parent.csv_name)
        
        def find_csv_filenames( path_to_dir, suffix=".csv" ):
            filenames = os.listdir(path_to_dir)
            return [ filename for filename in filenames if filename.endswith( suffix ) ]

        fnames = find_csv_filenames(dirname)
        for name in fnames:
            print(name)

        for fname in range(len(fnames)):
            path = os.path.join(dirname, fnames[fname])
            if fname == 0:    
                df = pd.read_csv(path)
            else:
                temp = pd.read_csv(path)
                pd = pd.concat([df,temp])
                
        # print(df)
        # df.columns = ['trigger','count','euler_1','euler_2','euler_3']
        print(df[0:-1])

        self.moves = self.parent.action_num

        targ_trigs = df[
            (df["trigger"] == 1000) | (df["trigger"] == 1001) | (df["trigger"] == 1002) | (df["trigger"] == 1003) |(df["trigger"] == 1004) | (df["trigger"] == 1005)
        ].index

        epoch_len = self.parent.epoch_len
        temp_targ = []

        for targ in range(len(targ_trigs)):
            temp_targ = df.iloc[targ_trigs[targ]: targ_trigs[targ]+ epoch_len, [2,3,4]]

            print(temp_targ)
            print(len(temp_targ))

            X.append(temp_targ)
            y.append(df.iloc[targ_trigs[targ]]["trigger"] - 1000)
            print(df.iloc[targ_trigs[targ]]["trigger"])
            temp_targ = []
        y = np.array(y)
        X = np.array(X)

        #################################
        # Define Model Architecture

        dropout = 0.2
        input_shape = (100, 3)


        imu_model = Sequential()
        imu_model.add(
            Flatten(input_shape=input_shape)
        )  # flatten 7 freqs by 16 channels array to (112,) shape array

        imu_model.add(Dense(224))
        imu_model.add(Activation("relu"))
        imu_model.add(Dropout(dropout))

        imu_model.add(Dense(448))
        imu_model.add(Activation("relu"))
        imu_model.add(Dropout(dropout))

        imu_model.add(Dense(224))
        imu_model.add(Activation("relu"))
        imu_model.add(Dropout(dropout))

        imu_model.add(Dense(112))
        imu_model.add(Activation("relu"))
        imu_model.add(Dropout(dropout))

        imu_model.add(Dense(56))
        imu_model.add(Activation("relu"))
        imu_model.add(Dropout(dropout))

        imu_model.add(Dense(self.moves))
        # imu_model.add(Dense(1))
        imu_model.add(Activation("softmax"))

        opt = tf.keras.optimizers.Adam(
            learning_rate=0.001,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=10e-8,
            decay=0.0,
            amsgrad=False,
        )

        imu_model.compile(
            optimizer=opt, 

            # loss="binary_crossentropy", 
            loss="sparse_categorical_crossentropy",
            # loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True),

            metrics=["accuracy"]

            # optimizer=opt, loss="sparse_categorical_crossentropy", metrics=["accuracy"]
        )

        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2)
        
        history = imu_model.fit(
            X_train,
            y_train,
            batch_size=64,
            epochs=200,
            validation_data=(X_val, y_val),
            shuffle=True,
        )

        print(history)

        self.model = imu_model

        for i in range(9):
            temp_x_subset = X[i][:][:]
            print(i)
            print(temp_x_subset)

            temp_x_subset = np.expand_dims(temp_x_subset, axis=0)

            output = self.model.predict(temp_x_subset)

            print(output)

        self.model.save("saved_models/{}_model".format(self.csv_name))
        # self.model.save('saved_model/my_model')

        self.stopAnimation()

    def startAnimation(self):
        self.movie.start()

    def stopAnimation(self):
        # self.parent.session_window_button.setEnabled(True)
        self.parent.title.setText("Start a Session to try out the Model")
        self.parent.ml_model = self.model
        self.movie.stop()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = model_win()
    win.show()
    sys.exit(app.exec())
