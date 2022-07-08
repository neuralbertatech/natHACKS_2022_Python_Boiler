'''
This is a very basic PyQt5 window
It can be adapted to do anything
'''

import sys

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, QtOpenGL, Qt
from PyQt5.QtWidgets import *

import pyqtgraph as pg


class MenuWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setMinimumSize(800,200)
    
        # setting window title
        self.setWindowTitle('PyQt5 Blank Window')
        
        # init layout
        self.layout = QGridLayout()
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # here is where you create your widgets and add them to the layout
        self.graphWidget = pg.GraphicsLayoutWidget()
        self.graph_layout = QVBoxLayout()
        self.layout.addLayout(self.graph_layout,0,0)
        self.graph_layout.addWidget(self.graphWidget)

        # returns a tuple. first in the tuple is a list of user selected files. next is a string
        # saying what filter was used to select them
        self.files = QFileDialog.getOpenFileNames()[0]

        print('you selected the files',self.files)


  
    def closeEvent(self, event):
        # this code will autorun just before the window closes
        
        event.accept()

if __name__ == '__main__':    
    app = QApplication(sys.argv)    
    win = MenuWindow() 
    win.show() 
    sys.exit(app.exec())