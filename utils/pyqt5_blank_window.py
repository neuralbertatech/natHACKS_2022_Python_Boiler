'''
This is a very basic PyQt5 window
It can be adapted to do anything
'''

import sys

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, QtOpenGL, Qt
from PyQt5.QtWidgets import *

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
  
    def closeEvent(self, event):
        # this code will autorun just before the window closes
        
        event.accept()

if __name__ == '__main__':    
    app = QApplication(sys.argv)    
    win = MenuWindow() 
    win.show() 
    sys.exit(app.exec())