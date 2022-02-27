'''
This is the menu that starts the spectrograph
It allows the user to decide of file reading, simulation, or livestreaming from hardware.
And to select the hardware they're using/emulation, as well as the file, arduino port, etc

'''


import sys
from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtWidgets import *

import matplotlib

matplotlib.use('Qt5Agg')

import numpy as np
import random
import time
import os

# from spectrograph import spectrograph_gui
from baseline_window import baseline_win
from impedance_window import impedance_win
from session_window import session_win 
from model_window import model_win # animation fix needed
# results not implemented yet
from graph_window import graph_win

import tensorflow as tf

if sys.platform == 'win32':
    from arduino_windows import ard_wind_on as ard_turn_on
else:
    from arduino_mac import ard_mac_on as ard_turn_on

# import pdb


# let's make a menu window class
class MenuWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()

        ####################################
        ##### Init Main Window Globals #####
        #################################### 

        '''
        -------------------INPUTS-------------------|    
        |                  TITLE                    |
        |       HARDWARE              TYPE          |
        |       MODEL                 PORT          |
        |       CSV                   ARDUINO       |
        |                                           |
        |------------------ACTIONS------------------|
        |                                           |
        |    IMPED       BASELINE        SESSION    |
        |    ARDUINO     MODEL           RESULTS    |
        |                GRAPH                      |
        |                                           |
        |-------------------------------------------|

        '''

        self.setMinimumSize(900,900)
        
        # self.setStyleSheet("background-color: gray;")
        # setting window title and icon
        self.setWindowTitle('PyQt5 Menu')
        self.setWindowIcon(QtGui.QIcon('utils/logo_icon.jpg'))
        
        # init layout
        self.layout = QGridLayout()
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        ### DEBUG ###
        self.debug = True

        if self.debug == True:
            self.bci_serial_port = 'COM1'
            self.arduino_con = 'Debug'
            self.arduino_serial_port = 'COM2'

        ###################################
        ##### Init GUI Input Elements #####
        ################################### 

        ### INIT INPUT LAYOUTS ###
        # Create layouts explicitly for all GUI input fields
        self.title_layout = QHBoxLayout() 
        self.hardware_layout = QVBoxLayout()
        self.model_layout = QVBoxLayout()
        self.type_layout = QVBoxLayout()
        self.port_layout = QVBoxLayout()
        self.csv_layout = QVBoxLayout()
        self.arduino_layout = QVBoxLayout()
        self.limb_layout = QVBoxLayout()

        '''
        |------------------INPUTS-------------------|    
        |                                           |
        |       HARDWARE              TYPE          |
        |       MODEL                 PORT          |
        |       CSV                   ARDUINO       |
        |                   LIMB*                   |
        |                                           |
        |-------------------------------------------|
        '''
        
        ### TITLE ###
        self.title = QLabel()
        self.title.setFont(QtGui.QFont('Arial',14))
        self.title.setText('Select hardware')
        self.title_layout.addWidget(self.title)
        
        ### HARDWARE ###
        # drop down menu to decide what hardware
        self.hardware_dropdown = QComboBox()
        self.hardware_dropdown.setPlaceholderText('Select hardware')
        self.hardware_dropdown.addItems(['openBCI'])
        self.hardware_dropdown.activated.connect(self.handle_hardware_choice)
        self.hardware_label = QLabel('Select hardware')
        self.hardware_layout.addWidget(self.hardware_label)
        self.hardware_layout.addWidget(self.hardware_dropdown)

        ### MODEL ###
        # drop down menu for model of hardware
        self.model_dropdown = QComboBox()
        self.model_dropdown.setPlaceholderText('Select model')
        self.model_label = QLabel('Select model')
        self.model_dropdown.setEnabled(False) # starts disabled
        self.model_dropdown.activated.connect(self.handle_model_choice)
        self.model_layout.addWidget(self.model_label)
        self.model_layout.addWidget(self.model_dropdown)

        ### CSV ###
        self.csv_name_edit = QLineEdit('eeg_log_file.csv')
        self.csv_name_edit.returnPressed.connect(self.csv_name_changed)
        self.csv_name = 'eeg_log_file.csv'
        self.csv_label = QLabel('CSV name to save to')
        self.csv_layout.addWidget(self.csv_label)
        self.csv_layout.addWidget(self.csv_name_edit)

        ### DATATYPE ###
        # drop down menu for simulate or live (previously included file step through)
        self.type_dropdown = QComboBox()
        self.type_dropdown.setPlaceholderText('Select data type')
        self.type_dropdown.addItems(['Task live','Task simulate'])
        self.type_dropdown.activated.connect(self.handle_type_choice)
        self.type_label = QLabel('Select data type')
        self.type_layout.addWidget(self.type_label)
        self.type_layout.addWidget(self.type_dropdown)
        if self.debug == True:
            self.type_dropdown.setEnabled(True) # start disabled
        else:
            self.type_dropdown.setEnabled(False) # start disabled

        ### PORT ###
        self.openbci_label = QLabel("OpenBCI Serial Port")
        self.openbci_port = QLineEdit()
        self.openbci_port.setEnabled(False)
        self.port_layout.addWidget(self.openbci_label)
        self.port_layout.addWidget(self.openbci_port)
        self.openbci_port.setPlaceholderText("Enter Port # (Integers Only)") 
        self.openbci_port.textEdited.connect(self.handle_bci_port)

        ### ARDUINO ###
        self.arduino_label = QLabel("Arduino Settings")
        self.arduino_dropdown = QComboBox()
        self.arduino_dropdown.setPlaceholderText('Select connection to arduino')
        self.arduino_dropdown.addItems(['Wired','NeuroStimDuino','Wireless','Debug'])
        self.arduino_dropdown.activated.connect(self.handle_arduino_dropdown)
        self.arduino_port = QLineEdit()
        self.arduino_port.setEnabled(False)
        self.arduino_port.setPlaceholderText("Enter Port # (Integers Only)") 
        self.arduino_port.textEdited.connect(self.handle_arduino_port)
        self.arduino_layout.addWidget(self.arduino_label)
        self.arduino_layout.addWidget(self.arduino_dropdown)
        self.arduino_layout.addWidget(self.arduino_port)
        # self.arduino_process = None

        ### LIMB ###
        self.limb_sub_layout = QHBoxLayout()
        self.limb_label = QLabel('Which arm is the target?')
        self.limb_rbtn1 = QRadioButton('Left Arm')
        self.limb_rbtn2 = QRadioButton('Right Arm')
        self.limb_rbtn1.toggled.connect(self.onClicked)
        self.limb_rbtn2.toggled.connect(self.onClicked)
        self.limb_sub_layout.addWidget(self.limb_rbtn1)
        self.limb_sub_layout.addWidget(self.limb_rbtn2)
        self.limb_layout.addWidget(self.limb_label)
        self.limb_layout.addLayout(self.limb_sub_layout)

        ### ADD INPUT SUBLAYOUTS TO MAIN ###
        self.layout.setContentsMargins(100,100,100,100)
        self.hardware_layout.setContentsMargins(50,50,50,50)
        self.model_layout.setContentsMargins(50,50,50,50)
        self.csv_layout.setContentsMargins(50,50,50,15)
        self.type_layout.setContentsMargins(50,50,50,50)
        self.port_layout.setContentsMargins(50,50,50,50)
        self.arduino_layout.setContentsMargins(50, 50, 50, 15)
        self.limb_layout.setContentsMargins(50, 15, 50, 25)
        self.layout.addLayout(self.title_layout,0,0,1,-1, QtCore.Qt.AlignHCenter)
        self.layout.addLayout(self.hardware_layout,1,0)
        self.layout.addLayout(self.model_layout,2,0)
        self.layout.addLayout(self.csv_layout,3,0)
        self.layout.addLayout(self.type_layout,1,1)
        self.layout.addLayout(self.port_layout,2,1)
        self.layout.addLayout(self.arduino_layout, 3, 1)
        self.layout.addLayout(self.limb_layout, 4,0,1,-1, QtCore.Qt.AlignHCenter)

        ####################################
        ##### Init GUI Action Elements #####
        ####################################

        '''
        |------------------ACTIONS------------------|
        |                                           |
        |    IMPED       BASELINE        SESSION    |
        |    ARDUINO     MODEL           RESULTS    |
        |                GRAPH                      |
        |-------------------------------------------|
        '''

        # here is a button to actually start a impedance window
        self.impedance_window_button = QPushButton('Impedance Check')
        self.impedance_window_button.setEnabled(False)
        self.layout.addWidget(self.impedance_window_button,5,0, 1, 1, QtCore.Qt.AlignHCenter)
        self.impedance_window_button.clicked.connect(self.open_impedance_window)

        # here is a button to start the arduino window
        self.arduino_window_button = QPushButton('Turn on Arduino')
        self.arduino_window_button.setEnabled(False)
        self.layout.addWidget(self.arduino_window_button,6,0, 1, 1, QtCore.Qt.AlignHCenter)
        self.arduino_window_button.clicked.connect(self.open_arduino_window) # IMPLEMENT THIS FUNCTION

        # here is a button to actually start a data window
        self.baseline_window_button = QPushButton('Start Baseline')
        self.baseline_window_button.setEnabled(False)
        self.layout.addWidget(self.baseline_window_button,5,0, 1, -1, QtCore.Qt.AlignHCenter)
        self.baseline_window_button.clicked.connect(self.open_baseline_window)

        # here is a button to train the model
        self.model_window_button = QPushButton('Train Model')
        ##########################################################
        self.model_window_button.setEnabled(True) # set to false for deployment
        self.layout.addWidget(self.model_window_button,6,0, 1, -1, QtCore.Qt.AlignHCenter)
        self.model_window_button.clicked.connect(self.open_model_window)

        # here is a button to start the session
        self.session_window_button = QPushButton('Start Session')
        if self.debug == True:
            self.session_window_button.setEnabled(True)
        else:
            self.session_window_button.setEnabled(False)
        self.layout.addWidget(self.session_window_button,5,1, 1, -1, QtCore.Qt.AlignHCenter)
        self.session_window_button.clicked.connect(self.open_session_window) # IMPLEMENT THIS FUNCTION

        # here is a button to display results of the session
        self.results_window_button = QPushButton('Results')
        self.results_window_button.setEnabled(False)
        self.layout.addWidget(self.results_window_button,6,1, 1, -1, QtCore.Qt.AlignHCenter)
        self.results_window_button.clicked.connect(self.open_results_window) # IMPLEMENT THIS FUNCTION

        # here is a button to display graph
        self.graph_window_button = QPushButton('Graph')
        self.graph_window_button.setEnabled(True)
        self.layout.addWidget(self.graph_window_button,7,0, 1, -1, QtCore.Qt.AlignHCenter)
        self.graph_window_button.clicked.connect(self.open_graph_window) # IMPLEMENT THIS FUNCTION

        # this is a variable to show whether we have a data window open
        self.data_window_open = False

        # this is a variable to show whether we have a impedance window open
        self.impedance_window_open = False

        # init variable for saving temp csv name
        self.csv_name = None

        # init variables for model
        self.ml_model = None

        # targ limb
        self.targ_limb = None 

        if self.debug == True:
            self.hardware = 'openBCI' 
            self.model = 'Cyton-Daisy'
            self.data_type = 'Task simulate'
            self.targ_limb = 1
            self.arduino_con = 'Debug'
            self.arduino_serial_port = 'COM1'
            self.csv_name = 'eeg_log_file_1639676920'
            self.ml_model = tf.keras.models.load_model('saved_models/{}_model'.format(self.csv_name))
            # self.ml_model = tf.keras.models.load_model('saved_model/my_model')

    def closeEvent(self, event):
        # this code will autorun just before the window closes
        # we will check whether streams are running, if they are we will close them
        if self.data_window_open:
            self.data_window.close()
        event.accept()

    #########################################
    ##### Functions for Handling Inputs #####
    #########################################  

    def handle_hardware_choice(self):
        self.hardware = self.hardware_dropdown.currentText()
        # handle the choice of hardware - by opening up model selection
        self.model_dropdown.setEnabled(True)
        self.type_dropdown.setEnabled(False)
        self.type_dropdown.setCurrentIndex(-1)
        self.title.setText('Select model')
        self.model_dropdown.clear()
        if self.hardware_dropdown.currentText() == 'openBCI':
            self.model_dropdown.addItems(['Ganglion','Cyton','Cyton-Daisy'])
        elif self.hardware_dropdown.currentText() == 'Muse':
            self.model_dropdown.addItems(['Muse 2','Muse S'])
        elif self.hardware_dropdown.currentText() == 'Blueberry':
            self.model_dropdown.addItem('Prototype')
    
    def handle_model_choice(self):
        # handle the choice of model by opening up data type selection
        self.model = self.model_dropdown.currentText()
        self.baseline_window_button.setEnabled(False)
        self.openbci_port.setEnabled(False)
        self.type_dropdown.setEnabled(True)
        self.type_dropdown.setCurrentIndex(-1)
        self.title.setText('Select data type')

    def csv_name_changed(self):
        # this runs when the user hits enter on the text edit to set the name of the csv log file
        # first we check if file already exists
        print('text is {}'.format(self.csv_name_edit.text()))
        if not self.csv_name_edit.text().endswith('.csv'):
            # add .csv ending if absent
            self.csv_name_edit.setText(self.csv_name_edit.text() + '.csv')
        print('csv name after adding ending {}'.format(self.csv_name_edit.text()))
        if os.path.isfile(self.csv_name_edit.text()):
            # chop off .csv ending, add number, readd .csv
            self.csv_name = self.csv_name_edit.text()[:-4] + '_1.csv'
        else:
            self.csv_name = self.csv_name_edit.text()

    def handle_type_choice(self):
        # handle the choice of data type
        self.data_type = self.type_dropdown.currentText()
        if self.data_type == 'Task live':
            self.title.setText('Select BCI Hardware Port')
            self.openbci_port.setEnabled(True)
        elif self.data_type == 'Task simulate':
            self.baseline_window_button.setEnabled(True)
            self.impedance_window_button.setEnabled(True)
            self.title.setText('Check Impedance or Start Baseline')
        
    def handle_bci_port(self):
        # check for correct value entering and enable type dropdown menu
        if self.openbci_port.text().isdigit():
            self.type_dropdown.setEnabled(True)
            self.bci_serial_port = "COM" + self.openbci_port.text()
            if self.data_type == 'Task live':
                self.baseline_window_button.setEnabled(True)
                self.impedance_window_button.setEnabled(True)
            self.title.setText('Check Impedance or Start Baseline')
        else:
            # print("Error: OpenBCI port # must be an integer.")
            self.baseline_window_button.setEnabled(False)
            self.title.setText('Select BCI Hardware Port')

    def handle_arduino_dropdown(self):
        # check if arduino checkbox is enabled
        self.arduino_con = self.arduino_dropdown.currentText()
        self.arduino_port.setEnabled(True)
        if self.arduino_port.text().isdigit():
            self.arduino_window_button.setEnabled(True)
            self.arduino_serial_port = "COM" + self.arduino_port.text()
        else: 
            self.arduino_window_button.setEnabled(False)

    def handle_arduino_port(self):
        # check for correct value entering and enable type dropdown menu
        if self.arduino_port.text().isdigit():
            self.arduino_window_button.setEnabled(True)
            self.arduino_serial_port = "COM" + self.arduino_port.text()
        else:
            self.arduino_window_button.setEnabled(False)

    def onClicked(self):
        radioBtn = self.sender()
        if radioBtn.isChecked():
            if radioBtn.text() == 'Left Arm':
                self.targ_limb = 1
        elif radioBtn.text() == 'Right Arm':
                self.targ_limb = 2

    #########################################
    ##### Functions for Opening Windows #####
    #########################################    

    def open_arduino_window(self):
        # this actually starts the arduino testing window
        # called by user pressing button, which is enabled by selecting from dropdowns
        # if self.arduino_process is not None:
        #     self.arduino_process.terminate()
        #     while self.arduino_process.is_alive():
        #         time.sleep(0.1)
        #     self.arduino_process.close()
        #     self.arduino_process = None
        if self.arduino_port.text().isdigit() != True:
            print("Error: arduino port # must be an integer.")
        else:
            self.data_window = ard_turn_on(
                parent = self,
                arduino_con = self.arduino_con,
                arduino_port=self.arduino_serial_port,
            )
            self.data_window.show()
            self.data_window.show()
            self.is_data_window_open = True
    
    def open_impedance_window(self):
        self.impedance_window = impedance_win(
        parent = self,
        hardware = self.hardware, 
        model = self.model, 
        data_type = self.data_type, 
        serial_port = self.bci_serial_port,
        )   
        self.impedance_window.show()
        self.is_impedance_window_open = True

    def open_baseline_window(self):
        self.data_window = baseline_win(
            hardware = self.hardware, 
            model = self.model,
            data_type = self.data_type, 
            csv_name = self.csv_name, 
            parent = self,
            serial_port = self.bci_serial_port,
            )
        self.data_window.show()
        self.is_data_window_open = True

    def open_model_window(self):
        self.impedance_window = model_win(
        parent = self,
        hardware = self.hardware, 
        model = self.model,
        targ_limb = self.targ_limb,
        )   
        self.impedance_window.show()
        self.is_impedance_window_open = True

    def open_session_window(self):
        self.session_window = session_win(
            hardware = self.hardware, 
            model = self.model,
            targ_limb = self.targ_limb,
            data_type = self.data_type, 
            csv_name = self.csv_name, 
            parent = self,
            serial_port = self.bci_serial_port,
            arduino_con = self.arduino_con,
            arduino_port=self.arduino_serial_port,
            )
        self.session_window.show()
        self.is_session_window_open = True

    def open_results_window(self):
        self.session_window = session_win(
            hardware = self.hardware, 
            model = self.model,
            data_type = self.data_type, 
            csv_name = self.csv_name, 
            parent = self,
            arduino_port=self.arduino_port.text(),
            serial_port = self.bci_serial_port,
            )
        self.session_window.show()
        self.is_session_window_open = True

    def open_graph_window(self):
        self.graph_window = graph_win(
        parent = self,
        hardware = self.hardware, 
        model = self.model, 
        data_type = self.data_type, 
        serial_port = self.bci_serial_port,
        )   
        self.graph_window.show()
        self.is_graph_window_open = True

if __name__ == '__main__':    
    app = QApplication(sys.argv)    
    win = MenuWindow() 
    win.show() 
    # print('we got here')  
    sys.exit(app.exec())