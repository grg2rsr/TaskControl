from psychopy import visual, core, monitors
from psychopy.visual.windowwarp import Warper
import socket
import struct

mon = monitors.Monitor(name="display",width=10,distance=5)
win = visual.Window(size=[1024,768], monitor=mon, screen=0, fullscr=False, useFBO=True)
# warper = Warper(win,
#                 warp='spherical',
#                 warpfile = "",
#                 warpGridsize = 128,
#                 eyepoint = [0.5, 0.5],
#                 flipHorizontal = False,
#                 flipVertical = False)

gabor = visual.GratingStim(win, tex='sin', mask='gauss', sf=5, name='gabor', autoLog=False, size=2)

def update(x,y):
    x = x / 10
    y = y / 10
    gabor.draw()
    win.flip()

UDP_IP, UDP_PORT = "127.0.0.1", 4002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False) 

while True:
    try:
        raw_read = sock.recv(8)
        x,y = struct.unpack('ff',raw_read)
        update(x,y)       

    except BlockingIOError:
        pass

