from brainflow.board_shim import BoardShim, BrainFlowInputParams
import brainflow
import numpy as np

# Actions
FILE = "File"
SIMULATE = "Simulate"
CONNECT = "Connect"

# Hardware types
MUSE = "Muse"
BCI = "OpenBCI"

# Model types
GANGLION = "Ganglion"
CYTON = "Cyton"
CYTON_DAISY = "Cytom-Daisy"
MUSE_2 = "Muse 2"
MUSE_S = "Muse S"

class Board:
    def __init__(self, data_type="", hardware="", model="", board_id=None, debug=False):
        if debug == True:
            BoardShim.enable_dev_board_logger()
            serial_port = "COM1"

        # Brainflow Init
        self.params = BrainFlowInputParams()
        self.hardware = hardware
        self.model = model

        # set baord id based on parameters only if it wasn't given to us
        if board_id == None:
            if data_type == CONNECT:
                if hardware == BCI:
                    if model == GANGLION:
                        self.board_id = 1
                    elif model == CYTON:
                        self.board_id = 0
                    elif model == CYTON_DAISY:
                        self.board_id = 2
                elif hardware == MUSE:
                    if model == MUSE_2:
                        self.board_id = 22
                    elif model == MUSE_S:
                        self.board_id = 21
            elif data_type == SIMULATE:
                self.board_id = -1
        else:
            self.board_id = board_id

        for i in range(10):
            self.params.serial_port = "COM" + str(i)
            self.board = BoardShim(self.board_id, self.params)
            try:
                self.board.prepare_session()
            except brainflow.board_shim.BrainFlowError:
                pass
            else:
                # didn't have the bad com port exeption
                break

        print(
            "init hardware is running with hardware", self.hardware, "model", self.model
        )
        self.board.start_stream()

        exg_channels = BoardShim.get_exg_channels(self.board_id)
        sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        window_size = 4
        self.num_points = window_size * sampling_rate

        self.chan_num = len(exg_channels)
        self.exg_channels = np.array(exg_channels)



    def get_new_data(self):
        return self.board.get_current_board_data(self.num_points)