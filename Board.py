from brainflow.board_shim import BoardShim, BrainFlowInputParams
import brainflow
import numpy as np

# Actions
SIMULATE = "Task simulate"
CONNECT = "Task live"

# Hardware types
MUSE = "Muse"
BCI = "OpenBCI"

# Model types
GANGLION = "Ganglion"
CYTON = "Cyton"
CYTON_DAISY = "Cyton-Daisy"
MUSE_2 = "Muse 2"
MUSE_S = "Muse S"


class Board:
    def __init__(self, data_type="", hardware="", model="", board_id=None, debug=False, num_points=None):
        if debug == True:
            BoardShim.enable_dev_board_logger()
            serial_port = "COM1"

        # Brainflow Init
        self.params = BrainFlowInputParams()
        self.hardware = hardware
        self.model = model
        if num_points == None:
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
            window_size = 4
            self.num_points = window_size * self.sampling_rate
        else:
            self.num_points = num_points

        # set board id based on parameters only if it wasn't given to us
        self.board_id = board_id
        if self.board_id is None:
            self.board_id = get_board_id(data_type, hardware, model)
        assert self.board_id is not None, "Error: Undefined combination of arguments passed to 'get_board_id'"

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

        self.chan_num = len(exg_channels)
        self.exg_channels = np.array(exg_channels)

        self.last_board_data_count = 0

    def get_new_data(self):
        '''
        check how much data has been addedto the ringbuffer since last call (to this function) and grab that much data
        '''
        new_board_data_count = self.board.get_board_data_count()
        count_diff = new_board_data_count-self.last_board_data_count
        self.last_board_data_count = new_board_data_count
        return self.board.get_current_board_data(count_diff)
    
    def get_data_quantity(self,num_points=None):
        '''
        Get only a specified amount of most recent board data
        If num_points is not specified, will use the num_points given on init.
        If not specified on init, will produced error.
        '''
        if num_points == None:
            if self.num_points == None:
                raise Exception('Data quantity unspecfied. Please specify as an argument or when creating the board.')
            else:
                num_points = self.num_points
        return self.board.get_current_board_data(num_points)

    def stop(self):
        self.board.stop_stream()
        self.board.release_session()


def get_board_id(data_type, hardware, model):
    """Gets the brainflow board_id from the given arguments

    Args:
        data_type (String): A string of either "Task live" or "Task simulate"
        hardware (String): A string of either "Muse" or "OpenBCI"
        model (String): A string of either "Muse 2", "Muse S", "Ganglion", "Cyton", or "Cyton-Daisy"

    Returns:
        int: The board_id that brainflow uses internally to determine board type
    """
    board_id = None
    if data_type == CONNECT:
        if hardware == BCI:
            if model == GANGLION:
                board_id = 1
            elif model == CYTON:
                board_id = 0
            elif model == CYTON_DAISY:
                board_id = 2
        elif hardware == MUSE:
            if model == MUSE_2:
                board_id = 22
            elif model == MUSE_S:
                board_id = 21
    elif data_type == SIMULATE:
        board_id = -1

    return board_id
