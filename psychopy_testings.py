from psychopy import visual, core, monitors
from psychopy.visual.windowwarp import Warper
import socket
import struct
import threading 

mon = monitors.Monitor(name="display",width=10,distance=5)#fetch the most recent calib for this monitor
win = visual.Window(size=[1024,768], monitor=mon, screen=0, fullscr=False, useFBO=True)
# warper = Warper(win,
#                 warp='spherical',
#                 warpfile = "",
#                 warpGridsize = 128,
#                 eyepoint = [0.5, 0.5],
#                 flipHorizontal = False,
#                 flipVertical = False)

# Setup stimulus
gabor = visual.GratingStim(win, tex='sin', mask='gauss', sf=5, name='gabor', autoLog=False, size=2)

def update(x,y):
    x = (x - 2281)/10000
    y = (y + 850)/10000
    gabor.pos = [x,y]
    # gabor.phase += 0.01  # Increment by 10th of cycle
    gabor.draw()
    win.flip()

UDP_IP, UDP_PORT = "127.0.0.2", 4001

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False) # non-blocking mode: recv doesn't receive data, exception is raised
# well this might in the end be a bit pointless: first I set it to non-blocking to raise and 
# exception and then I let it pass w/o doing anything. Verify if necessary

# def udp_reader():
while True:
    try:
        # read data and publish it via a qt signal
        raw_read = sock.recv(24) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai
        t,x,y = struct.unpack('>ddd',raw_read)
        # print(x,y)
        update(x,y)       

    except BlockingIOError:
        pass

# th_read = threading.Thread(target=udp_reader)
# th_read.start()