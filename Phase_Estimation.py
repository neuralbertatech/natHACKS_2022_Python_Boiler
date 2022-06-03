# -*- coding: utf-8 -*-
"""
Created on Thu Dec 23 16:01:09 2021

@author: eredm
"""

# C:\Users\eredm\Documents\GitHub\Open_Stroke_Rehab\GUI


import numpy as np
from brainflow.data_filter import (
    DataFilter,
    FilterTypes,
    AggOperations,
    WindowFunctions,
    DetrendOperations,
)
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, freqz, hilbert, chirp
import pandas as pd
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.ar_model import AutoReg

# from scipy import signal

in_file = "eeg_log_file_1639676920.csv"

# print("restored data head: \n {} \nrestored_data.shape{}".format(restored_data, restored_data.shape))

sampling_rate = BoardShim.get_sampling_rate(0)
print("sampling rate: {}".format(sampling_rate))

win_length = sampling_rate / 2

intra_epoch_num = 5

intra_epoch_ind = np.zeros((intra_epoch_num, 2), dtype=int)

for cur_intra in range(intra_epoch_num):
    low_bound = (
        int(sampling_rate / intra_epoch_num) * cur_intra
    ) - sampling_rate / intra_epoch_num
    high_bound = int(sampling_rate / intra_epoch_num) * cur_intra
    intra_epoch_ind[cur_intra][0] = low_bound
    intra_epoch_ind[cur_intra][1] = high_bound

bands = {
    # 'theta' : (4.0, 7.0),
    # 'low_alpha' : (8.0, 10.0),
    # 'high_alpha' : (10.0, 13.0),
    "alpha": (7.0, 13.0),
    "low_beta": (13.0, 20.0),
    "high_beta": (20.0, 30.0),
}

# nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
# print(nfft)
nfft = 32

