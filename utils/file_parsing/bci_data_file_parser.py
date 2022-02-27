        
if __name__ == '__main__':
    eeg_data = EEG_file_data('test_eeg_data_file.raw')
    real_data = EEG_file_data('qB2OmVrndrRITz1QFkjfnRlqnJl1 (13).raw')



class EEG_file_data():
    '''
    an object containing all the data from the file name passed to it
    very nested
    contains:
    - a list of trials ('trials')
    Each trial contains:
    - the header (a string, 'header')s
    - a list of samples ('samples')
    Each sample contains:
    - the trigger (string, 'trigger')
    - the time (int, 'time')
    - eeg data point list ( 16 ints, one from each electrode. 'eeg_list')

    also has a list of lists containing just the eeg data ('eeg_data')
    - outer list has 16 lists, one for each electrode
    - each inner list has a point for each timestamp


    '''
    def __init__(self, fname):
        f = open(fname,'r')
        content = f.read()
        f.close()
        self.mode = 'start'
        self.trials = []

        for letter in content:
            # print(letter)
            if self.mode == 'start':
                if letter == '[':
                    self.mode = 'reading trials'
                else:
                    print('error unexpected character while ' + self.mode + ': '+letter)
            elif self.mode == 'reading trials':
                if letter == '[':
                    # print('switching to content from general trials')
                    self.mode = 'reading trial content'
                    self.trial = Trial()
                elif letter == ',':
                    pass
                elif letter == ']':
                    self.mode = 'end'
                    print('done')
                else:
                    print('error unexpected character while ' + self.mode + ': '+letter)
            elif self.mode == 'reading trial content':
                if letter == '"':
                    self.mode = 'reading header string'
                    # print('switching to header string mode')
                elif letter == ',':
                    self.mode = 'reading trial sample'
                elif letter == ']':
                    self.trials.append(self.trial)
                    self.mode = 'reading trials'
                else:
                    print('error unexpected character while ' + self.mode + ': '+letter)
            elif self.mode == 'reading header string':
                if letter == '"':
                    # print('from string switching to header content')
                    self.mode = 'reading trial content'
                else:
                    self.trial.add_header(letter)
            elif self.mode == 'reading trial sample':
                if letter == '[':
                    self.sample = Sample()
                    self.mode = 'reading sample trigger'
                elif letter == ']':
                    self.trial.add_sample(self.sample)
                    self.mode = 'reading trial content'
                else:
                    print('error unexpected character while ' + self.mode + ': '+letter)
            elif self.mode == 'reading sample trigger':
                if letter == ',':
                    self.mode = 'reading sample eeg'
                else:
                    self.sample.add_trigger(letter)
            elif self.mode == 'reading sample eeg':
                if letter == '[':
                    self.mode = 'reading eeg time'
                    self.time = ''
                else:
                    print('error unexpected character while ' + self.mode + ': '+letter)
            elif self.mode == 'reading eeg time':
                if letter == ',':
                    self.mode = 'reading eeg data point'
                    self.data_point = ''
                    self.sample.set_time(int(self.time))
                else:
                    self.time += letter
            elif self.mode == 'reading eeg data point':
                if letter == ',':
                    self.sample.add_eeg_point(int(self.data_point))
                    self.data_point = ''
                elif letter == ']':
                    self.sample.add_eeg_point(int(self.data_point))
                    self.data_point = ''
                    self.mode = 'reading trial sample'
                else:
                    self.data_point += letter
        self.eeg_data = []
        for i in range(16):
            electrode = []
            for trial in self.trials:
                for sample in trial.samples:
                    electrode.append(sample.eeg_list[i])
            self.eeg_data.append(electrode)
        
        
            
                

                

                    
class Trial():
    def __init__(self):
        self.header = ''
        self.samples = []
    def add_header(self, letter):
        self.header += letter
    def add_sample(self, sample):
        self.samples.append(sample)        

class Sample():
    def __init__(self):
        self.trigger = ''
        self.time = 0
        self.eeg_list = []
    def add_trigger(self, letter):
        self.trigger += letter
    def set_time(self, time):
        self.time = time
    def add_eeg_point(self, data_point):
        self.eeg_list.append(data_point)
