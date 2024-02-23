import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time
from PIL import Image

# Program Constants
serialBaudrate = 9600
serialPort = 'COM7' # different for different computers, devices. Program chooses an avaiable port if any are open
linelen = 12 # length of each line of data from the serial port. This means there are 12 data points transmitting
dataPeriod = 100 # data sending interval in milleseconds
displayPeriod = 50 # how long the time graphs are, data over this amount (in seconds) old is removed from memory
listLength = int(round(displayPeriod / (dataPeriod/1000), 0)) # fixed length lists for time respective data will be this long
xlist = list(range(0,listLength, 1)) # list, 0-300
zerolist = [0] * listLength # does the same as 'zeros(listlength)' in MATLAB
fuelConstant = 0.00000114475 # the constant that converts milleseconds of injector time to gallons of fuel burned, found experimentally
mapBackground = 'Thompson_Trackmap.jpg' # image used as the background of the map
mapBounds = [71.8325, 71.821111, 41.978333, 41.983333] # bounds of the map image: [left, right, bottom, top], in degrees (floats)

# Set up GUI elements
# Right hand side time-graphs
fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, sharex=True, figsize=[10,10], animated=True) # animated=True tells matplotlib to only draw the artist (axes) when we explicitly tell it (in FuncAnimation)
plt.get_current_fig_manager().full_screen_toggle()
plt.xticks([])
fig.suptitle('Miskoe Motorsports Telemetry, Car #770')
ax1.set_ylabel('RPM  ', rotation='horizontal', horizontalalignment='right')
ax2.set_ylabel('TPS [%] ', rotation='horizontal', horizontalalignment='right')
ax3.set_ylabel('Air-Fuel Ratio ', rotation='horizontal', horizontalalignment='right')
ax4.set_ylabel('Water Temp [°F] ', rotation='horizontal', horizontalalignment='right')
ax5.set_ylabel('MAP [psi]  ', rotation='horizontal', horizontalalignment='right')

ax1.set_xlim([listLength-1, 0]) # Time axis
ax1.set_ylim([0,7300]) # RPM
ax2.set_ylim([0,100]) # TPS
ax3.set_ylim([0,25]) # AFR
ax4.set_ylim([0,250]) # Water temp
ax5.set_ylim([0,20]) # Manifold Air Pressure (absolute, psi)
plt.get_current_fig_manager().full_screen_toggle()

line1, = ax1.plot(xlist, zerolist, 'r-')
line2, = ax2.plot(xlist, zerolist, 'r-')
line3, = ax3.plot(xlist, zerolist, 'r-')
line4, = ax4.plot(xlist, zerolist, 'r-')
line5, = ax5.plot(xlist, zerolist, 'r-')

# Bottom left table
table = plt.table(cellColours=['1', '1', '1', '1', '1', '1', '1', '1', '1', '1'], cellLoc='right', rowLabels=['RPM', 'TPS', 'Fuel Burned [gal]', 'AFR', 'Water Temp [°F]', 'MAP [psi]', 'Duty Cycle [%]', 'Voltage', 'Ignition Angle [°]', 'Engine Revs'], loc='left', bbox=[-0.7,0.1, 0.15, 2.5], animated=False)
table.set_fontsize(20)


# Box that flashes to alert the pit-lane that the ACK button has been pressed on the steering wheel
buttonPatch = fig.add_axes(rect=[0.27, 0.05, 0.12, 0.15], animated=True)
buttonPatch.set_facecolor('skyblue')
buttonLabel = plt.text(0.5,0.5 ,'ACK Pressed!', horizontalalignment='center', verticalalignment='center', fontsize='xx-large', animated=True)
plt.xticks([])
plt.yticks([])
buttonPatch.set_visible(False)
buttonLabel.set_visible(False)


# Top left map, uses the mapBacground and mapBounds from the program constants above
map = fig.add_axes(rect=[0.015,0.45,0.4,0.55], animated=True)
map.set_xlim([mapBounds[0], mapBounds[1]])
map.set_ylim([mapBounds[2], mapBounds[3]])
mapBackground = Image.open(mapBackground)
map.imshow(mapBackground, extent=mapBounds)
plt.xticks([])
plt.yticks([])

fig.subplots_adjust(wspace=0.1, left=0.5, right=0.98, top=0.92, bottom=0.05)
plt.pause(0.1)

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

        ports = serial.tools.list_ports.comports() # get a list of the available serial ports
        if len(ports) == 1: # if there are any avaiable ports
            self.ser.port = ports[0].device # choose the first available one (assumes only one COM port open)
        else:
            self.ser.port = serialPort # choose the default port if none are open
        self.open_serial_port()
        self.errorCount = 0 # gives each instnace an error counter

    def open_serial_port(self):
        try:
            if self.ser.is_open:
                self.ser.close()
            self.ser.baudrate = int(serialBaudrate)
            self.ser.open()
        except serial.SerialException as e: # kinda janky but this part tries to reopen the serial port endlessly if it fails to open
            print(f"Error opening serial port: {e}")
            time.sleep(1)
            self.open_serial_port()

    def serial_reader(self):
        while True:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    self.serial_callback(line)

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

        if len(datalist) == linelen:
            dataObject.calculate_data(datalist)
        else:
            print('Error: Wrong Line Length!')
        
        
