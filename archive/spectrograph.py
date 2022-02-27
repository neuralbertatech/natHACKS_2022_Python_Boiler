'''
This file contains a data window with spectrographs for eeg data display
It is started by menu_spectrograph, and can read file, simulate, or livestream from hardware
(currently only works with muse and ganglion openbci. Note that with ganglion, an lsl stream must be
started from the openbci gui)
It saves all its data as a csv at the end, unless it wasx reading from a file

Project ideas:
Live or file data display and analysis. Currently includes spectrogram, spectra, and raw,
as well as a very simple hypnogram. 
More complex and accurate simulation.


'''


import sys
from math import sqrt, acos, pi, sin
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtWidgets import *

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from multiprocessing import Process, Queue
from utils.lsl_functions.pyqt5_send_receive import *
from utils.pyqt5_widgets import MplCanvas
from utils.lsl_functions.muse_connect import send_muse
from utils.arduino import arduino_run
import utils.file_parsing.muse_csv_parser
from utils.lsl_functions.OpenBCI_connect_windows import send_openbci
import numpy as np
import time
import csv
import os
import pandas as pd
import sqlite3
from scipy import fft
# \u03B1 = alpha
# \u03B2 = beta
# \u03B8 = theta
# \u03B4 = delta

SIMULATE = 0
FILE = 1
LIVESTREAM = 2