chan_num = 16
drop_col = [0, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
col_names = [
    "chan_1",
    "chan_2",
    "chan_3",
    "chan_4",
    "chan_5",
    "chan_6",
    "chan_7",
    "chan_8",
    "chan_9",
    "chan_10",
    "chan_11",
    "chan_12",
    "chan_13",
    "chan_14",
    "chan_15",
    "chan_16",
    "trig",
]

butter_cutoff = 50
butter_order = 6
bandpass_center = 10
bandpass_width = 4

targ_elec = 5
ref_elec = [6, 7, 8, 9]

desired_phase = 0
technical_delay = 8
delay_tolerance = 5

########################################


data = DataFilter.read_file(in_file)

for chan in range(chan_num):
    DataFilter.perform_lowpass(
        data[chan],
        sampling_rate,
        butter_cutoff,
        butter_order,
        FilterTypes.BUTTERWORTH.value,
        0,
    )

df = pd.DataFrame(np.transpose(data))

df.drop(df.columns[drop_col], axis=1, inplace=True)
df.columns = col_names

targ_trigs = df[(df["trig"] == 1) | (df["trig"] == 2)].index

X = []
y = []

temp_targ = []
temp_chan = []
temp_intra_epoch = []
temp_bands = []

for targ in range(len(targ_trigs)):
    for chan in range(chan_num):
        """
        still need to add in within epoch baseline subtraction
        """
        for intra_epoch in range(intra_epoch_num):  # range(len(intra_epoch_ind)
            # print(len(restored_data[chan][targ_trigs[targ] + intra_epoch_ind[intra_epoch][0]:targ_trigs[targ] + intra_epoch_ind[intra_epoch][1]]))
            targ_win_low = targ_trigs[targ] + intra_epoch_ind[intra_epoch][0]
            targ_win_high = targ_trigs[targ] + intra_epoch_ind[intra_epoch][1]
            psd = DataFilter.get_psd_welch(
                df.iloc[targ_win_low:targ_win_high, chan].to_numpy(),
                nfft,
                nfft // 2,
                sampling_rate,
                WindowFunctions.BLACKMAN_HARRIS.value,
            )
            for (
                band
            ) in (
                bands
            ):  # iteration through the target bands and grab the average over the time bucket
                temp_chan_spec_buc = DataFilter.get_band_power(
                    psd, bands[band][0], bands[band][1]
                )  # temporary channel spectral bucket
                temp_bands.append(temp_chan_spec_buc)
            temp_intra_epoch.append(temp_bands)
            temp_bands = []
            temp_chan.append(temp_intra_epoch)
            temp_intra_epoch = []
        temp_targ.append(temp_chan)
        temp_chan = []
    temp_targ = np.array(temp_targ)
    temp_targ = np.squeeze(temp_targ, axis=2)

    """
    Outputs here as:

    16 channels
    5 intra epoch buckets
    3 bandwidths

    """
    X.append(temp_targ)
    y.append(df.iloc[targ_trigs[targ]]["trig"])
    print(df.iloc[targ_trigs[targ]]["trig"])
    temp_targ = []
y = np.array(y)
X = np.array(X)

### Hjorth
df["Hjorth"] = df.iloc[:, targ_elec] - df.iloc[:, ref_elec].mean(axis=1)
Hjorth = df["Hjorth"].to_numpy()

DataFilter.perform_bandpass(
    Hjorth,
    sampling_rate,
    bandpass_center,
    bandpass_width,
    butter_order,
    FilterTypes.BUTTERWORTH.value,
    1,
)
phase_target = df["Hjorth"][-101:-1].to_numpy()


#%% Hilber and get amplitude envelope, instantaneous phase/frequency, and average frequency
analytic_signal = hilbert(phase_target)
# inst_phase = np.unwrap(np.angle(analytic_signal))#inst phase
amplitude_envelope = np.abs(analytic_signal)
inst_phase_series = np.angle(analytic_signal, deg=False)

inst_freq_series = np.diff(np.unwrap(inst_phase_series)) / (2.0 * np.pi) * sampling_rate

# take the average frequency of the signal (exculding the very beginning and very end)
avg_inst_freq = np.mean(
    inst_freq_series[
        int(len(inst_freq_series) * 0.2) : -np.int(len(inst_freq_series) * 0.2)
    ]
)
print(avg_inst_freq)

x = np.arange(0, len(phase_target)) * (1 / 250)

#%%
### Plot
plt.figure(1)
plt.plot(x, phase_target)
plt.plot(x, amplitude_envelope)
plt.plot(x, inst_phase_series)
plt.plot(x, np.tile(avg_inst_freq, len(phase_target)))
plt.plot(x[:-1], inst_freq_series)
# plt.plot(x,phase_target)

# ax = plt.gca()
# ax.set_xlim([xmin, xmax])
# ax.set_ylim([-5, 30])

# # gives radians
# phase = (2*np.pi*avg_inst_freq*(win_length-1)/sampling_rate+inst_phase) % (2*np.pi) #% Current sample phase
# print(phase)
# # convert to degrees
# phase = (phase + np.pi) % (2 * np.pi) - np.pi
# print(phase)

#%% Pure phase prediction - simple
"""
This just get the last instantaneous phase and based on
frequency and time estimates the next cycle
"""
# desired_phase = 2*np.pi
# desired_phase = np.pi/2
desired_phase = 0
time_past = 12  # number of milliseconds passed
technical_delay = 8  # time it takes to trigger the FEN from sending signal
delay_tolerance = 5  # milliseconds allows offset from optimal stimulation

# phase varies from -pi to pi (-3.14 to 3.14)

# Pure phase prediction
phase_diff = (
    2 * np.pi - np.abs(desired_phase - inst_phase_series[-1]) - np.pi / 2
)  # phase goes from 0 at 2pi and goes down to
samples_per_cycle = sampling_rate / avg_inst_freq  # number of sampling points per cycle
full_cycle = 2 * np.pi

phaseshift_per_sample = full_cycle / samples_per_cycle

samples_required = phase_diff / phaseshift_per_sample
base_wait_time_s = samples_required * 1 / 250
base_wait_time_ms = base_wait_time_s * 1000

# check to make sure this isn't a phase reset artifact
if inst_phase_series[-2] - inst_phase_series[-1] > phaseshift_per_sample * 2:
    print("phase turnover")

wait_time = base_wait_time_ms - technical_delay - time_past

start = x[-1]
# x = np.arange(0,len(phase_target)+np.ceil(samples_required))*(1/250)
full_wait_x = np.arange(0, np.ceil(samples_required)) * (1 / 250) + start
full_wait_y = np.tile(-4.0, int(np.ceil(samples_required)))

time_past_x = full_wait_x[0:3]
time_past_y = np.tile(-3.0, len(time_past_x))

wait_time_x = full_wait_x[int(len(time_past_x)) : -int(len(tech_delay_x)) - 1]
wait_time_y = np.tile(-2.0, len(wait_time_x))

tech_delay_x = full_wait_x[-3:-1]
tech_delay_y = np.tile(-1.0, len(tech_delay_x))


#%%
# full_wait_x = np.asarray(full_wait_x,dtype=int)

# time_past_length =
plt.figure(2)
plt.plot(full_wait_x, full_wait_y)
plt.plot(time_past_x, time_past_y)
plt.plot(wait_time_x, wait_time_y)
plt.plot(tech_delay_x, tech_delay_y)
plt.plot(x, phase_target)
plt.plot(x, inst_phase_series)

plt.figure(3)
plt.plot(full_wait_x, full_wait_y, linewidth=3, label="zero phase pred")
plt.plot(time_past_x, time_past_y, linewidth=3, label="compute time")
plt.plot(wait_time_x, wait_time_y, linewidth=3, label="idle time")
plt.plot(tech_delay_x, tech_delay_y, linewidth=3, label="technical delay")
plt.plot(
    x[int(len(phase_target) / 2) : -1],
    phase_target[int(len(phase_target) / 2) : -1],
    linewidth=2,
    label="alpha carrier",
)
plt.plot(
    x[int(len(inst_phase_series) / 2) : -1],
    inst_phase_series[int(len(inst_phase_series) / 2) : -1],
    linewidth=2,
    label="phase series",
)
plt.plot(x[int(len(phase_target) / 2) : -1], np.tile(0, int(len(phase_target) / 2 - 1)))

# plt.plot(x,phase_target, label="alpha carrier")
# plt.plot(x,inst_phase_series, label="phase series")
# plt.plot(x,np.tile(0,int(len(x))))
# plt.legend(loc="upper right")
# plt.legend(loc="upper left")

legend = plt.legend(loc="upper left", edgecolor="black", prop={"size": 8})
legend.get_frame().set_alpha(None)

# shift over phase plot for easier visualization


plt.figure(4)
plt.plot(full_wait_x, full_wait_y, linewidth=3, label="zero phase pred")
plt.plot(time_past_x, time_past_y, linewidth=3, label="compute time")
plt.plot(wait_time_x, wait_time_y, linewidth=3, label="idle time")
plt.plot(tech_delay_x, tech_delay_y, linewidth=3, label="technical delay")
plt.plot(
    x[int(len(phase_target) / 2) : -1],
    phase_target[int(len(phase_target) / 2) : -1],
    linewidth=2,
    label="alpha carrier",
)
plt.plot(
    x[int(len(inst_phase_series) / 2 + len(full_wait_x)) : -1],
    inst_phase_series[int(len(inst_phase_series) / 2 + len(full_wait_x)) : -1],
    linewidth=2,
    label="phase series",
)
plt.plot(moded_phase_x, np.tile(0, len(moded_phase_x)))

plt.axvline(x=x[-1], linestyle="dashed")
plt.axvline(x=full_wait_x[-1], linestyle="dotted")
plt.axhline(y=-np.pi / 2, linestyle="dotted")
ax = plt.gca()
ax.set_ylim([-6, 7])

legend = plt.legend(loc="upper left", ncol=2, edgecolor="black", prop={"size": 8})
legend.get_frame().set_alpha(None)

#%% Putting it all together

### Ground truth autoregression prediction and comparison
phase_len = len(phase_target)
predict_len = int(phase_len / 2)
predict_x = np.linspace(phase_len, phase_len + predict_len, predict_len)

# Create training and test data
train_data = phase_target[: len(phase_target) - predict_len]
test_data = phase_target[len(phase_target) - predict_len :]

# Instantiate and fit the AR model with training data
ar_model = AutoReg(train_data, lags=5).fit()

# Print Summary
# print(ar_model.summary())

# Make the predictions
pred_groud_truth_y = ar_model.predict(
    start=len(train_data), end=phase_len, dynamic=False
)
pred_ground_truth_x = np.arange(0, np.ceil(predict_len) + 1) * (1 / 250) + x[50]


### Novel autoregression prediction
train_data = phase_target

predict_len = np.ceil(samples_required) * 2

# Instantiate and fit the AR model with training data
ar_model = AutoReg(train_data, lags=5).fit()

# Print Summary
# print(ar_model.summary())

# Make the predictions
pred_new_y = ar_model.predict(
    start=len(train_data), end=int(len(train_data) - 1 + predict_len), dynamic=False
)
pred_new_x = np.arange(0, np.ceil(predict_len)) * (1 / 250) + pred_ground_truth_x[-1]


plt.figure(5)
plt.plot(full_wait_x, full_wait_y, linewidth=3, label="zero phase pred")
plt.plot(time_past_x, time_past_y, linewidth=3, label="compute time")
plt.plot(wait_time_x, wait_time_y, linewidth=3, label="idle time")
plt.plot(tech_delay_x, tech_delay_y, linewidth=3, label="technical delay")
plt.plot(
    x[int(len(phase_target) / 2) : -1],
    phase_target[int(len(phase_target) / 2) : -1],
    linewidth=2,
    label="alpha carrier",
)
plt.plot(
    x[int(len(inst_phase_series) / 2) : -1],
    inst_phase_series[int(len(inst_phase_series) / 2) : -1],
    linewidth=2,
    label="phase series",
)
plt.plot(moded_phase_x, np.tile(0, len(moded_phase_x)))

### NEW (Predictions)
plt.plot(pred_ground_truth_x, pred_groud_truth_y)
plt.plot(pred_new_x, pred_new_y)

plt.axvline(x=x[-1], linestyle="dashed")
plt.axvline(x=full_wait_x[-1], linestyle="dotted")
plt.axhline(y=-np.pi / 2, linestyle="dotted")
ax = plt.gca()
ax.set_ylim([-6, 7])

legend = plt.legend(loc="upper left", ncol=2, edgecolor="black", prop={"size": 8})
legend.get_frame().set_alpha(None)

#%% Appending the novel prediction with the pre-existing trace

hybrid_signal_x = np.append(x[int(len(phase_target) / 2) : -1], pred_new_x)
hybrid_signal_y = np.append(phase_target[int(len(phase_target) / 2) : -1], pred_new_y)


plt.figure(5)
plt.plot(full_wait_x, full_wait_y, linewidth=3, label="zero phase pred")
plt.plot(time_past_x, time_past_y, linewidth=3, label="compute time")
plt.plot(wait_time_x, wait_time_y, linewidth=3, label="idle time")
plt.plot(tech_delay_x, tech_delay_y, linewidth=3, label="technical delay")
# plt.plot(x[int(len(phase_target)/2):-1],phase_target[int(len(phase_target)/2):-1],linewidth=2, label="alpha carrier")
# plt.plot(x[int(len(inst_phase_series)/2):-1],inst_phase_series[int(len(inst_phase_series)/2):-1],linewidth=2, label="phase series")
plt.plot(moded_phase_x, np.tile(0, len(moded_phase_x)))

### NEW (Hybrid signal)
plt.plot(hybrid_signal_x, hybrid_signal_y)

plt.axvline(x=x[-1], linestyle="dashed")
plt.axvline(x=full_wait_x[-1], linestyle="dotted")
plt.axhline(y=-np.pi / 2, linestyle="dotted")
ax = plt.gca()
ax.set_ylim([-6, 7])

legend = plt.legend(loc="upper left", ncol=2, edgecolor="black", prop={"size": 8})
legend.get_frame().set_alpha(None)


#%% Move over prediction to match the autoregression intersect of phase 0
# Start from just the autoregression and find the

# use interpolate from
# validate with a really zoomed in plot of just the dotted horizontal and the the hybrid signal

# try moving over the stim delivered time to match the autoregression prediction
# plot the delay_tolerance margin as a low alpha yellow rectangle - centered on stim delivered time


#%% Stationarity Test #2

from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# Draw Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=80)
plot_acf(inst_phase_series, ax=ax1, lags=50)
plot_pacf(inst_phase_series, ax=ax2, lags=20)

# Decorate
# lighten the borders
ax1.spines["top"].set_alpha(0.3)
ax2.spines["top"].set_alpha(0.3)
ax1.spines["bottom"].set_alpha(0.3)
ax2.spines["bottom"].set_alpha(0.3)
ax1.spines["right"].set_alpha(0.3)
ax2.spines["right"].set_alpha(0.3)
ax1.spines["left"].set_alpha(0.3)
ax2.spines["left"].set_alpha(0.3)

# font size of tick labels
ax1.tick_params(axis="both", labelsize=12)
ax2.tick_params(axis="both", labelsize=12)
plt.show()

#%% Prediction with test (compare ground truth)

# https://vitalflux.com/autoregressive-ar-models-with-python-examples/

phase_len = len(phase_target)

predict_len = int(phase_len / 2)
predict_x = np.linspace(phase_len, phase_len + predict_len, predict_len)

# Create training and test data
train_data = phase_target[: len(phase_target) - predict_len]
test_data = phase_target[len(phase_target) - predict_len :]

# Instantiate and fit the AR model with training data
ar_model = AutoReg(train_data, lags=5).fit()

# Print Summary
print(ar_model.summary())

# Make the predictions
pred_groud_truth_y = ar_model.predict(
    start=len(train_data), end=phase_len, dynamic=False
)

# Plot the prediction vs test data
print(len(pred))

# train_x = np.arange(0,phase_len/2+1)*(1/250)

pred_ground_truth_x = np.arange(0, np.ceil(predict_len) + 1) * (1 / 250) + x[50]
print(len(x_pred))
# full_wait_y = np.tile(-4.0,int(np.ceil(samples_required)))


plt.figure(5)
plt.plot(x, phase_target)
plt.plot(pred_ground_truth_x, pred_groud_truth_y)


#%% Predication of instantaneous phase
"""
phase_len = len(inst_phase_series)

predict_len = int(len(inst_phase_series)/2)
predict_x = np.linspace(inst_phase_series, inst_phase_series + predict_len, predict_len)

#
# Create training and test data
#
train_data = inst_phase_series[:len(inst_phase_series)-predict_len]
test_data = inst_phase_series[len(inst_phase_series)-predict_len:]
#
# Instantiate and fit the AR model with training data
#
ar_model = AutoReg(train_data, lags=15).fit()
#
# Print Summary
#
print(ar_model.summary())

# Make the predictions
#
pred = ar_model.predict(start=len(train_data), end=phase_len, dynamic=False)
#
# Plot the prediction vs test data
#
print(len(pred))

# train_data = np.append(train_data)


plt.figure(5)
plt.plot(pred)
plt.plot(train_data)
plt.plot(test_data, color='red')
"""

#%% Prediction without test - new data

train_data = phase_target

# Instantiate and fit the AR model with training data
ar_model = AutoReg(train_data, lags=5).fit()

# Make the predictions
pred_new_y = ar_model.predict(
    start=len(train_data) + 1, end=len(train_data) + predict_len, dynamic=False
)

pred_new_x = np.arange(0, np.ceil(predict_len)) * (1 / 250) + pred_ground_truth_x[-1]


plt.figure(6)
plt.plot(x, phase_target)
plt.plot(pred_ground_truth_x, pred_groud_truth_y)
plt.plot(pred_new_x, pred_new_y)


#%% Just looking at instantaneous frequency

"""
desired_phase = 0

Xf = fft(chunk_filt,4096);
[~,idx] = max(abs(Xf));
f_est = (idx-1)*fs/length(Xf); % Estimated frequecy
phase_est = angle(Xf(idx)); % Estimated phase at the beggining of winddow
phase = mod(2*pi*f_est*(win_length-1)/fs+phase_est,2*pi); % Current sample phase
phase = wrapToPi(phase);

# also need instantaneous frequency

if abs((desired_phase-phase)*fs/f_est/2/pi-technical_delay) <= delay_tolerance
    outp(address, 32);
    trig_timer = tic; % Reset timer after each trigger
    pause(0.015);
    outp(address, 0);
    allTs_trigger = [allTs_trigger ts];
    disp('Stim');
"""
