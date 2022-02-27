# thsi file is for parsing muse csv files
# it opens and reads a file, and returns the data in a convenient format

import csv
import numpy as np


def read_csv_file(fname, outer_channels = False):
    # thsi will read the given file and return a list of lists
    if outer_channels == False:
        # each inner list has 4 values from each of the 4 electrodes
        with open(fname) as csv_file:
            data = []
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count <= 1:
                    line_count += 1
                    continue
                # if line_count >= 20:
                #     break
                # print(row)
                timestep_list = []
                for electrode in row[:4]:
                    # only take first 4 numbers to exclude 0 column and time
                    timestep_list.append(float(electrode))
                data.append(timestep_list)
                line_count += 1
    else:
        with open(fname) as csv_file:
            # outer list has 4 items, one for each channel. Each inner list has n items
            data = [[],[],[],[]]
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count <= 1:
                    line_count += 1
                    continue
                # if line_count >= 20:
                #     break
                # print(row)
                for electrode in range(4):
                    # only take first 4 numbers to exclude 0 column and time
                    data[electrode].append(float(row[electrode]))
                line_count += 1
            for i in range(len(data)):
                data[i] = np.array(data[i])
    return(data)   
        
if __name__ == '__main__':
    data = read_csv_file('Muse_sample_1.csv')
    print('output data:',data)