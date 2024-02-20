// Teensy 4.0 Telemetry System
// 7/20/2023
// Garrett Miskoe

#include <FlexCAN_T4.h>

FlexCAN_T4<CAN1, RX_SIZE_256, TX_SIZE_16> can;
CAN_message_t msg;
//CAN_message_t steer;
#define NUM_TX_MAILBOXES 0
#define NUM_RX_MAILBOXES 5


unsigned long total = 0; // total injector open time
unsigned long starttime = 0;
unsigned long endtime = 0;
unsigned long oldstart = 0;
bool buttonState = false; // true represents a button press
unsigned long buttonTime = 0;
bool voltageDrop = false; // flag raised when the voltage drops abruptly
#define voltThresh 10 * 1 // Max drop amount between frames for the voltageDrop flag to be raised (multiplied by 10 for the scaling factor)
uint16_t lastVolt = 0;
#define voltTime 10 * 1000 // Time, in milleseconds, that the voltage drop flag is rasied for
unsigned long voltFallTime = 0;


#define fuelPin 3
#define STBY 21
#define buttonPin 19
#define buttonDelay 5000 // Time, in milleseconds, that the button press is remembered for
//#define AVI1 20
#define transmitPeriod 300 //Time, in milleseconds, between serial output data transmissions

uint16_t TPS = 0; // *10
uint16_t RPM = 0;
uint16_t AFR = 0; // AFR * 10
uint16_t H2O = 0; // water temp in C
uint16_t volt = 0; // battery voltage * 10
uint16_t MAP = 0; // manifold air pressure in kPa * 10
uint16_t ignitionAngle = 0; // leading ignition angle in degrees * 10
uint16_t revolutions = 0; // engine revolutions recorded since ignition start
byte dutyCycle = 0;


void setup() {
  Serial1.begin(112500);
  digitalWrite(STBY, LOW); // Puts the CAN Transciever into Normal mode
  can.begin();
  can.setBaudRate(1000000);
  can.setMaxMB(NUM_TX_MAILBOXES + NUM_RX_MAILBOXES);

  for (int i = NUM_RX_MAILBOXES; i<(NUM_TX_MAILBOXES + NUM_RX_MAILBOXES); i++){
    can.setMB((FLEXCAN_MAILBOX)i,TX);
  } // In this case MB0-MB4 are recieve
  can.setMBFilter(REJECT_ALL); // Rejects all messages in all mailboxes, except for allowed ID's below
  can.setMBFilter(MB0,0x360); //CAN ID for RPM and TPS
  can.setMBFilter(MB1,0x362); // CAN ID for ignition angle
  can.setMBFilter(MB2,0x368); //CAN ID for AFR
  can.setMBFilter(MB3,0x372); // CAN ID for Battery Voltage
  can.setMBFilter(MB4,0x3E0); //CAN ID for Coolant Temperature

  can.enableMBInterrupts();
  can.onReceive(MB0, RPMreceive);
  can.onReceive(MB1, ignitionrecieve);
  can.onReceive(MB2, AFRreceive);
  can.onReceive(MB3, voltreceive);
  can.onReceive(MB4, H20receive);

  pinMode(fuelPin, INPUT_PULLUP);
  attachInterrupt(fuelPin, change, CHANGE);

  pinMode(buttonPin, INPUT_PULLUP);
  attachInterrupt(buttonPin, buttonPress, FALLING); // button has a pullup resistor (see line above) so this interrupt is called when the button is pressed and pulls the pin to ground
}

void loop() {

  if (buttonState == 1) {
    if (millis() > buttonTime){
      buttonState = 0; // Reset the button value after the buttonDelay has expired
    }
  }

  can.events();
  serialPrint();
  delay(transmitPeriod); // Slow the loop time, does not block Serial1 or interrupts
}

void serialPrint(){ // Sends data to serial port, delimited with commas. Each line is a new set of data
  Serial1.print(total); Serial1.print(',');
  Serial1.print(RPM); Serial1.print(',');
  Serial1.print(TPS); Serial1.print(',');
  Serial1.print(AFR); Serial1.print(',');
  Serial1.print(H2O); Serial1.print(',');
  Serial1.print(volt); Serial1.print(',');
  Serial1.print(MAP); Serial1.print(',');
  Serial1.print(ignitionAngle); Serial1.print(',');
//  Serial1.print(Steer); Serial1.print(',');
  Serial1.print(dutyCycle); Serial1.print(',');
  Serial1.print(revolutions); Serial1.print(',');
  Serial1.print(voltageDrop); Serial1.print(',');
  Serial1.println(buttonState);
}

void change(){
  if(digitalRead(fuelPin) == 0){
 //   Serial1.println("FALL");
    starttime = millis();
    revolutions = revolutions + 2; // add 2 revs for each injector firing
    dutyCycle = byte(float(oldstart - endtime) / float(starttime - oldstart));
  }else{
 //   Serial1.println("RISE");
    endtime = millis();
    total = endtime - starttime + total;
    oldstart = starttime;
  }
}

void buttonPress(){
  // this activates when the green steering wheel button is pressed down
  buttonState = true;
  buttonTime = buttonDelay + millis(); // time when the flag expires
}

void RPMreceive (const CAN_message_t &msg)  {
  RPM = (msg.buf[0]<<8)|msg.buf[1];
  MAP = (msg.buf[2]<<8)|msg.buf[3];
  TPS = (msg.buf[4]<<8)|msg.buf[5];
}

void ignitionrecieve (const CAN_message_t &msg)  {
  ignitionAngle = (msg.buf[4]<<8)|msg.buf[5];
}

void AFRreceive (const CAN_message_t &msg)  {
  AFR = (msg.buf[0]<<8)|msg.buf[1];
}

void voltreceive (const CAN_message_t &msg)  {
  //lastVolt = volt;
  volt = (msg.buf[0]<<8)|msg.buf[1];
  //voltageDrop = voltageFlag(); // logic to determine if the voltage drops abruptly. If so, the flag is rasied
}

void H20receive (const CAN_message_t &msg)  {
  H2O = (msg.buf[0]<<8)|msg.buf[1];
}

bool voltageFlag(){
  if ((lastVolt-voltThresh) > volt){
    // raise the flag
    voltFallTime = millis();
    return true;
  }else{
    if ((millis()-voltTime) > voltFallTime){
      // lower the flag
      return false;
    }
    // time has not expired, flag is still raised
    return true;
  }
}
