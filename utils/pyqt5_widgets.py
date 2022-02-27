# thsi file will have bermuda widgets to be imported and displayed by a mainwindow

import sys
from math import sqrt, acos, pi
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5 import QtGui
from PyQt5.QtOpenGL import *

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import numpy as np


import pdb

class body_glWidget(QGLWidget):
    '''
    This is an opengl object that can be embedded into PyQt5 as an widget
    The program currently has one - an eyeball model for eye tracking, and
    later there'll be a second - a stick figure for body tracking.
    
    Mostly it gets methods and stuff from its parent class
    
    paintGL is the function where you put all the onjects you want to display.
     - paintGL is called by updateGl, which is called by update (in the UI_MainWindow class)
    
    initializeGL is the function for camera settings and stuff
     - it gets called automatically by some hidden gl function in the beginning
    
    
    '''
    # def __init__(self, parent=None):
    def __init__(self, parent):
        # QGLWidget.__init__(self, parent)
        QGLWidget.__init__(self)
        self.parent = parent
        print('body parent',self.parent)
        self.setMinimumSize(700, 500)

    def paintGL(self):
        '''
        This is for all the objects you want to display. Their color, position,
        rotation, etc.
        
        I don't know how to give it arguments (like an angle to rotate something by)
        Currently I'm using global variables to substitute.
        
        The three axes in relation to the screen (approximate):
        positive z is out of the screen and slightly left
        positive x is right
        positive y is up
        
        '''
        
        #print('painting gl')
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE )
        
        #angle = -15  * count
        #glRotatef(angle,0,1,0)
        
        #new_x = -0*count - 3.0
        y = 0.5
        z = -6
        
        # negative z is into the sreen and slightly right
        # positive x is right
        # positive y is up
        
        # positioning camera
        # note: this line works on my windows computer with its screen
        # cahnge the 3 and 1 as necesssary for different windows computers
        gluLookAt(0,0,10,3,1,0,0,1,0)
        # this line will work on a mac
        #gluLookAt(0,0,10,0,0,0,0,1,0)
    
        # rotating camera by time
        count = self.parent.get_count()
        # print("paint's count:",count)
        glRotatef(count*3,0,1,0)
        
        # list of lists. Each sublist is a vertex. Pair them so they make desired lines
        
        # 21 samples - 7 sets of 3
        # head, shoulders, hips, rhand, lhand, rfoot, lfoot
        
        # * person is facing away from camwra so their right and our right is the same
        body_posn = self.parent.get_body_posn()
        head =  np.add([0,0.5,0], body_posn[0:3])
        shoulders = np.add([0,0,0], body_posn[3:6])
        hips = np.add([0,-1,0], body_posn[6:9])
        rhand = np.add([1,0.5,0], body_posn[9:12])
        lhand = np.add([-1,0.5,0], body_posn[12:15])
        rfoot = np.add([0.5,-2,0], body_posn[15:18])
        lfoot = np.add([-0.5,-2,0], body_posn[18:21])
        
        
        
        # print('paint head',head)
        # print('paint shoulders',shoulders)
        # print('paint hips', hips)
        
        # let's define some variables to go into the list. They can be edited with new data
        

        
        vertices = [shoulders, hips, shoulders, rhand, shoulders, lhand, hips,
                    rfoot, hips, lfoot]
        
        # glTranslatef(-3,0,0)
        
        glLineWidth(5)
        glColor3f(1.0, 0.0, 0.0)
        glNormal3f( 0, 0, 1 )
        # GL_LINES takes a stream of vertices and makes them into lines in pairs
        # vertices 1 and 2 are a line, 3 and 4 etc. If you give an odd number, the last one is ignored
        glBegin(GL_LINES)
