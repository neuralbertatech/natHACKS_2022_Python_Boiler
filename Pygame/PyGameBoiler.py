import matplotlib.backends.backend_agg as agg
from DropDown import DropDown
from PlusMinusButton import PlusMinusButton
from Board import FILE, MUSE_2, MUSE_S, SIMULATE, CONNECT, MUSE, BCI, GANGLION, Board
import numpy as np
import pygame as pg
import matplotlib
import time

from Board import CYTON, CYTON_DAISY

matplotlib.use("Agg")
import random
from Sprites import *
import csv
from scipy import fft

MAIN = 0
PLOT1 = 1
PLOT2 = 2

GREEN = (0, 255, 0)
RED = (255, 0, 0)

LEFT_CLICK = 0
RANDOM = 1

SCALE_FACTOR_EEG = (4500000) / 24 / (2**23 - 1)  # uV/count
SCALE_FACTOR_AUX = 0.002 / (2**4)


BACKGROUND_COLOR = (0, 150, 250)


class MuseInterface:
    def __init__(self):
        # Initialize all variables
        self.width, self.height = 600, 500
        self.size = (self.width, self.height)
        self.mode = MAIN
        self.floor = 300
        self.vert_velocity = 0
        self.jumping = False
        self.bullets = pg.sprite.Group()
        self.cacti = pg.sprite.Group()
        self.dino = pg.sprite.Group(Dinosaur(50, self.floor))
        self.data = []
        self.hypnogram_data = []
        self.M_wrapper = None
        self.board = None
        self.game_mode = LEFT_CLICK
        self.stream = None

        self.input_file = None
        self.output_filename = "PyGame_" + str(int(time.time())) + ".csv"
        with open(self.output_filename, mode="a", newline="") as file:
            fwriter = csv.writer(
                file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            fwriter.writerow(['"eeg' + str(i) + '"' for i in range(4)])

        self.outlet_eeg = None
        self.outlet_aux = None

        # Initialize pygame stuff
        pg.init()
        self.screen = pg.display.set_mode(self.size)
        pg.display.set_caption("NATHacks Muse Tool")

        # Create The Backgound
        background = pg.Surface(self.screen.get_size())
        self.background = background.convert()
        self.background.fill((250, 250, 250))

        # defining a font
        self.smallfont = pg.font.SysFont("Corbel", 25)

        self.dropdown_main = DropDown(
            0,
            0,
            100,
            40,
            pg.font.SysFont("Corbel", 18),
            "Select Mode",
            [FILE, SIMULATE, CONNECT],
        )
        self.dropdown_connect_hardware = DropDown(
            125,
            100,
            100,
            40,
            pg.font.SysFont("Corbel", 15),
            "Select Device",
            [MUSE, BCI],
        )
        self.dropdown_connect_model_muse = DropDown(
            375,
            100,
            100,
            40,
            pg.font.SysFont("Corbel", 15),
            "Select Device",
            [MUSE_2, MUSE_S],
        )
        self.dropdown_connect_model_bci = DropDown(
            375,
            100,
            100,
            40,
            pg.font.SysFont("Corbel", 15),
            "Select Device",
            [CYTON, CYTON_DAISY, GANGLION],
        )
        self.dropdown_connect_model_default = DropDown(
            350,
            100,
            150,
            40,
            pg.font.SysFont("Corbel", 15),
            "<- Select Mode First!",
            [],
        )

        self.clock = pg.time.Clock()

        # white color
        self.color = (255, 255, 255)

        # light shade of the button
        self.color_light = (170, 170, 170)

        # dark shade of the button
        self.color_dark = (100, 100, 100)

        # stores the width of the
        # screen into a variable
        self.width = self.screen.get_width()

        # stores the height of the
        # screen into a variable
        self.height = self.screen.get_height()

        # Create hardcoded text objects
        self.exitText = self.smallfont.render("Quit", True, self.color)
        self.plot1Text = self.smallfont.render("Click", True, self.color)
        self.plot2Text = self.smallfont.render("Brain", True, self.color)
        self.openText = self.smallfont.render("Open File", True, self.color)

        # Create widths & heights for different rects, text
        self.exitX, self.exitY, self.exitWidth, self.exitHeight = (
            17 * self.width / 20,
            8 * self.height / 9,
            self.width / 8,
            self.height / 12,
        )
        self.plotWidth, self.plotHeight = self.width / 4, self.height / 8
        self.plot1X, self.plot1Y = 1 * self.width / 7, 5.75 * self.height / 8
        self.plot2X, self.plot2Y = 4.5 * self.width / 7, 5.75 * self.height / 8

        # Create rectangles
        self.exitRect = pg.Rect(self.exitX, self.exitY, self.exitWidth, self.exitHeight)
        self.plot1Rect = pg.Rect(
            self.plot1X, self.plot1Y, self.plotWidth, self.plotHeight
        )
        self.plot2Rect = pg.Rect(
            self.plot2X, self.plot2Y, self.plotWidth, self.plotHeight
        )
        self.openRect = pg.Rect(315, 225, 150, 50)
        self.connectRect = pg.Rect(250, 230, 100, 30)

        # Create miscillaneous pygame objects
        self.inputBox = pg.Rect(255, 165, 295, 50)
        self.deviceInputBox = pg.Rect(270, 175, 150, 40)
        self.inputText = "Input Filename"
        self.deviceText = ""
        self.connectText = self.smallfont.render(CONNECT, True, self.color)
        self.streaming = False
        self.circPos = (self.width / 4, 5 * self.height / 8)
        self.fileInputActive = False
        self.deviceInputActive = False

    # if mouse is hovered on a button it
    # changes to lighter shade
    def drawButton(self, mouse, rect):
        if rect.collidepoint(mouse):
            pg.draw.rect(self.screen, self.color_light, rect)
        else:
            pg.draw.rect(self.screen, self.color_dark, rect)

    # Draws the main screen
    def drawMain(self, mouse):
        # Changes color of streaming circle
        if self.streaming:
            pg.draw.circle(self.screen, GREEN, self.circPos, 20)  #
        else:
            pg.draw.circle(self.screen, RED, self.circPos, 20)  #

        # Draws the buttons that can be clicked on.
        self.drawButton(mouse, self.exitRect)
        self.drawButton(mouse, self.plot1Rect)
        self.drawButton(mouse, self.plot2Rect)

        # Draw dropdown
        self.dropdown_main.draw(self.screen)

        # superimposing the text onto our button
        self.screen.blit(
            self.exitText, self.exitText.get_rect(center=self.exitRect.center)
        )
        self.screen.blit(
            self.plot1Text, self.plot1Text.get_rect(center=self.plot1Rect.center)
        )
        self.screen.blit(
            self.plot2Text, self.plot2Text.get_rect(center=self.plot2Rect.center)
        )
        self.screen.blit(
            self.smallfont.render("Muse PyQt Boiler", True, self.color), (200, 50)
        )
        self.screen.blit(
            self.smallfont.render("<- Click for streaming On/Off", True, self.color),
            (200, 295),
        )

        # Draw different things for the interior dropdown
        if self.dropdown_main.main == FILE:
            self.drawFileDD(mouse)
        elif self.dropdown_main.main == CONNECT:
            self.drawConnectDD(mouse)
        elif self.dropdown_main.main == SIMULATE:
            self.drawSimulateDD(mouse)
        else:
            self.screen.blit(
                self.smallfont.render(
                    "Please select an option from the dropdown.", True, self.color
                ),
                (100, 150),
            )

    # Draw the dropdown skin for selecting an output file
    def drawFileDD(self, mouse):
        self.drawButton(mouse, self.openRect)
        pg.draw.rect(self.screen, self.color, self.inputBox, 2)
        filename = self.smallfont.render(self.inputText, True, self.color)
        self.screen.blit(
            self.openText, self.openText.get_rect(center=self.openRect.center)
        )
        self.screen.blit(
            self.smallfont.render("File name:", True, self.color), (130, 180)
        )
        self.screen.blit(filename, filename.get_rect(center=self.inputBox.center))
        return

    # Draw dropdown skin for connecting to a neurotech device.
    def drawConnectDD(self, mouse):
        self.dropdown_connect_hardware.draw(self.screen)

        if self.dropdown_connect_hardware.main == MUSE:
            self.dropdown_connect_model_muse.draw(self.screen)
        elif self.dropdown_connect_hardware.main == BCI:
            self.dropdown_connect_model_bci.draw(self.screen)
        else:
            self.dropdown_connect_model_default.draw(self.screen)

        self.drawButton(mouse, self.connectRect)
        self.screen.blit(
            self.connectText, self.connectText.get_rect(center=self.connectRect.center)
        )
        return

    # Draw dropdown skin for simulating neurotech device data.
    def drawSimulateDD(self, mouse):
        return

    # Plots the cacti
    def plot(self):
        # https://www.pygame.org/wiki/MatplotlibPygame
        # Accessed May 8th, 2021

        self.cacti.draw(self.screen)
        self.cacti.update()

        self.bullets.draw(self.screen)
        self.bullets.update()

        self.dino.draw(self.screen)

        if pg.sprite.spritecollide(self.dino.sprites()[0], self.cacti, False):
            self.mode = MAIN
            self.cacti.empty()
            self.bullets.empty()

        # Remove cacti which already moved across the screen
        for bullet in self.bullets:
            if pg.sprite.spritecollide(bullet, self.cacti, True):
                bullet.kill()

        return

    def addToHypnogram(self, data):
        channel = np.array(data).T[0]
        N, S = 256, []

        for k in range(0, channel.shape[0] + 1, N):
            x = fft.fftshift(fft.fft(channel[k : k + N], n=N))[N // 2 : N]
            Pxx = 10 * np.log10(np.real(x * np.conj(x)))
            S.append(Pxx)

        specgram = np.array(S).T
        alpha = specgram[32:64, :]
        self.hypnogram_data.append(np.mean(alpha, axis=0))

    # Saves the created neurotech device data to the given filename
    def openFile(self):
        if self.input_file is not None:
            self.input_file.close()

        try:
            self.input_file = open(self.inputText, "r")
        except FileNotFoundError:
            print("Error: File specified does not exist.")
        else:
            print("Reading from " + self.inputText)
            self.data = []
            self.input_file.readline()  # Get rid of header
            self.inputText = "Input Filename"

        return

    def writeToOutput(self, data):
        with open(self.output_filename, mode="a", newline="") as file:
            fwriter = csv.writer(
                file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            fwriter.writerows(data)

    def readFromFile(self):
        assert self.input_file is not None
        lines = []

        for _ in range(24):  # Read 24 lines at a time
            line = self.input_file.readline()

            if not line:
                print("Reached end of input file. Closing file.")
                self.input_file.close()
                self.input_file = None
                return []

            line = line[1:-1].split(",")
            lines.append([float(i) for i in line])
        return lines

    # Draw the screen for the first plot button (dinosaur)
    def drawPlot(self, mouse):
        self.drawButton(mouse, self.exitRect)
        back = self.smallfont.render("Back", True, self.color)
        self.screen.blit(back, back.get_rect(center=self.exitRect.center))

        if self.mode == PLOT1:
            self.screen.blit(
                self.smallfont.render("Press 'Space' to shoot!", True, self.color),
                (240, 30),
            )
        elif self.mode == PLOT2:
            self.screen.blit(
                self.smallfont.render("Think real hard!", True, self.color), (240, 30)
            )

        self.plot()
        return

    # Updates the given dropdown, depending on if it was clicked on
    def updateDropDown(self, dropDown, ev_list):
        selected_option = dropDown.update(ev_list)
        if selected_option >= 0:
            dropDown.main = dropDown.options[selected_option]
        return

    # Connects to a Muse
    def connect(self):
        if self.dropdown_connect_hardware.main == MUSE:
            model = self.dropdown_connect_model_muse.main
        elif self.dropdown_connect_hardware.main == BCI:
            model = self.dropdown_connect_model_bci.main

        self.board = Board(
            self.dropdown_main.main, self.dropdown_connect_hardware.main, model
        )
        return

    # Accepts the stream, sends it to the right arrays
    def lsl_streamers(self, sample):
        self.outlet_eeg.push_sample(np.array(sample.channels_data) * SCALE_FACTOR_EEG)
        self.outlet_aux.push_sample(np.array(sample.aux_data) * SCALE_FACTOR_AUX)

    # Where to change the jump condition
    def fire_condition_met(self, ev_list, data):
        if self.mode == PLOT1:  # Jump when space bar key is pressed
            return any(ev.type == pg.KEYDOWN and ev.key == pg.K_SPACE for ev in ev_list)

        """
        Change this condition to your liking!
        """
        if len(self.hypnogram_data) < 2:
            return False
        return self.hypnogram_data[-1] > self.hypnogram_data[-2]

    # The main function
    def run(self):
        done = False

        # While the screen has not been exited
        while not done:
            self.clock.tick(10)

            # If a muse is connected, take input
            if self.streaming:
                if self.dropdown_main.main == SIMULATE:
                    data = (
                        np.random.random((20, 4)) * 2000 - 1000
                    )  # Map from 0 - 1 -> -1000 - 1000
                elif self.dropdown_main.main == FILE:
                    if self.input_file is not None:
                        data = self.readFromFile()
                    else:
                        print("Please use an existing data file!")
                elif self.dropdown_main.main == CONNECT:
                    data = self.board.get_new_data()
                else:
                    data = []

                # Only waste time appending if we need to.
                if len(data):
                    print("Pulled: {}".format(data.shape))
                    self.writeToOutput(data)
                    self.addToHypnogram(data)
            else:
                data = []

            # stores the (x,y) coordinates into
            # the variable as a tuple
            mouse = pg.mouse.get_pos()

            ev_list = pg.event.get()

            # Update the necessary dropdowns
            if self.mode == MAIN:
                self.updateDropDown(self.dropdown_connect_hardware, ev_list)
                self.updateDropDown(self.dropdown_connect_model_muse, ev_list)
                self.updateDropDown(self.dropdown_connect_model_bci, ev_list)
                self.updateDropDown(self.dropdown_main, ev_list)

            for ev in ev_list:
                if ev.type == pg.QUIT:
                    done = True

                # checks if a mouse is clicked
                if ev.type == pg.MOUSEBUTTONDOWN:

                    if self.mode == MAIN:
                        # if the mouse is clicked on the
                        # button the game is terminated
                        if self.exitRect.collidepoint(mouse):
                            done = True

                        # Change modes depending on the current scren
                        if self.plot1Rect.collidepoint(mouse):
                            self.mode = PLOT1

                        if self.plot2Rect.collidepoint(mouse):
                            self.mode = PLOT2

                        # if the mouse is clicked on the
                        # button the game is terminated

                        if self.plot1Rect.collidepoint(mouse):
                            time.sleep(0.01)
                            self.mode = PLOT1

                        if self.plot2Rect.collidepoint(mouse):
                            self.mode = PLOT2

                        # Detect clicks on the circle
                        sqx = (mouse[0] - self.circPos[0]) ** 2
                        sqy = (mouse[1] - self.circPos[1]) ** 2

                        if (sqx + sqy) ** 0.5 <= 20:
                            self.streaming = not self.streaming

                        # Logic for the file dropdown
                        if self.dropdown_main.main == FILE:
                            if self.inputBox.collidepoint(mouse):
                                self.fileInputActive = True
                                self.inputText = ""

                            if self.openRect.collidepoint(mouse):
                                self.openFile()

                            if self.inputBox.collidepoint(mouse):
                                self.fileInputActive = True
                                self.inputText = ""
                            else:
                                self.fileInputActive = False
                                if not len(self.inputText):
                                    self.inputText = "Input Filename"

                        # Logic for the connect dropdown
                        if self.dropdown_main.main == CONNECT:

                            if self.connectRect.collidepoint(mouse):
                                print(self.dropdown_connect_hardware.main)
                                # if self.dropdown_connect_hardware.main in [FILE, CONNECT, SIMULATE]:
                                self.connect()
                                # else:
                                # print("You must select a type of device to connect to.")

                    # Clear the cacti when going back to main screen
                    if self.mode in (PLOT1, PLOT2) and self.exitRect.collidepoint(
                        mouse
                    ):
                        self.cacti.empty()
                        self.bullets.empty()
                        self.mode = MAIN

                if self.mode != MAIN:
                    # This version is for click-generation of cacti
                    if random.random() > 0.9:
                        self.cacti.add(Cactus(self.width, self.floor))

                if ev.type == pg.KEYDOWN:
                    # Detect input on file name
                    if self.fileInputActive:
                        if ev.key == pg.K_RETURN:
                            self.fileInputActive = False
                        elif ev.key == pg.K_BACKSPACE:
                            self.inputText = self.inputText[:-1]
                        else:
                            self.inputText += ev.unicode

            if self.mode != MAIN and self.fire_condition_met(ev_list, data):
                self.bullets.add(Bullet(150, self.floor + 35))

            # fills the screen with a color
            self.screen.fill(BACKGROUND_COLOR)

            # Draw the appropriate screen.
            if self.mode == MAIN:
                self.drawMain(mouse)
            else:
                self.drawPlot(mouse)

            # updates the frames of the game
            pg.display.update()

        return


def main():
    interface = MuseInterface()
    interface.run()


if __name__ == "__main__":
    main()