class dataManager:
    def __init__(self):
        self.total = 0 # initalize all single/current data points
        self.RPM = 4321
        self.AFR = 0
        self.TPS = 12
        self.WaterTemp = 0
        self.voltage = 0
        self.MAP = 0
        self.dutyCycle = 0
        self.revolutions = 0
        self.ignitionAngle = 0
        self.voltageFlag = False
        self.buttonState = False

        # make fixed length lists for the parameters which are graphed with time, to store the 'historical' data
        # lists contain all zeros, to start
        self.RPMlist = [self.RPM] * listLength
        self.TPSlist = [self.TPS] * listLength
        self.AFRlist = [self.AFR] * listLength
        self.WaterTemplist = [self.WaterTemp] * listLength
        #self.steerPoslist = [0] * listLength
        self.MAPlist = [self.MAP] * listLength


    def calculate_data(self, newdata): # this calculates and stores the data in individual lists, each with the same length

        self.total = newdata[0] # total fuel injector open time, in milleseconds
        self.RPM = newdata[1]
        self.TPS = newdata[2]/10.0
        self.AFR = newdata[3]/1000.0
        self.WaterTemp = newdata[4]/10.0 # water temp in degrees Celcius
        self.voltage = newdata[5]/10.0 # car voltage
        self.MAP = newdata[6]/10.0 # Manifold Air Pressure in kPa
        self.ignitionAngle = newdata[7]/10.0 # Leading Ignition Angle in degrees
        self.dutyCycle = newdata[8] # duty cycle (%) as an integer
        self.revolutions = newdata[9] # engine revolutions since ignition start
        self.voltageFlag = newdata[10] # flag raised by onboard MCU if the voltage drops abruptly
        self.buttonState = newdata[11] # state of the steering wheel button (1=pressed)
     #  steerPos = newdata[6] # steering position

        # Conversions and calculations
        self.WaterTemp = self.WaterTemp*9/5 + 32 # convert Celsius to Fahrenheit
        self.MAP = round(self.MAP*0.14504, 1) # convert kPa to psi (all absolute pressure) and round to 1 decimal place
        self.total = round(self.total*fuelConstant, 3) # converts milleseconds of injector open time to fuel burned in [gallons] and rounds to 3 decimal places
                            #   ^ this constant is tuned for the car, as we don't know the exact flowrate of the injectors in their dynamic enviornment
                            #     (experimentally tuned)

        # List incremenataions
        self.RPMlist = self.increment_list(self.RPMlist, self.RPM)
        self.TPSlist = self.increment_list(self.TPSlist, self.TPS)
        self.AFRlist = self.increment_list(self.AFRlist, self.AFR)
        self.WaterTemplist = self.increment_list(self.WaterTemplist, self.WaterTemp)
        self.MAPlist = self.increment_list(self.MAPlist, self.MAP)
       # self.steerPoslist = self.increment_list(self.steerPoslist, steerPos)

    def increment_list(self, lst, newValue): # this function pushed all the existing valued in the list down by 1 index, and then puts the new value in the [0] index
        #SLICING:
        lst = lst[:-1] # Keep only the last listLength - 1 elements
        lst = [newValue] + lst # Add the new value to the beginning

        return lst # returns modified list
    
class Visualization:
    def __init__(self):
        self.ACKflag = 0

    def update_plot(event, self):

        # Put new data in each of the line artist objects
        line1.set_ydata(dataObject.RPMlist)
        line2.set_ydata(dataObject.TPSlist)
        line3.set_ydata(dataObject.AFRlist)
        line4.set_ydata(dataObject.WaterTemplist)
        line5.set_ydata(dataObject.MAPlist)
        #line5.set_ydata(dataObject.steerPoslist)

        # Put new data in each of the table cells
        table[(0,0)].get_text().set_text(dataObject.RPM)
        table[(1,0)].get_text().set_text(dataObject.TPS)
        table[(2,0)].get_text().set_text(dataObject.total)
        table[(3,0)].get_text().set_text(dataObject.AFR)
        table[(4,0)].get_text().set_text(dataObject.WaterTemp)
        table[(5,0)].get_text().set_text(dataObject.MAP)
        table[(6,0)].get_text().set_text(dataObject.dutyCycle)
        table[(7,0)].get_text().set_text(dataObject.voltage)
        table[(8,0)].get_text().set_text(dataObject.ignitionAngle)
        table[(9,0)].get_text().set_text(dataObject.revolutions)
    
        # Sets the visibility of the ACK alert to be the button state
        if dataObject.buttonState == 1:
            if self.ACKflag == 0:
                buttonPatch.set_visible(True)
                buttonLabel.set_visible(True)
                self.ACKflag = 1
            else:
                buttonPatch.set_visible(False)
                buttonLabel.set_visible(False)
                self.ACKflag = 0

        return line1, line2, line3, line4, line5, map, buttonPatch, buttonLabel

def on_close(event):
    print('closed figure!')
    exit()

fig.canvas.mpl_connect('close_event', on_close)


# Create an instance of the dataManager class, this holds all the data
dataObject = dataManager()

# Create an instance of the SerialPort class, this manages incoming data
serial_port = SerialPort()
if serial_port.ser.is_open:
    serial_thread = threading.Thread(target=serial_port.serial_reader)
    serial_thread.daemon = True
    serial_thread.start()

# Create an instance of the Visualization class, and pass it to the animation loop
vis = Visualization()
ani = FuncAnimation(fig, vis.update_plot, interval=dataPeriod, save_count=listLength, blit=True)
plt.show()