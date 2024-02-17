import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time

# Program Constants
serialBaudrate = 115200
serialPort = 'COM7' # different for different computers, devices
dataRate = 4 # estimated rate of newlines recieved by the serial port, in Hertz. MUST BE AN INT
dataPeriod = 1.0/dataRate # a portion of the period of the datarate, for the program to plt.pause - this way it will most likely be done with plt.pause and waiting when the next data line arrives
displayPeriod = 30 # how long the time graphs are, data over this amount (in seconds) old is removed from memory
listLength = displayPeriod * dataRate # fixed length lists for time respective data will be this long
xlist = list(range(0,listLength, 1)) # list, 0-300
zerolist = [0] * listLength # does the same as 'zeros(listlength)' in MATLAB

# Set up GUI elements
# Right hand side time-graphs
fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, sharex=True, figsize=[10,10], animated=True) # animated=True tells matplotlib to only draw the artist (axes) when we explicitly tell it
plt.get_current_fig_manager().full_screen_toggle()
plt.xticks([])
fig.suptitle('Miskoe Motorsports Telemetry, Car #770')
ax1.set_ylabel('RPM  ', rotation='horizontal', horizontalalignment='right')
ax2.set_ylabel('TPS  ', rotation='horizontal', horizontalalignment='right')
ax3.set_ylabel('Speed (mph)  ', rotation='horizontal', horizontalalignment='right')
ax4.set_ylabel('Water Temp  ', rotation='horizontal', horizontalalignment='right')
ax5.set_ylabel('Oil Press  ', rotation='horizontal', horizontalalignment='right')

ax1.set_xlim([0,displayPeriod]) # Time axis
ax1.set_ylim([0,7200]) # RPM
ax2.set_ylim([0,100]) # TPS
ax3.set_ylim([0,120]) # Speed
ax4.set_ylim([0,235]) # Water temp
ax5.set_ylim([0,60]) # Oil Pressure
plt.get_current_fig_manager().full_screen_toggle()

line1, = ax1.plot(xlist, zerolist, 'r-')
line2, = ax2.plot(xlist, zerolist, 'r-')
line3, = ax3.plot(xlist, zerolist, 'r-')
line4, = ax4.plot(xlist, zerolist, 'r-')
line5, = ax5.plot(xlist, zerolist, 'r-')

# Bottom left table
table = plt.table(cellColours=['1', '1', '1', '1', '1', '1', '1'], cellLoc='right', rowLabels=['RPM', 'TPS', 'Fuel Burned', 'Fuel Left', 'Oil Temp', 'Water Pressure', 'Duty Cycle'], loc='left', bbox=[-0.7,0.1, 0.15, 2]) #cellText=None, ,

# Top left map
map = fig.add_axes(rect=[0.03,0.5,0.35,0.4])
plt.xticks([])
plt.yticks([])

fig.subplots_adjust(wspace=0.1, left=0.5, right=0.98, top=0.92, bottom=0.05)
#plt.show(block=False)
plt.pause(0.1)
background = fig.canvas.copy_from_bbox(fig.bbox) # copies the entire figure into a 'background' object
# draw the animated artist (the figure)
fig.draw_artist(ax1)
fig.draw_artist(ax2)
fig.draw_artist(ax3)
fig.draw_artist(ax4)
fig.draw_artist(ax5)
fig.canvas.blit(fig.bbox) # show the result to the screen


class SerialPort:
    def __init__(self):
        self.ser = serial.Serial()
        self.open_serial_port()
        self.errorCount = 0 # gives each instnace an error counter

    def open_serial_port(self):
        try:
            if self.ser.is_open:
                self.ser.close()
            self.ser.port = serialPort
            self.ser.baudrate = int(serialBaudrate)
            self.ser.open()
        except serial.SerialException as e: # kinda janky but this part tries to reopen the serial port endlessly if it fails to open
            print(f"Error opening serial port: {e}")
            #plt.pause(1)
            time.sleep(1)
            self.open_serial_port()

    def serial_reader(self):
        while True:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    if len(line) == 15: # check to make sure the length of the line is correct, then pass it to the callback
                        self.serial_callback(line)
                        time.sleep(dataPeriod)

            except:
                if self.ser.is_open:
                    print("Error reading serial data")
                    self.errorCount +=1 # increment error count
                    if self.errorCount > 5:
                        self.errorCount = 0 # reset the error count, force close the serial port, then try to reopen
                        self.ser.close()
                        self.open_serial_port()
                else:
                    self.open_serial_port()

    def serial_callback(self, newline):
        # this gets run every time we recieve serial data, with the new data in a line 'newline'
        stringlist = newline.split(',') # the data line split into a list of strings
        datalist = [int(x) for x in stringlist] # a list of the data as integers, converted from strings in stringlist

        try:  
            dataObject.calculate_data(datalist) # big hitter, gives the datalist to the dataObject, then the calculation results are passed to update_plot
                                                              # the * is required to 'unpack' the result of calculate_data, which is a tuple of lists. It unpacks and passes each list in the tuple as an individual argument
        except Exception as e:
            print('unknown error: %s' %str(e))


