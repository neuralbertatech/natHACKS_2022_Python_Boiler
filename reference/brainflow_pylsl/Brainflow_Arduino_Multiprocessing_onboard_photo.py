'''
Authored by Eden Redman May 2021
For the use of validating Koalacademy (NeurAlbertaTech)

To-do: 

* Long duration recording - see if there is a compounding trail - check if samples + sampling rate are as expected
* Try stoping the threads first and seeing if we still have stuff in the lsl inlet to pull out. 
    * If so we can get around by just leaving some flushing time - if it doesn't effect marker placement
    * see if passing an arbitary value to the arduino inlet solves sampling rate issues
* When starting the LSL stream grabs from main script - make sure we are caught up - not just taking the top queue item
    * Flush both exg and marker lsl queues before starting to put to global data store

'''

import sys
import time
import numpy as np
import multiprocessing
import pandas as pd
from pylsl import StreamInlet, resolve_byprop
from pynput import keyboard

from brainflow_lsl_photo import Brainflow_LSL

class experiment():
    def __init__(self):
        # Init bool for clean breaking program on 'end' key press
        self.clean_break = False

        self.queue = multiprocessing.Queue()

        # Data containers
        self.count = 0
        self.samples = 0
        self.data =  np.array(np.zeros(18,dtype=float)) # timestamp (1-16), eeg data (time), colour data (trig)

        self.start_time = 0

        self.debug = False
        # self.debug = True

        # Grab participant and session_number
        if not self.debug:
            self.partnum = input("partnum: ") # enter participant in command prompt
            self.session_num = input("session_num: ")

        ## Define filename for saving
        if self.debug == 0:
            self.filename = "{}_{}.csv".format(self.partnum,self.session_num)
        else:
            self.filename = "save_test.csv"

        # Define main thread parameters and initial wait
        self.init_wait = 4
        self.on_press_wait = 0.02
        self.sesh_len = 150000

        def init_exg():
            y = multiprocessing.Process(target=Brainflow_LSL,args=(self.queue,))
            # y.daemon = True
            y.start()
            return y

        def init_lsl():
            ### Intialize EEG LSL inlets
            print("looking for an EXG stream...")
            eeg_streams = resolve_byprop('type', 'EXG',minimum=1,timeout=10)
            eeg_inlet = StreamInlet(eeg_streams[0])
            print(eeg_inlet.info)
            return eeg_inlet

        def on_press(key):
            # self.clean_break
            print(key)
            if key == keyboard.Key.end:
                print ('end pressed')
                self.clean_break = True
                self.close_program()
            time.sleep(self.on_press_wait)
                # return False

        def init_key_logger():
            listener = keyboard.Listener(on_press=on_press)
            listener.start()
            return listener

        ### Start multiprocess
        print("starting exg")
        self.y = init_exg()
        ### Wait for multiprocess to spin up
        time.sleep(self.init_wait)
        print("waiting in init for exg")

        # Start LSL (main thread side)
        print("starting lsl")
        self.eeg_inlet = init_lsl()
        ### Wait for LSL to spin up
        time.sleep(self.init_wait)
        print("waiting in init for lsl")

        # Start Key logger thread (main thread side)
        print("starting key logger")
        self.listener = init_key_logger()

    def save_data(self):
        self.data = pd.DataFrame(data=self.data) #, columns=column_names)
        self.data.to_csv(self.filename, float_format='%.3f', index=True)
        self.samples = self.data.shape[0]

        sesh_duration = time.time() - self.start_time

        # cur_time = time.time()
        print(self.samples)
        print("time per sample: {}".format(sesh_duration/self.samples))
        print("samples per second: {}".format(self.samples/sesh_duration))
    
    def close_program(self):        
        # Save data 
        print("Saving data to csv")
        self.save_data()
        print("data saved")

        ### Close listener process
        self.listener.stop

        ### Close inlet
        self.eeg_inlet.close_stream()
        time.sleep(self.init_wait)
        print("deleted the inlet")

        # ### close eeg thread
        self.y.terminate()
        time.sleep(0.1) # give it some time!
        print("tried to terminate worker from the main thread")
        self.y.join()

        sys.exit()

    def concat_data(self,joined_list):
        self.data = np.vstack((self.data,np.array(joined_list)))
        self.count += 1

    def get_concat_data(self):
        ("attempting to grab data from inlet")
        exg_sample, exg_timestamp = self.eeg_inlet.pull_sample()
        joined_list = exg_sample + [exg_timestamp]
        self.concat_data(joined_list)

if __name__ == "__main__":
    exp = experiment()
    print("main loop init done")

    ### Start time
    print("starting start timer")
    start_time = time.time()

    exp.start_time = start_time

    while time.time() - start_time <= exp.sesh_len and exp.clean_break != True:
        exp.get_concat_data()
        exp.count += 1
 