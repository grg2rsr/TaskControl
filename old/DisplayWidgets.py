
"""
 _______   __       _______..______    __          ___   ____    ____
|       \ |  |     /       ||   _  \  |  |        /   \  \   \  /   /
|  .--.  ||  |    |   (----`|  |_)  | |  |       /  ^  \  \   \/   /
|  |  |  ||  |     \   \    |   ___/  |  |      /  /_\  \  \_    _/
|  '--'  ||  | .----)   |   |  |      |  `----./  _____  \   |  |
|_______/ |__| |_______/    | _|      |_______/__/     \__\  |__|

"""
        
class DisplayController(QtWidgets.QWidget):
    """
    brainstorm states:
    idle: dark screen, discarding any command that is not setting it into run
    run: listen to serial port and update the circle according to received x and y
    """

    def __init__(self, parent):
        super(DisplayController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # connecting to the relevant signals
        parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
        parent.LoadCellController.Signals.processed_lc_data_available.connect(self.on_lc_data)

        self.state = "IDLE"
        self.display_for_mouse = True
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Display controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!
        
        # Display and aesthetics # TODO !!!
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.disableAutoRange()
        self.plot_widget.hideAxis('left')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.setYRange(-10,10)
        self.plot_widget.setAspectLocked(True)
        # self.plot_widget.showGrid(x=True,y=True,alpha=0.5)
        # self.plot_widget.showGrid(x=True,y=True)
        self.cursor = self.plot_widget.plot(x=[self.parent().LoadCellController.X_last[0]],
                                            y=[self.parent().LoadCellController.X_last[1]],
                                            pen=(255,255,255), symbolBrush=(255,255,255),
                                            symbolPen='w', symbolSize=150)

        self.Layout.addWidget(self.plot_widget)
        self.setLayout(self.Layout)
        
        self.show()

        # if self.display_for_mouse==True:
        #     # get screens
        #     app = self.parent().main
        #     displays = app.screens()

        #     x = displays[0].geometry().width()
        #     # utils.debug_trace()
            
        #     self.move(QtCore.QPoint(x,0))
        #     self.windowHandle().setScreen(displays[1])
        #     self.showFullScreen() # maximises on screen 1

    def on_lc_data(self,x,y):
        """ update display """
        # if self.state == "RUN":
        self.cursor.setData(x=[x],y=[y])
        pass

    def on_serial(self,line):
        """
        define how command sent from arduino to here should look like
        GET SET CMD RET
        OR: replys go flanked by [ ] // alrady used by sending raw data now
        if line.split() ... 
        """
        if line.startswith('<') and line.endswith('>'):
            read = line[1:-1].split(' ')
            if read[0] == "RET" and read[1] == "DISPLAY":
                if read[2] == "STATE":
                    self.state = read[3]
                    # self.set_state(read[3])

                # if read[2] == "TARGET":
                #     x,y = read[3:]
                #     self.draw_target(x,y)
                # if read[2] == "RGB":
                #     R,G,B = read[3:]
                #     self.set_monochrome(r,g,b)
                # if read[2] == "GRATING":
                #     f,phi,v = read[3:]
                #     self.draw_grating(f,phi,v)
                # if read[2] == "SYNC":
                # flash corner for sync
                
        pass

    def Run(self, folder):
        # stub
        # 
        pass

    def closeEvent(self, event):
        # stub
        self.close()


# psychopy
  
# from psychopy import visual, core, monitors
# from psychopy.visual.windowwarp import Warper

# class DisplayControllerPP(QtWidgets.QWidget):

#     def __init__(self, parent):

#         super(DisplayControllerPP, self).__init__(parent=parent)
#         self.setWindowFlags(QtCore.Qt.Window)

#         # here all the other stuff goes in from the computer downstairs ... 

#         parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
#         parent.LoadCellController.Signals.processed_lc_data_available.connect(self.on_lc_data)

#         self.state = "IDLE"
#         self.display_for_mouse = True
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle("Display controller")
#         self.Layout = QtWidgets.QHBoxLayout()
#         self.setMinimumWidth(300) # FIXME hardcoded!

#         # self.Layout.addWidget(self.plot_widget)
#         self.setLayout(self.Layout)
        
        
#         self.mon = monitors.Monitor(name="display",width=10,distance=5)#fetch the most recent calib for this monitor

#         self.win = visual.Window(size=[1024,768], monitor=self.mon, screen=0, fullscr=False, useFBO=True)

#         # warper = Warper(win,
#         #                 warp='spherical',
#         #                 warpfile = "",
#         #                 warpGridsize = 128,
#         #                 eyepoint = [0.5, 0.5],
#         #                 flipHorizontal = False,
#         #                 flipVertical = False)

#         # Setup stimulus
#         self.gabor = visual.GratingStim(self.win, tex='sin', mask='gauss', sf=5, name='gabor', autoLog=False, size=3)

#         self.show()

#     def on_lc_data(self,x,y):
#         """ update display """
#         self.gabor.pos = [x,y]
#         self.gabor.draw()
#         self.win.flip()
#         pass

#     def on_serial(self,line):
#         """
#         define how command sent from arduino to here should look like
#         GET SET CMD RET
#         OR: replys go flanked by [ ] // alrady used by sending raw data now
#         if line.split() ... 
#         """
#         if line.startswith('<') and line.endswith('>'):
#             read = line[1:-1].split(' ')
#             if read[0] == "RET" and read[1] == "DISPLAY":
#                 if read[2] == "STATE":
#                     self.state = read[3]
#                     # self.set_state(read[3])

#                 # if read[2] == "TARGET":
#                 #     x,y = read[3:]
#                 #     self.draw_target(x,y)
#                 # if read[2] == "RGB":
#                 #     R,G,B = read[3:]
#                 #     self.set_monochrome(r,g,b)
#                 # if read[2] == "GRATING":
#                 #     f,phi,v = read[3:]
#                 #     self.draw_grating(f,phi,v)
#                 # if read[2] == "SYNC":
#                 # flash corner for sync
                
#         pass

#     def Run(self, folder):
#         # stub
#         # 
#         pass

#     def closeEvent(self, event):
#         # stub
#         self.close()