# this is a function to save data (as gotten from brainflow)
# to a csv
import numpy as np

def save_to_csv(data,csv_name,channels = None, logger=None):
    '''
    Saved the given data to a csv
    data should be of the sort brainflow outputs, from a call to the board. ( numpy array)
    csv_name should be text, the name of the file to save to
    channels is optional, and is indexes of channels to save of the brainflow data (meant to be the output 
    of Boardshim.get_exg_channels or something similar). If not provided, this function will save every channel.
    logger is a python logger to send log messages to (if not provided, no logging will be done)
    '''

    with open(csv_name, "a") as csvfile:
            if channels is None:
                data_to_save = data[:, :].T
            else:
                data_to_save = data[channels, :].T
            if logger != None:
                logger.debug("data size {}".format(data_to_save.shape))
                logger.debug(data_to_save)
            np.savetxt(csvfile, data_to_save, delimiter=",")