#        glVertex3f(0.0, 0.0, 0.0)
#        glVertex3f(3, 0, 0)
        
        for vertex in vertices:
            glVertex3f(vertex[0],vertex[1],vertex[2])
        glEnd()
        
        for i in range(int(len(vertices)/2)):
            vertex1 = vertices[2*i]
            vertex2 = vertices[2*i+1]
            glTranslatef(vertex1[0],vertex1[1],vertex1[2])
            vector = []
            for j in range(len(vertex1)):
                vector.append(vertex1[j]-vertex2[j])
            length = sqrt(vector[0]**2 + vector[1]**2 +vector[2]**2)
            for j in range(len(vector)):
                vector[j] = vector[j]/length
            # processing the vector to turn it into an angle and axis of rotation to be given to glRotatef
            # cross product vector with current direction (0,0,1)
            axis = [0,0,1]
            cross = [-vector[1], vector[0], 0]
            #print(cross,i)
            # dot product of same two vectors
            dot = acos(vector[2]) *180 / pi
            glRotatef(dot - 180,cross[0],cross[1],cross[2])
            gluCylinder(gluNewQuadric(),0.1,0.1,length,6,8)
            glRotatef(180 - dot,cross[0],cross[1],cross[2])
            glTranslatef(-vertex1[0],-vertex1[1],-vertex1[2])
            
            
            
            
        # making a disk for the head
        glNormal3f( 0, 0, 1 )
        glTranslatef(head[0],head[1],head[2])
        # gluDisk(gluNewQuadric(),0.0,0.5,16,8)
        
        gluSphere(gluNewQuadric(),0.5,32,32)
        
        glFlush()

        glDisable(GL_LIGHT0)
        glDisable(GL_LIGHT1)
        glDisable(GL_LIGHTING)
        glDisable(GL_COLOR_MATERIAL)

    def initializeGL(self):
        glClearDepth(1.0)              
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()  
        
        # this line is for camera settings. First number is the field of view in y direction (degrees)
        # next number is x:y aspect ratio
        # next two numbers are the distance to the near and far clip planes 
        # - only objects between them will be shown, must both be positive
        originalperspective = [45.0,1.33,0.1, 100.0]               
        gluPerspective(50.0,1.6,0.1, 100.0) 
        
        glMatrixMode(GL_MODELVIEW)
        
        glLight(GL_LIGHT0, GL_POSITION,  (-5, 5, 5, 1)) # point light from the left, top, front, I think
        glLight(GL_LIGHT1, GL_POSITION,  (0, 2, 1, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))


class eye_glWidget(QGLWidget):
    '''
    This is an opengl object that can be embedded into PyQt5 as an widget
    The program currently has one - an eyeball model for eye tracking, and
    later there'll be a second - a stick figure for body tracking.
    
    Mostly it gets methods and stuff from its parent class
    
    paintGL is the function where you put all the onjects you want to display.
     - paintGL is called by updateGl, which is called by update (in the UI_MainWindow class)
    
    initializeGL is the function for camera settings and stuff
     - it gets called automatically by some hidden gl function in the beginning
    
    
    '''
    # def __init__(self, parent=None):
    def __init__(self, parent):
        # QGLWidget.__init__(self, parent)
        QGLWidget.__init__(self)
        self.parent = parent
        print('eye parent',self.parent)
        original_min_zsize = (700, 500)
        self.setMinimumSize(700, 500)
        #pdb.set_trace()

    def paintGL(self):
        '''
        This is for all the objects you want to display. Their color, position,
        rotation, etc.
        
        I don't know how to give it arguments (like an angle to rotate something by)
        Currently I'm using global variables to substitute.
        
        The three axes in relation to the screen (approximate):
        positive z is out of the screen and slightly left
        positive x is right
        positive y is up
        
        '''
        
        #print('painting gl')
        #global count
        #print("paint's count:",count)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE )
        
        # positioning camera
        # note: this line works on my windows computer with its screen
        # cahnge the 3 and 1 as necesssary for different windows computers
        gluLookAt(0,0,10,3,1,0,0,1,0)
        # this line will work on a mac
        #gluLookAt(0,0,10,0,0,0,0,1,0)
    
        # rotating camera by time
        count = self.parent.get_count()
        # print("paint's count:",count)
        glRotatef(count*3,0,1,0)
        
        # negative z is into the sreen and slightly right
        # positive x is right
        # positive y is up
        
        # drawing a set of axes to test
        # glTranslatef(0, 0,-12)
        glBegin(GL_LINES)
        glColor3f(1,0,0)
        glVertex3f(1,0,0)
        glVertex3f(0,0,0)
        glColor3f(0,1,0)
        glVertex3f(0,1,0)
        glVertex3f(0,0,0)
        glColor3f(0,0,1)
        glVertex3f(0,0,1)
        glVertex3f(0,0,0)
        glEnd()
        
        
        original_translate = (-1, -2.0, -12)
        # glColor3f( 1.0, 1.5, 0.0 )
        # glPolygonMode(GL_FRONT, GL_FILL)
        # glBegin(GL_TRIANGLES)
        # original1 = [2.0,-1.2,0.0]
        # glVertex3f(-0.5,-0.5,0.0)
        # original2 = [2.6,0.0,0.0]
        # glVertex3f(0.5,-0.5,0.0)
        # original3 = [2.9,-1.2,0.0]
        # glVertex3f(0,1,0.0)
        # glEnd()
        
        # processing a vector to normalize it
        # test vector value (uncomment this line and comment out the gloable to give it your own vector)
        #vector = [4,3,2]
        vector = self.parent.get_vector()
        #print("paint's init vector:",vector)
        
        magnitude = sqrt(vector[0]**2 + vector[1]**2 +vector[2]**2)
        for i in range(len(vector)):
            vector[i] = vector[i]/magnitude
        #print("paint's norm vector:",vector)

        # processing the vector to turn it into an angle and axis of rotation to be given to glRotatef
        # cross product vector with current direction (0,0,1)
        axis = [0,0,1]
        cross = [-vector[1], vector[0], 0]
        # dot product of same two vectors
        dot = acos(vector[2]) *180 / pi
        
        # making eyeball - drawing sphere and two cylinders (iris and pupil)
        # glTranslatef(-3.0, 1.0, 4)
        