class dataManager:
    def __init__(self):
        # make fixed length lists for the parameters which are graphed with time, to store the 'historical' data
        # lists contain all zeros, to start
        self.RPMlist = [0] * listLength
        self.TPSlist = [0.0] * listLength
        self.AFRlist = [0.0] * listLength
        self.WaterTemplist = [0.0] * listLength
        self.steerPoslist = [0] * listLength
        self.total = 0

    def calculate_data(self, newdata): # this calculates and stores the data in individual lists, each with the same length
        self.total = newdata[0] # total fuel injector open time, in milleseconds
        RPM = newdata[1]
        TPS = newdata[2]/10.0
        AFR = newdata[3]/1000.0
        WaterTemp = newdata[4]/10.0 # water temp in degrees Celcius
        self.voltage = newdata[5]/10.0 # car voltage
        steerPos = newdata[6] # steering position

        self.RPMlist = self.increment_list(self.RPMlist, RPM)
        self.TPSlist = self.increment_list(self.TPSlist, TPS)
        self.AFRlist = self.increment_list(self.AFRlist, AFR)
        self.WaterTemplist = self.increment_list(self.WaterTemplist, WaterTemp)
        self.steerPoslist = self.increment_list(self.steerPoslist, steerPos)

        # the order below really matters, otherwise data is plotted on the wrong graph
        #return self.RPMlist, self.TPSlist, self.AFRlist, self.WaterTemplist, self.steerPoslist, total, voltage

    def increment_list(self, lst, newValue): # this function pushed all the existing valued in the list down by 1 index, and then puts the new value in the [0] index

        # OLD WAY, MOVES EVERY ELEMENT IN THE LIST
      #  for i in range(listLength - 1, 0, -1): # move all values down by 1 index
      #      lst[i] = lst[i - 1]
       # lst[0] = newValue # put the new value into the [0] position
        
        # NEW WAY, SLICING:
        lst = lst[:-1] # Keep only the last listLength - 1 elements
        lst = [newValue] + lst # Add the new value to the beginning

        return lst # returns modified list
    

def update_plot(event):#, total, voltage): # this function takes arguments that dataManager.calculate_data returns
    #plt.ioff()
  #  fig.canvas.restore_region(background) # resets the figure to just the background, blank plots

    line1.set_ydata(dataObject.RPMlist)
    line2.set_ydata(dataObject.TPSlist)
    line3.set_ydata(dataObject.AFRlist)
    line4.set_ydata(dataObject.WaterTemplist)
    line5.set_ydata(dataObject.steerPoslist)

    table[(1,0)].get_text().set_text(dataObject.total)
    #table[(1,0)].set_text(dataObject.total)

    #fig.canvas.blit(fig.bbox) # copy the image to the GUI state, but screen might not be changed yet
   # fig.canvas.flush_events() # flush any pending GUI events, re-painting the screen if needed
    #plt.ion() # turns interactive mode ON
   # plt.pause(dataPeriod) # unsure if it finds 'dataPeriod' every loop iteration or not, it is a static variable
   # plt.ioff() # turns interactive mode OFF
    return line1, line2, line3, line4, line5, table, map

def on_close(event):
    print('closed figure!')
 #   plt.close()
    exit()

fig.canvas.mpl_connect('close_event', on_close)


# Create an instance of the dataManager class, this holds all the data
dataObject = dataManager()

# Create an instance of the SerialPort class. This calls the __init__ of the SerialPort class and lets things do their thing
serial_port = SerialPort()
if serial_port.ser.is_open:
    serial_thread = threading.Thread(target=serial_port.serial_reader)
    serial_thread.daemon = True
    serial_thread.start()
    #serial_port.serial_reader() # this method contains the main callback loop, which is called if f  the serial port is open

ani = FuncAnimation(fig, update_plot, interval=dataPeriod, save_count=listLength, blit=False) #interval=dataPeriod * 1000)  # Convert to milliseconds

plt.show()
