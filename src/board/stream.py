from threading import Thread, Lock
import time
import serial

def string_to_float(x):
    if x == "" or x == '' or x == None:
        return 0.0
    else:
        return float(x)

class Stream(Thread):
    def __init__(self, com_port: str, number_of_channels: int, sample_rate: int, baud_rate: int, buffer_size: int):
        Thread.__init__(self)
        self.buffer_size = buffer_size
        self.ns_per_sample =  1 / (sample_rate*2) * 1000000000
        self.serial_connection = serial.Serial(com_port, baud_rate)
        self.ring_buffer = [[0 for i in range(number_of_channels)] for j in range(buffer_size)]
        self.buffer_lock = Lock()
        self.buffer_current_index = 0;
        self.buffer_last_read_index = 0;

    def run(self):
        self.thread_running = True
        while self.thread_running:
            start = time.time_ns()
            sample = self.serial_connection.readline().decode("utf-8")
            if sample != "":
                split_sample = [string_to_float(x) for x in sample.split(',')]

                self.buffer_lock.acquire()
                self.ring_buffer[self.buffer_current_index] = split_sample
                self.buffer_current_index = (self.buffer_current_index + 1) % self.buffer_size
                if self.buffer_current_index == self.buffer_last_read_index:
                    self.buffer_last_read_index = (self.buffer_last_read_index + 1) % self.buffer_size
                self.buffer_lock.release()

            time_diff = time.time_ns() - start
            if time_diff < self.ns_per_sample:
                time.sleep((self.ns_per_sample - time_diff) / 1000000000)



    def pop_data(self):
        ret_data = []

        self.buffer_lock.acquire()
        if self.buffer_last_read_index > self.buffer_current_index:
            ret_data = self.ring_buffer[self.buffer_current_index:] + self.ring_buffer[:self.buffer_last_read_index]
        else:
            ret_data = self.ring_buffer[self.buffer_last_read_index:self.buffer_current_index]
        self.buffer_last_read_index = self.buffer_current_index
        self.buffer_lock.release()

        return ret_data

    def fetch_data(self, number_of_samples: int):
        ret_data = []

        self.buffer_lock.acquire()
        if number_of_samples > self.buffer_current_index:
            ret_data = self.ring_buffer[self.buffer_current_index - number_of_samples:] + self.ring_buffer[:self.buffer_current_index]
        else:
            ret_data = self.ring_buffer[self.buffer_current_index - number_of_samples:self.buffer_current_index]
        self.buffer_lock.release()

        return ret_data

    def stop(self):
        self.thread_running = False

