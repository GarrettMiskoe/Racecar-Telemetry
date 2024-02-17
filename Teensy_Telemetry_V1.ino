// Teensy 4.0 Telemetry System
// 7/20/2023
// Garrett Miskoe

#include <FlexCAN_T4.h>

FlexCAN_T4<CAN1, RX_SIZE_256, TX_SIZE_16> can;
CAN_message_t msg;
//CAN_message_t steer;
#define NUM_TX_MAILBOXES 4
#define NUM_RX_MAILBOXES 4


unsigned long total = 0; // total injector open time
unsigned long starttime = 0;
float fuelC; // fuel consumed in gallons

#define fuelPin 3
#define STBY 21
//#define buttonPin 19
#define AVI1 20
#define transmitPeriod 300 //Time, in milleseconds, between serial output data transmissions

short Steer = 0;
uint16_t TPS = 0;
uint16_t RPM = 0;
uint16_t AFR = 0; // AFR * 10
uint16_t H2O = 0; // water temp in C
uint16_t volt = 0; // battery voltage * 10


void setup() {
  Serial1.begin(112500);
  digitalWrite(STBY, LOW); // Puts the CAN Transciever into Normal mode
  can.begin();
  can.setBaudRate(1000000);
  can.setMaxMB(NUM_TX_MAILBOXES + NUM_RX_MAILBOXES);

/*  for (int i = 0; i<NUM_RX_MAILBOXES; i++){
    can.setMB((FLEXCAN_MAILBOX)i,RX);
  }
  */

  for (int i = NUM_RX_MAILBOXES; i<(NUM_TX_MAILBOXES + NUM_RX_MAILBOXES); i++){
    can.setMB((FLEXCAN_MAILBOX)i,TX);
  } // The recieve mailboxes are first, then the transmit mailboxes follow, so in this case MB0-MB3 are recieve and MB4 is transmit
  can.setMBFilter(REJECT_ALL); // Rejects all messages in all mailboxes, except for allowed ID's below
  can.setMBFilter(MB0,0x360); //CAN ID for RPM and TPS
  can.setMBFilter(MB1,0x368); //CAN ID for AFR
  can.setMBFilter(MB2,0x372); // CAN ID for Battery Voltage
  can.setMBFilter(MB3,0x3E0); //CAN ID for Coolant Temperature

  can.enableMBInterrupts();
  can.onReceive(MB0, RPMreceive);
  can.onReceive(MB1, AFRreceive);
  can.onReceive(MB2, voltreceive);
  can.onReceive(MB3, H20receive);

//  steer.len = 2;
//  steer.id = 0x500;

  pinMode(fuelPin, INPUT_PULLUP);
  attachInterrupt(fuelPin, change, CHANGE);
}

void loop() {

  Steer = analogRead(AVI1); ///10 + 150; // Random constants
  //  steer.buf[0||1] = Steer;
  // can.write(steer);
 
  fuelC = float(total) * 0.00000001; // Random constants
  can.events();
  serialPrint();
  delay(transmitPeriod); // Slow the loop time, does not block Serial1 or interrupts
}

void serialPrint(){ // Sends data to serial port, delimited with commas. Each line is a new set of data
  Serial1.print(total); Serial1.print(',');
 // Serial1.print(fuelC); Serial1.print(',');
  Serial1.print(RPM); Serial1.print(',');
  Serial1.print(TPS); Serial1.print(',');
  Serial1.print(AFR); Serial1.print(',');
  Serial1.print(H2O); Serial1.print(',');
  Serial1.print(volt); Serial1.print(',');
  Serial1.println(Steer);
}

void change(){
  if(digitalRead(fuelPin) == 0){
 //   Serial1.println("FALL");
    starttime = millis();
  }else{
 //   Serial1.println("RISE");
    total = millis() - starttime + total;
  }
}


void RPMreceive (const CAN_message_t &msg)  {
  RPM = (msg.buf[0]<<8)|msg.buf[1];
  TPS = (msg.buf[4]<<8)|msg.buf[5];
}

void AFRreceive (const CAN_message_t &msg)  {
  AFR = (msg.buf[0]<<8)|msg.buf[1];
}

void voltreceive (const CAN_message_t &msg)  {
  volt = (msg.buf[0]<<8)|msg.buf[1];
}

void H20receive (const CAN_message_t &msg)  {
  H2O = (msg.buf[0]<<8)|msg.buf[1];
}