#        if count % 2 == 0:
#            glRotatef(dot,cross[0],cross[1],cross[2])
#        else:
#            glRotatef(0,0,0,0)
#        eye_angle = count*4 - 10
        
        glRotatef(dot,cross[0],cross[1],cross[2])
        glColor3f(1.0, 1.0, 1.0)
        gluSphere(gluNewQuadric(),1,32,32)
        # making iris/pupil cylinder
        glColor3f(0.0, 0.9, 0.2)
        gluCylinder(gluNewQuadric(),0.5,0.5,1,6,16)
        # closing end of cylinder with a disk (disk is translated +z by cylinder's height)
        glTranslatef(0, 0, 1)
        gluDisk(gluNewQuadric(),0.0,0.5,6,8)
        
        # now let's make a pupil in the iris
        glTranslatef(0, 0, -0.9)
        glColor3f(0.0, 0., 0.0)
        gluCylinder(gluNewQuadric(),0.2,0.2,1,16,16)
        # closing end of cylinder (disk is translated +z by cylinder's height)
        glTranslatef(0, 0, 1)
        gluDisk(gluNewQuadric(),0.0,0.2,16,8)
        
        
        glFlush()

        glDisable(GL_LIGHT0)
        glDisable(GL_LIGHT1)
        glDisable(GL_LIGHTING)
        glDisable(GL_COLOR_MATERIAL)

    def initializeGL(self):
        glClearDepth(1.0)              
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()  
        
        # this line is for camera settings. First number is the field of view in y direction (degrees)
        # next number is x:y aspect ratio
        # next two numbers are the distance to the near and far clip planes 
        # - only objects between them will be shown, must both be positive
        originalperspective = [45.0,1.33,0.1, 100.0]               
        gluPerspective(45,1.4,1, 100.0) 
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        glLight(GL_LIGHT0, GL_POSITION,  (-5, 5, 5, 1)) # point light from the left, top, front, I think
        glLight(GL_LIGHT1, GL_POSITION,  (0, 2, 1, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))
  
        
        
class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.patch.set_facecolor('w')
        fig.set_tight_layout(True)
        self.axes = fig.add_subplot(1,1,1)
        self.axes.set_facecolor('w')
        self.fig = fig
        super(MplCanvas, self).__init__(fig)