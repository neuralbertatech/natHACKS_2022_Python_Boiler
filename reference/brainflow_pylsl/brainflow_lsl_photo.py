import time
from queue import Queue
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from pylsl import StreamInfo, StreamOutlet, local_clock

def Brainflow_LSL(main_q):
    debug = False

    params = BrainFlowInputParams()
    params.serial_port = "COM3"

    if debug:
        BoardShim.enable_dev_board_logger()
    else:
        BoardShim.disable_board_logger()

    # Grab cyton-daisy board object
    board = BoardShim(BoardIds.CYTON_DAISY_BOARD.value, params)
    board.prepare_session()

    # Think Pulse
    # board.config_board("x1040010Xx2040010Xx3040010Xx4040010Xx5040010Xx6040010Xx7040010Xx8040010XxQ040010XxW040010XxE040010XxR040010XxT040010XxY040010XxU040010XxI040010X")

    # Reinitialize the 15/16 channel for EOG
    print("Reinitialize the 15/16 channel for EOG")
    res = board.config_board("xU040100XxI040100X")
    print("res for eog init: {}".format(res))

    # Start analog mode to grab all the analog channels
    print("Start analog mode to grab all the analog channels")
    res = board.config_board('/2')  # only if you want to get analog pin values instead of accelerometer
    print("res for analog init: {}".format(res))

    start_time = time.time()

    # LSL initialization  
    channel_names = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,28] # D12

    n_channels = len(channel_names)
    srate = 125
    info = StreamInfo('OpenBCI', 'EXG', n_channels, srate, 'double64', 'OpenBCI_EEG_123')
    outlet = StreamOutlet(info)
    fw_delay = 0

    # start stream
    board.start_stream(45000)
    time.sleep(1)
    start_time = local_clock()
    sent_samples = 0
    queue = Queue(maxsize = 5*srate)
    worker_thread = True

    # read data with brainflow and send it via LSL
    print("Now sending data...")
    while worker_thread:
        data = board.get_board_data()[channel_names]
        for i in range(len(data[0])):
            queue.put(data[:,i].tolist())
        elapsed_time = local_clock() - start_time
        required_samples = int(srate * elapsed_time) - sent_samples
        if required_samples > 0 and queue.qsize() >= required_samples:    
            mychunk = []
            for i in range(required_samples):
                mychunk.append(queue.get())
            stamp = local_clock() - fw_delay 
            outlet.push_chunk(mychunk, stamp)
            sent_samples += required_samples
        time.sleep(1)