class spectrograph_gui(QWidget):
    def __init__(self, hardware = None, model = None, fname = None, data_type = None, sim_type = None, parent=None, step = True, csv_name = 'eeg_log_file', arduino_port=0):
        # init from arguments
        self.parent = parent
        super(spectrograph_gui, self).__init__()
        self.fname = fname
        self.sim_type = sim_type
        self.hardware = hardware
        self.model = model
        timestamp = str(int(time.time()))
        self.csv_name = csv_name[:-4] + '_' + timestamp + ".csv"
        self.db_name = csv_name[:-4] + '_' + timestamp + ".db"
        self.conn = sqlite3.connect(self.db_name)
        self.cur = self.conn.cursor()
        self.step = step
        self.lock_to_end_clicked = False
        self.data_changed = True
        # self.arduino = arduino
        self.arduino_port = arduino_port
        self.arduino_process = None
        self.init_hardware_type()

        # MANUALLY SPECIFY COM PORT IF USING CYTON OR CYTON DAISY
        # if not specified, will use first available port
        # should be a string representing the COM port that the Cyton Dongle is connected to. 
        # e.g for Windows users 'COM3', for MacOS or Linux users '/dev/ttyUSB1
        self.com_port = None

        if data_type == 'Live stream':
            self.data_type = LIVESTREAM
        elif data_type == 'Simulate':
            self.data_type = SIMULATE
        elif data_type == 'File':
            self.data_type = FILE
        else:
            raise Exception('Unknown data type: {} Try "Live stream", "Simulate", or "File"'.format(data_type))

        # self.data_type = SIMULATE
        
        self.shown_data = np.array([[]])
        self.spectrogram = np.array([[]])
        self.window_left = self.window_right = 0
        self.full_length_fn = self.graph_full_length
        self.main_graph_fn = self.graph_main_graph_raw_trace
        self.full_length_drawn = False
        self.main_graph_drawn = False
        self.hypnogram_drawn = False
        plt.rcParams.update({'font.size': 8})
        self.is_stream_running = False
        self.processes = []
        # this is which channel the spectrograph shows
        self.curr_channel = -1
        self.data = [[] for _ in range(self.channels)]
        self.csv_length = 0
        self.data_width = 50

        self.data = np.array(self.csv_length).T
        self.plotted_data = self.data
        # setting background color
        self.setStyleSheet("background-color: #cfe2f3; font-size: 15px;")

        # setting window title
        if self.fname:
            self.setWindowTitle('Reading file: {}'.format(self.fname))
        else:
            self.setWindowTitle("Live streaming")
        self.setWindowIcon(QtGui.QIcon('utils/logo_icon.jpg'))

        # adding widgets to the window
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.plot_container = QWidget()
        self.plot_vbox = QVBoxLayout()

        self.title = QLabel("NeurAlbertaTech Muse Boiler")
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.title)

        # Create the full-length
        self.full_length = MplCanvas(self, width=10, height=0, dpi=100)

        self.full_length_vbox = QVBoxLayout()
        self.full_length_vbox.addWidget(self.full_length, 10)
        self.plot_vbox.addLayout(self.full_length_vbox, 2)

        # Create the hypnogram
        self.hypnogram = MplCanvas(self, width=50, height=20, dpi=100)
        self.hypnogram.axes.plot([0 if i % 6 <= 2 else 1 for i in range(100)])
        self.hypnogram_vbox = QVBoxLayout()
        self.hypnogram_vbox.addWidget(self.hypnogram)
        self.plot_vbox.addLayout(self.hypnogram_vbox, 1)

        # create the main graph
        self.main_graph = MplCanvas(self, width=100, height=100, dpi=100)

        self.main_graph_radio_container = QButtonGroup()
        self.main_graph_raw_trace = QRadioButton("Raw Trace")
        self.main_graph_raw_trace.clicked.connect(self.graph_main_graph_raw_trace)
        self.main_graph_spectra = QRadioButton("Spectra")
        self.main_graph_spectra.clicked.connect(self.graph_main_graph_spectra)
        self.main_graph_spectrogram = QRadioButton("Spectrogram")
        self.main_graph_spectrogram.clicked.connect(self.graph_main_graph_spectrogram)
        self.main_graph_radio_container.addButton(self.main_graph_raw_trace)
        self.main_graph_radio_container.addButton(self.main_graph_spectra)
        self.main_graph_radio_container.addButton(self.main_graph_spectrogram)

        self.main_graph_vbox = QVBoxLayout()
        self.main_graph_radio_hbox = QHBoxLayout()
        self.main_graph_radio_hbox.addSpacing(800)
        self.main_graph_radio_hbox.addWidget(self.main_graph_raw_trace)
        self.main_graph_radio_hbox.addWidget(self.main_graph_spectra)
        self.main_graph_radio_hbox.addWidget(self.main_graph_spectrogram)
        # here's a checkbox for whether to lock the display to the most recent data
        self.lock_to_end_checkbox = QCheckBox('Lock to most recent data')
        self.main_graph_radio_hbox.addWidget(self.lock_to_end_checkbox)
        self.lock_to_end_checkbox.stateChanged.connect(self.lock_to_end)
        self.main_graph_vbox.addWidget(self.main_graph, 10)
        self.main_graph_vbox.addLayout(self.main_graph_radio_hbox, 1)
        self.plot_vbox.addLayout(self.main_graph_vbox, 4)
        # self.layout.addWidget(self.main_graph,50,20,30,50)

        self.plot_container.setLayout(self.plot_vbox)
        self.layout.addWidget(self.plot_container)

        self.central_settings_vbox = QVBoxLayout()
        self.window_buttons_hbox = QHBoxLayout()

        
        self.comboBox = QComboBox()
        channel_names = ['All Channels']
        for i in range(self.channels):
            channel_names.append('Channel ' + str(i))
        self.comboBox.addItems(channel_names)
        self.comboBox.activated.connect(self.change_channel)
        self.window_left_button = QPushButton("Move Window Left")
        self.window_left_button.clicked.connect(self.move_window_left)
        self.window_right_button = QPushButton("Move Window Right")
        self.window_right_button.clicked.connect(self.move_window_right)
        self.window_buttons_hbox.addWidget(self.window_left_button)
        self.window_buttons_hbox.addWidget(self.window_right_button)
        self.central_settings_vbox.addLayout(self.window_buttons_hbox)
        self.central_settings_vbox.addWidget(self.comboBox)

        # if self.arduino:
        #     self.arduino_activate_button = QPushButton("Activate Arduino")
        #     self.arduino_activate_button.clicked.connect(self.activate_arduino)
        #     self.central_settings_vbox.addWidget(self.arduino_activate_button)

        self.settings_hbox = QHBoxLayout()
        self.settings_container = QWidget()
        self.window_resize = plus_minus_button(self.layout, 80, 55, 5, 10, 6, "Window Size", lambda t: (self.expand_window_sizes(t), self.get_window_time_range()))
        self.step_resize = plus_minus_button(self.layout, 90, 55, 5, 10, 6, "Step Size", lambda t: (True, self.data_points_to_range(t)))
        self.settings_hbox.addSpacing(100)
        self.settings_hbox.addWidget(self.window_resize)
        self.settings_hbox.addSpacing(200)
        self.settings_hbox.addLayout(self.central_settings_vbox)
        self.settings_hbox.addSpacing(200)
        self.settings_hbox.addWidget(self.step_resize)
        self.settings_hbox.addSpacing(100)
        self.settings_container.setLayout(self.settings_hbox)
        self.layout.addWidget(self.settings_container)
        # The plus-minus buttons

        # update timer
        self.timer = QtCore.QTimer()

        if self.data_type == FILE and self.step == True:
            self.read_in_file()
        else:
            self.start_data_stream()

        self.full_length_fn()
        self.main_graph_fn()
        return
    
    def init_hardware_type(self):
        # this function should run once, during __init__
        # let's set channels, sample rate, and expected data range based on hardware type
        # todo: change values for data types as appropriate

        print('init hardware is running with hardware',self.hardware,'model',self.model)
        if self.hardware == 'Muse':
            if self.model == 'Muse 2':
                self.srate = 250
                self.channels = 4
            elif self.model == 'Muse S':
                self.srate = 250
                self.channels = 4
        elif self.hardware == 'openBCI':
            if self.model == 'Ganglion':
                self.srate = 200
                self.channels = 4
            elif self.model == 'Cyton':
                print('using openbci cyton: REMEMBER TO MANUALLY SPECIFY COM PORT')
                self.srate = 250
                self.channels = 8
            elif self.model == 'Cyton-Daisy':
                print('using openbci cyton daisy: REMEMBER TO MANUALLY SPECIFY COM PORT')
                self.srate = 250
                self.channels = 16
        elif self.hardware == 'Blueberry':
            if self.model == 'Prototype':
                self.srate = 250
                self.channels = 4


    def activate_arduino(self):
        if self.arduino_process is None:
            self.arduino_process = Process(target = arduino_run, args = (int(self.arduino_port),), name = 'arduino process')
            self.arduino_process.start()
            self.processes.append(self.arduino_process)
        else:
            self.arduino_process.terminate()
            while self.arduino_process.is_alive():
                time.sleep(0.1)
            self.arduino_process.close()
            self.processes.pop()
            self.arduino_process = None

    def start_data_stream(self):
        # this starts the stream for simulating or reading from a file
        # stream runs with pylsl (simulate) or just a queue (file read)
        # either way, starts at least one new process which needs to be closed with stop_data_stream

        self.is_stream_running = True
        
        print('the stream data function is running in the pyqt5 window')
        global gq
        gq = Queue(250)
        
        cols = ','.join('eeg' + str(i) + ' real' for i in range(self.channels))
        self.cur.execute("CREATE TABLE data (" + cols + ');')
        # increase csv length for the two new lines we just added
        self.csv_length += 2   
        
        # starting processes to get data
        if self.data_type == SIMULATE:
            print(self.sim_type)
            if self.sim_type == 'Awake':
                self.sending_data = Process(target = sim_awake_eeg, args = (self.srate,self.channels,), name = 'sim data stream process', daemon = True)
            elif self.sim_type == 'Asleep':
                self.sending_data = Process(target = sim_asleep_eeg, args = (self.srate,self.channels,), name = 'sim data stream process', daemon = True)
            else:
                self.sending_data = Process(target = send_eeg, args = (self.srate,self.channels,True,), name = 'sim data stream process', daemon = True)
            self.sending_data.start()
            self.receiving_data = Process(target = receive_eeg, args = (gq,False,self.channels,), name = 'receiving data process', daemon = True)
            self.receiving_data.start()
        elif self.data_type == LIVESTREAM:
            if self.hardware == 'Muse':
                self.sending_data = Process(target = send_muse, args = (self.srate,self.channels,), name = 'hardware data stream process', daemon = True)
                self.sending_data.start()
                self.receiving_data = Process(target = receive_eeg, args = (gq,False,self.channels,), name = 'receiving data process', daemon = True)
                self.receiving_data.start()
            elif self.hardware == 'openBCI':
                if self.model == 'Ganglion':
                    print('Ganglion: user must start eeg stream from openbci gui')
                elif self.model == 'Cyton' or self.model == 'Cyton-Daisy':
                    self.sending_data = Process(target = send_openbci, args = (self.channels,self.com_port), name = 'hardware data stream process', daemon = True)
                    self.sending_data.start()
                self.receiving_data = Process(target = receive_eeg, args = (gq,False,self.channels,), name = 'receiving data process', daemon = True)
                self.receiving_data.start()
        elif self.data_type == FILE:
            if self.step == False:
                # we are reading from a file as tho it's live
                self.reading_file = Process(target = read_file, args = (self.fname, self.hardware, self.model, gq, self.srate,self.channels,), name = 'file reading process', daemon = True)
                self.reading_file.start()

        # updating list of processes
        if self.data_type == FILE and self.step == False:
            self.processes.append(self.reading_file)
        elif self.model == 'Ganglion':
            self.processes.append(self.receiving_data)
        else:
            self.processes.extend([self.sending_data, self.receiving_data])

        # when the timer goes it will call update - that will move data from the q to the database
        self.timer.timeout.connect(self.update_eeg)
        self.timer.start(int(1000/self.srate))
        # here's a new timer
        # when it goes it will call a figure update function
        self.display_timer = QtCore.QTimer()
        self.display_timer.timeout.connect(self.update_data)
        self.display_timer.start(100)
        return

    def stop_data_stream(self, closing = False):
        # stop the stream process, turn off the timer
        # closing is whether or not this was called by closeEvent
        print('stop eeg stream ran')
        self.timer.timeout.disconnect(self.update_eeg)
        self.display_timer.stop()

        _ = [process.terminate() for process in self.processes]
        while any(process.is_alive() for process in self.processes):
            time.sleep(0.01)
        _ = [process.close() for process in self.processes]
        self.is_stream_running = False

    def closeEvent(self, event):
        # this code will autorun just before the window closes
        # we will check whether streams are running, if they are we will close them
        print('close event works')
        if self.is_stream_running:
            # calling with True because we are closing
            self.stop_data_stream(closing = True)
        
        # save database as csv if we weren't file reading
        if self.data_type != FILE:
            self.cur.execute("SELECT * FROM data;")
            with open(self.csv_name, mode='a',newline = '') as file:
                fwriter = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                fwriter.writerow(["\"eeg"+str(i)+"\"" for i in range(self.channels)])
                fwriter.writerows(self.cur)

        self.conn.close()
        os.remove(self.db_name)
        event.accept()
    
    def read_in_file(self):
        '''
        this runs instead of start data_stream when stepping through a file
        it reads the whole file into the database
        '''
        cols = ','.join('eeg' + str(i) + ' real' for i in range(self.channels))
        self.cur.execute("CREATE TABLE data (" + cols + ');')  

        with open(self.fname, mode = 'r') as file:
            csv_reader = csv.reader(file, delimiter=',', quoting = csv.QUOTE_NONNUMERIC)
            line_count = 0
            for row in csv_reader:
                if line_count <= 1:
                    line_count += 1
                    continue
                # only take first [channels] numbers to exclude 0 column and time
                sample = row[:self.channels]
                # print('fr read {}'.format(sample))
                self.cur.execute("INSERT INTO data VALUES (" + ','.join('?' for _ in range(self.channels)) + ")", sample)
                line_count += 1

        self.csv_length += line_count

        # here's a new timer
        # when it goes it will call a figure update function
        self.display_timer = QtCore.QTimer()
        self.display_timer.timeout.connect(self.update_data)
        self.display_timer.start(100)

        return

    
    def update_eeg(self):
        # this should run every time the timer goes, it updates the data display (by calling whatever updates the display)
        # pdb.set_trace()

        # all debug messages for update have been removed because they clog up the display at high sample rates
        # uncomment them if you need to debug
        # print('eeg update start')
        global gq
        if not gq.empty():
            # print('u gq not empty\n')
            samples = []
            while not gq.empty():
                sample = gq.get()
                # process the delta
                if self.data_type == FILE:
                    # file reading doesn't send timestamps
                    samples.append(sample)
                elif self.data_type == SIMULATE:
                    # removing timestamp
                    samples.append(sample[0])
                else:
                    # removing timestamp
                    samples.append(sample[0][:self.channels])

            self.cur.executemany("INSERT INTO data VALUES (" + ','.join('?' for _ in range(self.channels)) + ")", samples)
            self.csv_length += len(samples)
            

        else:
            # print('u gq empty\n')
            pass
    
    def update_data(self):
        # runs every time we need to update display
        # pulls data from csv and updates data with it, calls update functions of figures
        start_line = self.csv_length - self.data_width
        if start_line < 2:
            start_line = 2
        new_data = [1]
        # new_data will be [] if we haven't managed to receive any data yet
        if new_data != []:
            # new_data is now a list of lists, each inner list is an instant containing channels data points
            # so is self.data
            # now we update our data and the figures
            # print('new data shape {} old data shape {}'.format(np.array(new_data).shape,self.data.shape))
            # print('new data {} old data {}'.format(np.array(new_data), self.data))
            # self.data = np.append(self.data, np.array(new_data), axis=0)
            self.full_length_fn()
            if self.lock_to_end_clicked:
                self.main_graph_fn()

    def keyPressEvent(self, event):
        pass
        # if event.key() == QtCore.Qt.Key_Right:
        #     self.move_window_right()
        # elif event.key() == QtCore.Qt.Key_Left:
        #     self.move_window_left()
    
    def change_channel(self):
        # runs when user selcts channel from channel dropdown
        # sets our current channel (to be plotted on spectrogram) to new one
        # calls to update display
        self.curr_channel = self.comboBox.currentIndex() - 1
        self.full_length_fn()
        self.main_graph_fn()
    
    def lock_to_end(self, state):
        # runs when state of lock to end checkbox is changed
        # if checked, locks window to end and disables buttons
        # if unchecked, enables buttons
        if state == QtCore.Qt.Checked:
            window_size = self.window_right - self.window_left
            self.lock_to_end_clicked = True
            self.window_resize.setEnabled(False)
            self.step_resize.setEnabled(False)
            self.full_length_fn()
            self.main_graph_fn()
        else:
            self.lock_to_end_clicked = False
            self.window_resize.setEnabled(True)
            self.step_resize.setEnabled(True)
    
    def graph_full_length(self):
        ticks = np.linspace(0, self.csv_length / self.srate, 12)
        ax = self.full_length.axes
        ax.cla()
        ax.set_ylabel('Voltage (${\mu}$V)')
        ax.set_title("Timeline")
        ax.set_xlim(0, self.csv_length)
        ax.set_xticks(np.linspace(0, self.csv_length, 12))
        ax.set_xticklabels(np.round(ticks, decimals=3))
        ax.get_yaxis().set_visible(False)

        if self.lock_to_end_clicked:
            self.window_right = self.csv_length
            self.window_left = self.window_right - self.window_resize.get_content() * 2 # 2x since the content represents dist of window panel from middle

        ax.vlines([self.window_left, self.window_right], 0, 1, color='black', linewidth=3)
        ax.vlines([i for i in range(self.srate, self.csv_length, self.srate)], 0, 1, color='black', linewidth=1, linestyles='dashed')
        if self.full_length_drawn:
            self.update_graph(self.full_length)
        self.full_length_drawn = True
        return

    def graph_hypnogram(self):
        """
        For hypnogram:
        Get the mean of a window under the 'delta' region of the spectrogram (-0.5 - 31.5, bottom quarter)
            - Similar to a convolution, or max pooling
        Hardcode a threshold (for now), and if the mean is above the threshold label it as a sleep state on the hypnogram. Otherwise, plot it as other.
        """

        self.hypnogram.axes.cla()
        
        delta = self.spectrogram[-32:,:]
        means = np.mean(delta, axis=0)

        self.hypnogram.axes.step([i for i in range(len(means))], means > np.mean(means))
        self.hypnogram.axes.set(title="Hypnogram", ylim=(-0.1, 1.1), yticks=[0, 1], yticklabels=["Other", "SWS"])
        self.hypnogram.axes.set_ylabel('Sleep\nState', rotation='horizontal',va="center", ha='right')
        if self.hypnogram_drawn:
            self.update_graph(self.hypnogram)
        self.hypnogram_drawn = True

    def get_main_graph_data(self):
        # Updates the data to the most recent window selection
        if self.lock_to_end_clicked:
            self.cur.execute("SELECT * FROM data ORDER BY rowid DESC LIMIT ?;", (int(self.window_right - self.window_left),))
            self.shown_data = np.array([data for data in self.cur])[::-1]
        elif self.data_changed:
            self.cur.execute("SELECT * FROM data WHERE rowid BETWEEN ? AND ?", (self.window_left, self.window_right))
            self.shown_data = np.array([data for data in self.cur])

        # https://stackoverflow.com/questions/63640027/spectrogram-in-python-using-numpy
        # Accessed July 13th, 2021
        if len(self.shown_data):
            data = self.shown_data.T[self.curr_channel]
            N, S = 256, []

            for k in range(0, data.shape[0]+1, N):
                x = fft.fftshift(fft.fft(data[k:k+N], n=N))[N//2:N]
                Pxx = 10*np.log10(np.real(x*np.conj(x)))
                S.append(Pxx)

            self.spectrogram = np.array(S).T

    def main_graph_boiler(self):
        # Call this function AFTER plotting the data
        self.graph_hypnogram()
        range_start, range_end = self.get_window_time_range()
        ticks = np.linspace(*self.main_graph.axes.get_xlim(), 6)
        tick_labels = np.linspace(range_start, range_end, 6)

        self.main_graph.axes.set_xticks(ticks)
        self.main_graph.axes.set_xticklabels(np.round(tick_labels, decimals=3)) # labels along the bottom
        self.data_changed = False
        self.main_graph.axes.set_title("Window View")
        self.main_graph.axes.set_xlabel('Time (s)')
        return

    def graph_main_graph_raw_trace(self):
        self.main_graph_fn = self.graph_main_graph_raw_trace
        self.get_main_graph_data()
        self.main_graph.axes.cla()
        self.main_graph.axes.plot(self.shown_data)
        self.main_graph.axes.set_ylabel('Voltage (${\mu}$V)')
        self.main_graph_boiler()
        if self.main_graph_drawn:
            self.update_graph(self.main_graph)
        self.main_graph_drawn = True
        return

    def graph_main_graph_spectra(self):
        self.main_graph_fn = self.graph_main_graph_spectra
        self.get_main_graph_data()
        self.main_graph.axes.cla()
        self.main_graph.axes.plot(np.abs(np.fft.fft(self.shown_data, axis = 0)))
        self.main_graph.axes.set_ylabel('Intensity')
        self.main_graph.axes.set_xlabel('Frequency (Hz)')
        self.main_graph_boiler()
        if self.main_graph_drawn:
            self.update_graph(self.main_graph)
        self.main_graph_drawn = True
        return

    def graph_main_graph_spectrogram(self):
        self.main_graph_fn = self.graph_main_graph_spectrogram
        self.get_main_graph_data()
        self.main_graph.axes.cla()

        if len(self.shown_data) and self.shown_data.shape[1] < 256 * 5: # N = 256
            print("WARNING: The window specified is quite small for a spectrogram. Consider increasing the size of the window to at least 8s.")
        
        # Spectrogram rendering:
        self.main_graph.axes.imshow(self.spectrogram, origin='lower', aspect='auto')

        self.main_graph.axes.set_ylabel('Frequency (Hz)')
        self.main_graph.axes.set_yticks([ -0.5, 15.5, 31.5, 47.5, 63.5, 79.5, 95.5, 111.5, 127.5 ])
        self.main_graph.axes.set_yticklabels([None, str(u"\u03B4"), None, str(u"\u03B8"), None, str(u"\u03B1"), None, str(u"\u03B2"), None])
        self.main_graph_boiler()
        if self.main_graph_drawn:
            self.update_graph(self.main_graph)
        self.main_graph_drawn = True
        return

    def update_graph(self, graph):
        graph.draw()
        graph.flush_events()
        return

    def move_window_left(self):
        step_size = self.step_resize.sizes[self.step_resize.size_i]
        if self.window_left - step_size >= 0:
            self.window_left -= step_size
            self.window_right -= step_size
            self.data_changed = True
            self.full_length_fn()
            self.main_graph_fn()
        return

    def move_window_right(self):
        step_size = self.step_resize.sizes[self.step_resize.size_i]
        if self.window_right + step_size <= self.csv_length:
            self.window_left += step_size
            self.window_right += step_size
            self.data_changed = True
            self.full_length_fn()
            self.main_graph_fn()
        return

    def expand_window_sizes(self, size_diff):
        midpoint = (self.window_left + self.window_right) // 2
        if not (size_diff > 0 and midpoint - size_diff >= 0) or not (midpoint + size_diff < self.csv_length):
            print("Cannot expand window, doing so would push window beyond graph boundaries")
            return False
        else:
            self.window_left = midpoint - size_diff
            self.window_right = midpoint + size_diff
        
        self.data_changed = True
        self.full_length_fn()
        self.main_graph_fn()
        return True

    """
    Gets the points in time represented by each window border
    """
    def get_window_time_range(self):
        return (self.window_left / self.srate, self.window_right / self.srate)

    """
    Gets the time that has elapsed within a given span of points
    """
    def data_points_to_range(self, points):
        return 0, points / self.srate

class plus_minus_button(QWidget):
    sizes = [ 0, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    def __init__(self, layout, y, x, h, w, content_w, caption, graph_adjustment):
        assert content_w < w
        super(plus_minus_button, self).__init__()
        self.layout = layout
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.graph_adjustment = graph_adjustment
        self.size_i = 0
        self.content_w = content_w
        self.button_w = (w - content_w) // 2
        self.sizes_i = 0
        self.plus_button = QPushButton("+")
        self.minus_button = QPushButton("-")
        self.plus_button.clicked.connect(self.increment_content)
        self.minus_button.clicked.connect(self.decrement_content)
        _, (left, right) = self.graph_adjustment(0)
        self.label = QLabel(str(right-left) + ' s')
        self.caption = QLabel(str(caption))
        self.vbox = QVBoxLayout()
        self.hbox = QHBoxLayout()

        # self.hbox.addSpacing(500)
        self.hbox.addWidget(self.minus_button, self.button_w)
        self.hbox.addWidget(self.label, self.content_w)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.hbox.addWidget(self.plus_button, self.button_w)
        # self.hbox.addSpacing(500)
        self.vbox.addLayout(self.hbox)
        self.hbox.setAlignment(QtCore.Qt.AlignCenter)
        self.vbox.addWidget(self.caption)
        self.caption.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(self.vbox)
        self.vbox.setAlignment(QtCore.Qt.AlignCenter)


    def increment_content(self):
        if self.size_i < len(self.sizes) - 1:
            self.size_i += 1
        else:
            return
        adjust_success, (left, right) = self.graph_adjustment(int(self.sizes[self.size_i]))
        if adjust_success:
            self.label.setText(str(round(right-left, 3)) + ' s')
        else:
            self.size_i -= 1
            
    def decrement_content(self):
        if 0 < self.size_i:
            self.size_i -= 1
        else:
            return
        adjust_success, (left, right) = self.graph_adjustment(int(self.sizes[self.size_i]))
        if adjust_success:
            self.label.setText(str(round(right-left, 1)) + ' s')
        else:
            self.size_i += 1

    def get_content(self):
        return self.sizes[self.size_i]


if __name__ == "__main__":
    app = QApplication(sys.argv)    
    Form = QMainWindow()

    # run to read a file (must change path to be appropriate to your computer)  
    # ui = spectrograph_gui(hardware = 'Muse', model = 'Muse S', data_type = 'File', fname = 'C:/Users/madel/Documents/GitHub/NAT_Boilers/Muse/data/Muse_sample_1.csv', parent = Form, csv_name = 'eeg_log_file.csv') 
    
    # run to take live data from muse
    ui = spectrograph_gui(hardware = 'Muse', model = 'Muse S', data_type = 'Live stream', parent = Form) 
    
    ui.show()    
    sys.exit(app.exec_())