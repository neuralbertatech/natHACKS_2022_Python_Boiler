# Welcome to the introduction to PyQt5 and EEG data processing! 
# Today, we're going to walk through connecting to hardware, 
# and graphing the raw data in our very own window. 
# We'll also cover a few other GUI elements, like buttons and event handling. 
# Finally, we'll discuss some further ways to process and display EEG data.

# we'll start with eeg connection
from brainflow.data_filter import (
    DataFilter,
    FilterTypes,
    AggOperations,
    WindowFunctions,
    DetrendOperations,
)
import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from Board import Board, get_board_id
from utils.save_to_csv import save_to_csv

# setting up a board object 
# 1 for ganglion, 22 for muse 2
board_id = 22

board = Board(board_id = board_id)


data = board.get_data_quantity(10)
file_name = 'skelton_csv.csv'
exg_channels = board.get_exg_channels()

# let's display the channels we actually got data from
print(exg_channels)

# And now let's see the data
print(data)
save_to_csv(data,file_name,exg_channels)

