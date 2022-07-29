from src.board.board import Board
from src.board.stream import Stream
import numpy as np

class ExgPill:
    def __init__(self, com_port: str, number_of_channels: int = 5):
        self.com_port = com_port
        self.sampling_rate = 125
        self.number_of_channels = np.array(number_of_channels)
        self.exg_channels = np.array([x+1 for x in range(self.number_of_channels)])
        self.description = "UpsideDown Labs EXG Pill"
        self.stream = Stream(
                com_port=com_port,
                number_of_channels=5,
                sample_rate=self.sampling_rate,
                baud_rate=115200,
                buffer_size=16384
        )
        self.stream.start()

    def _transpose_data(self, data):
        try:
            size = len(data)
            transposed_data = [
                [sample[0]/1000 for sample in data],
                [sample[1]/1000 for sample in data],
                [sample[2]/1000 for sample in data],
                [sample[3]/1000 for sample in data],
                [sample[4]/1000 for sample in data]
            ]
            new_data = np.array([
                [x for x in range(0, size)],
                transposed_data[0],
                transposed_data[1],
                transposed_data[2],
                transposed_data[3],
                transposed_data[4],
                [0 for i in range(size)]
            ])
        except Exception:
            return np.array([[np.zeros(len(data))] for x in range(self.number_of_channels)])

        return new_data

    def get_new_data(self):
        """
        Check how much data has been added to the ringbuffer since last call (to this function) and grab that much data
        """
        return self._transpose_data(self.stream.pop_data())


    def get_data_quantity(self, number_of_points: int):
        """
        Get only a specified amount of most recent board data.
        """
        return self._transpose_data(self.stream.fetch_data(number_of_points))

    def stop(self):
        self.stream.stop()

    def get_exg_channels(self):
        return self.exg_channels

    def get_marker_channels(self):
        return self.number_of_channels

    def get_sampling_rate(self):
        return self.sampling_rate

    def get_board_description(self):
        return self.description
