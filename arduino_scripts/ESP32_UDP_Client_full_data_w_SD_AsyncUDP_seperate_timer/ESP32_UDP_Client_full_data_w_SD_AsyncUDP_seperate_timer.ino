/*
 * 
 */

//// CONSTANTS
//#define UPDATE_RATE_HZ 10 // 100
//#define USE_ASYNC_UDP false
#define ORIENT false
#define SEND_SAMPLES false // true
#define JSON false
#define DEBUG true
#define CALIBRATE false

// Libraries for SD card
#include <FS.h>
#include <SD.h>
#include <SPI.h>

// Libraries for Comms
#include <WiFi.h>
#include <AsyncUDP.h>
#include <ArduinoJson.h>

//Libraries for IMU
#include <Adafruit_SensorLab.h>
#include <Adafruit_Sensor_Calibration.h>
#include <Adafruit_AHRS.h>

String dataMessage;

Adafruit_SensorLab lab;
Adafruit_Sensor *accelerometer, *gyroscope, *magnetometer;

#if defined(ADAFRUIT_SENSOR_CALIBRATION_USE_EEPROM)
  Adafruit_Sensor_Calibration_EEPROM cal;
#else
  Adafruit_Sensor_Calibration_SDFat cal;
#endif

// Montreal
const char * ssid = "R12-253D";
const char * password = "qpjcp67647";
const char *host = "192.168.0.148";

//// Verdun
//const char * ssid = "NETGEAR87";
//const char * password = "7856@TasqeuP";
//const char *host = "192.168.1.33";

//// natFlat
//const char * ssid = "R12-2552";
//const char * password = "qudfq89869";
//const char *host = "192.168.0.148";

//// JRH - buggy
//const char * ssid = "CISSSLAV-Recherche";
//const char * password = "Re3s3arch-2021$";

uint16_t portNum = 3333; // this should be 333x where x = number on IMU case

bool trigReceived = false;

float gx, gy, gz;
float ax, ay, az;
float mx, my, mz;

float roll, pitch, heading;
// pick your filter! slower == better quality output
Adafruit_NXPSensorFusion filter; // slowest
//Adafruit_Madgwick filter;  // faster than NXP
//Adafruit_Mahony filter;  // fastest

int mainState; // NULL = setup not run, 0 = systems ready, 1 = started, 2 = done saving serve data
unsigned long sampleCount = 0;
unsigned long waitCount = 0;

AsyncUDP udp;

unsigned long lastUpdateTime = 0; // Timestamp at which updated data was last broadcast
unsigned int imuIndex = 1;
unsigned long sensorReadTime = 0;
//int trigNum = 0;

// Init command variables
char fileName[10] = "/0000.txt";
int returnFreq;
int samplingRate;
int idleRate = 100;

// Trig command variable
char curTrig[5] = "0000";
char defaultTrig[5] = "0000";

char replyPacket[] = "Hi there! Got the message :-)";  // a reply string to send back
char incomingPacket[255];  // buffer for incoming packets

char curPacket[120];
//String curPacket;

bool initCmdProcessed = false;

File appendFile; // globally accessible File object - later init for appending 
bool fileClosed = false;

//// Functions ////
// Initialize WiFi
void initWifi(){
  WiFi.mode(WIFI_STA);
//  WiFi.setSleep(false);
  WiFi.begin(ssid, password);
  
//  while (WiFi.status() != WL_CONNECTED) {
//    delay(500);
//    Serial.print(".");
//  }

  if (WiFi.waitForConnectResult() != WL_CONNECTED) {
      Serial.println("WiFi Failed");
      while(1) {
          delay(1000);
      }
  }

  if(udp.listen(portNum)) {
    Serial.print("UDP Listening on IP:");
    Serial.println(WiFi.localIP());

    udp.onPacket([](AsyncUDPPacket packet) {
      Serial.print("UDP Packet Type: ");
      Serial.print(packet.isBroadcast()?"Broadcast":packet.isMulticast()?"Multicast":"Unicast");
      Serial.println(", From: ");
      Serial.print(packet.remoteIP());
      Serial.print(":");
      Serial.print(packet.remotePort());
      Serial.println(", To: ");
      Serial.print(packet.localIP());
      Serial.print(":");
      Serial.print(packet.localPort());
      Serial.println(", Length: ");
      Serial.print(packet.length());
      Serial.println(", Data: ");
      Serial.write(packet.data(), packet.length());
      Serial.println();
      //reply to the client
      packet.printf("Got %u bytes of data", packet.length());
  
      // init command       :   4000, fileName, samplingRate,  returnFreq
      //                    ex. 4000,     1000,          100,           10
  
      // start command      :   5000,        0,           0,           0
      //                    ex. 5000,        0,           0,           0
  
      // trigger command    :   6000,  curTrig,           0,            0  
      //                    ex. 6000,     0006,           0,            0   
      
      // save command       :   7000,        0,           0,            0 
      // 
  
      char* curData = (char*)packet.data();
  
      int cmdCode = atoi(strtok(curData, ","));

      if (cmdCode == 4000){
        sprintf(fileName,"/%s.txt",strtok(NULL, ","));
        samplingRate = atoi(strtok(NULL, ","));
        returnFreq = atoi(strtok(NULL, ","));
        packet.printf("Command %u recieved, fileName set to %s, sample rate set to %u, every %u th will be sent back.", cmdCode, fileName, samplingRate, returnFreq);
        mainState = 1;
        Serial.println(String("mainState changed to: ") + String(mainState));
      } else if (cmdCode == 5000){
        mainState = 2;
        Serial.println(String("mainState changed to: ") + String(mainState));
        packet.printf("Command %u recieved, MCU is about to start saving data", cmdCode);
      } else if (cmdCode == 6000){
        sprintf(curTrig,"%s",strtok(NULL, ","));
        trigReceived = true;
        packet.printf("Command %u recieved, trig # %s injected into IMU stream", cmdCode, curTrig);
      } else if (cmdCode == 7000){
        mainState = 3;
        packet.printf("Command %u recieved, stopping IMU sampling and uploading files via FTP", cmdCode);
        Serial.println(String("mainState changed to: ") + String(mainState));
//      } else if (cmdCode == 8000){
// needs to be another command that initiates the data transfer over FTP
      
      
      } else {
        packet.printf("Command %u recieved, invalid command", cmdCode);
      }
    });
  }
}

// init IMU
void initIMU(){
  lab.begin();

  if (!cal.begin()) {
    Serial.println("Failed to initialize calibration helper");
  } else if (!cal.loadCalibration()) {
    Serial.println("No calibration loaded/found");
  }
  
  Serial.println("Looking for a magnetometer");
  magnetometer = lab.getMagnetometer();
  if (!magnetometer) {
    Serial.println(F("Could not find a magnetometer!"));
    while (1) yield();
  }
  
  Serial.println("Looking for a gyroscope");
  gyroscope = lab.getGyroscope();
  if (!gyroscope) {
    Serial.println(F("Could not find a gyroscope!"));
    while (1) yield();
  }
  
  Serial.println("Looking for a accelerometer");
  accelerometer = lab.getAccelerometer();
  if (!accelerometer) {
    Serial.println(F("Could not find a accelerometer!"));
    while (1) yield();
  }
  
  accelerometer->printSensorDetails();
  gyroscope->printSensorDetails();
  magnetometer->printSensorDetails();

  if (ORIENT){
    filter.begin(samplingRate);
  }
  
  Wire.setClock(400000); // 400KHz
}

////////////////////////
// Initialize SD card //
void initSD(){
   if (!SD.begin()) {
    Serial.println("Card Mount Failed");
    return;
  }
  uint8_t cardType = SD.cardType();

  if(cardType == CARD_NONE){
    Serial.println("No SD card attached");
    return;
  }

  uint64_t cardSize = SD.cardSize() / (1024 * 1024);
  Serial.printf("SD Card Size: %lluMB\n", cardSize);
}

// Write to the SD card
void writeFile(fs::FS &fs, const char * path, const char * message) {
  Serial.printf("Writing file: %s\n", path);

  File file = fs.open(path, FILE_WRITE);
  if(!file) {
    Serial.println("Failed to open file for writing");
    return;
  }
  if(file.print(message)) {
    Serial.println("File written");
  } else {
    Serial.println("Write failed");
  }
  file.close();
}

void initSaving(){
  // If the file w/ name "fileName" doesn't exist - Create a file on the SD card and write the data labels
  // -------------- need to add in a delete file if it does exist instead - need to be sure we aren't just appending to an old --------- //
  // https://forum.arduino.cc/t/while-not-working-as-expected-for-incrementing-sd-file-name/1035297 
  File file = SD.open(fileName);
  if(!file) {
    Serial.println("File doesn't exist");
    Serial.println("Creating file...");
    if (!ORIENT){
      writeFile(SD, fileName, "sampleCount, trigNum, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz \n");
    } else {
      writeFile(SD, fileName, "sampleCount, trigNum, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz, roll, pitch, heading \n");
    }
  }
  else {
    Serial.println("File already exists");  
    // add a portion to change the filename and try again
  }
  file.close();

  appendFile = SD.open(fileName, FILE_APPEND);
}

void readSensor(){
    if (DEBUG) {
      Serial.println(String("DEBUG #101-1: ") + String(millis()- lastUpdateTime));
    }
    
    // Read the motion sensors
    sensors_event_t accel, gyro, mag;
    accelerometer->getEvent(&accel);
    gyroscope->getEvent(&gyro);
    magnetometer->getEvent(&mag);

    if (CALIBRATE){
      cal.calibrate(mag);
      cal.calibrate(accel);
      cal.calibrate(gyro);
    }

    // Gyroscope needs to be converted from Rad/s to Degree/s
    // the rest are not unit-important
    gx = gyro.gyro.x * SENSORS_RADS_TO_DPS;
    gy = gyro.gyro.y * SENSORS_RADS_TO_DPS;
    gz = gyro.gyro.z * SENSORS_RADS_TO_DPS;

    ax = accel.acceleration.x;
    ay = accel.acceleration.y;
    az = accel.acceleration.z;

    mx = mag.magnetic.x;
    my = mag.magnetic.y;
    mz = mag.magnetic.z;

    if (ORIENT){
      // Update the SensorFusion filter
      filter.update(gx, gy, gz, 
                    ax, ay, az, 
                    mx, my, mz);
  
      roll = filter.getRoll();
      pitch = filter.getPitch();
      heading = filter.getYaw();
    }
    
    if (DEBUG) {
      Serial.println(String("DEBUG #101-2: ") + String(millis()- lastUpdateTime));
    }
}

void sendJsonPacket(){
    DynamicJsonDocument doc(1024);
    doc["sampleCount"] = sampleCount;
    doc["trigNum"] = curTrig;
    doc["sensorReadTime"] = sensorReadTime;
    doc["aX"] = ax; doc["aY"] = ay; doc["aZ"] = az;
    doc["gX"] = gx; doc["gY"] = gy; doc["gZ"] = gz;
    doc["mX"] = mx; doc["mY"] = my; doc["mZ"] = mz;

    if (ORIENT){
      doc["roll"] = roll; doc["pitch"] = pitch; doc["heading"] = heading;
    }
    
    // Send JSON over UDP
//    udp.beginPacket(host, portNum);
    serializeJson(doc, udp);
//    udp.println();
//    udp.endPacket();
}

void sendPacket(){
    if (DEBUG) {
      Serial.println(String("DEBUG #100-1: ") + String(millis()- lastUpdateTime));
    }
    if (!ORIENT){
//      int curPacket_len = sprintf(curPacket,"%lu;%s;%lu;%f;%f;%f;%f;%f;%f;%f;%f;%f;", sampleCount, curTrig, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz);
      int curPacket_len = sprintf(curPacket,"%lu;%s;%lu;%f;%f;%f;%f;%f;%f;%f;%f;%f;", sampleCount, curTrig, lastUpdateTime, ax, ay, az, gx, gy, gz, mx, my, mz);

      Serial.println(curPacket_len);
    } else {
//      int curPacket_len = sprintf(curPacket,"%lu;%s;%lu;%f;%f;%f;%f;%f;%f;%f;%f;%f;%f,%f;%f;", sampleCount, curTrig, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz, roll, pitch, heading);
      int curPacket_len = sprintf(curPacket,"%lu;%s;%lu;%f;%f;%f;%f;%f;%f;%f;%f;%f;%f,%f;%f;", sampleCount, curTrig, lastUpdateTime, ax, ay, az, gx, gy, gz, mx, my, mz, roll, pitch, heading);

      Serial.println(curPacket_len);
    }
  udp.broadcast(curPacket);

  if (DEBUG) {
    Serial.println(String("DEBUG #100-2: ") + String(millis()- lastUpdateTime));
  }
}

void saveSample(){
    if (DEBUG) {
      Serial.println(String("DEBUG #103-1: ") + String(millis()- lastUpdateTime));
    }
    // Concatenate all info separated by commas
    if (!ORIENT){
//      dataMessage = String(sampleCount) + "," + String(curTrig) + "," + String(sensorReadTime) + "," + String(ax) + "," + String(ay) + "," + String(az)+ "," + String(gx) + "," + String(gy) + "," + String(gz) + "," + String(mx) + "," + String(my) + "," + String(mz) + "\r\n";
      dataMessage = String(sampleCount) + "," + String(curTrig) + "," + String(lastUpdateTime) + "," + String(ax) + "," + String(ay) + "," + String(az)+ "," + String(gx) + "," + String(gy) + "," + String(gz) + "," + String(mx) + "," + String(my) + "," + String(mz) + "\r\n";
    } else {
//      dataMessage = String(sampleCount) + "," + String(curTrig) + "," + String(sensorReadTime) + "," + String(ax) + "," + String(ay) + "," + String(az)+ "," + String(gx) + "," + String(gy) + "," + String(gz) + "," + String(mx) + "," + String(my) + "," + String(mz) + "," + String(roll) + "," + String(pitch) + "," + String(heading) + "\r\n";
      dataMessage = String(sampleCount) + "," + String(curTrig) + "," + String(lastUpdateTime) + "," + String(ax) + "," + String(ay) + "," + String(az)+ "," + String(gx) + "," + String(gy) + "," + String(gz) + "," + String(mx) + "," + String(my) + "," + String(mz) + "," + String(roll) + "," + String(pitch) + "," + String(heading) + "\r\n";
    } 
    // Append the data to file -------- need to change so it stays open and append doesn't have to open each call
    // appendFile(SD, fileName, dataMessage.c_str());

    // Save
    if(appendFile.print(dataMessage.c_str())) {
//      Serial.println("Message appended");
    } else {
      Serial.println("Append failed");
    }
    if (DEBUG) {
      Serial.println(String("DEBUG #103-2: ") + String(millis()- lastUpdateTime));
    }
}

void setup() {
  Serial.begin(115200);
  initWifi();
  initSD();
  mainState = 0; // ready for first contact
}

void loop() {
  // might need to change to a microsecond timer
  // to do - move all the prints to a single loop
//  Serial.println("DEBUG 0");

  // define all the idle states - need a different loop speed 
  if (mainState == 0 || mainState == 1 || mainState == 3){ 
//    Serial.println("DEBUG 1");

    if((millis() - lastUpdateTime) >= (1000 / idleRate)){ 
      Serial.println(String("Time past since last idle update ") + String(millis() - lastUpdateTime) + String(" is greater than ") + String(1000 / idleRate) + String(" : ") + String((millis() - lastUpdateTime) > (1000 / idleRate)));
      Serial.println(String("lastUpdateTime: ") + String(lastUpdateTime));

//      Serial.println(String("Time past mainState pacemaker") + String(lastUpdateTime) + String(" DEBUG 3, mainState: ") + String(mainState));
      if (mainState == 0){
        // idle cross talk to PC
        if (waitCount % (idleRate*10) == 0){
          Serial.println("mainState is 0, ready to recieve init command");
          udp.broadcast("mainState is 0, ready to recieve init command");
        }

      // once we have recived command - setup the IMU + saving 
      // question - can we shutdown imu + re-init saving a second time without resetting
      } else if (mainState == 1){
//        Serial.println(String("DEBUG 4, mainState: ") + String(mainState));
        if (!initCmdProcessed){
          Serial.println("initIMU begin");
          initIMU(); // here because need to wait for sampleRate 
          Serial.println("initSaving begin");
          initSaving(); // here because need to wait for fileName 
          initCmdProcessed = true;
        }
        // idle cross talk to PC
        if (waitCount % (idleRate*10) == 0){
          Serial.println("mainState is 1, ready to start saving");
          udp.broadcast("mainState is 1, ready to start saving");
        }

      // Close file, FTP to PC
      } else if (mainState == 3){
//        Serial.println(String("DEBUG 5, mainState: ") + String(mainState));

        if (!fileClosed){
          Serial.println("mainState is 3, about to close file, then start data transfer");
          appendFile.close(); // failure to close means the data won't be saved properly
          fileClosed = true;
          Serial.println("File closed");
        }
        // idle cross talk to PC
        if (waitCount % (idleRate*10) == 0){
          Serial.println("mainState is 3");
          udp.broadcast("mainState is 3");
        }
      }
      waitCount += 1;
//      Serial.println(String("waitCount: ") + String(waitCount));
      lastUpdateTime = millis(); // Update the timestamp for main loop - move this to the top
    }
    
  // saving mode
  } else if (mainState == 2){
    if((millis() - lastUpdateTime) >= ((1000 / samplingRate) - 1)){ // need to try changing to 125 - to get accurate 100 sampling. 
      if (DEBUG){
        Serial.println(String("lastUpdateTime: ") + String(lastUpdateTime));
//        Serial.println(String("Time past since last sample update ") + String(millis() - lastUpdateTime) + String(" is greater than ") + String(1000 / samplingRate) + String(" is ") + String((millis() - lastUpdateTime) > ((1000 / samplingRate)-1)));
        Serial.println(String("DEBUG #99: ") + String(millis()));
//      Serial.println(String("lastUpdateTime: ") + String(lastUpdateTime));
//      Serial.println(String("Time past mainState pacemaker") + String(lastUpdateTime) + String(" DEBUG 6, mainState: ") + String(mainState) + String(" samplingRate: ") + String(samplingRate));
      }
      readSensor();
      // Serial.println("Pre save millisecond time: " + String(sensorReadTime));
      saveSample();
      // for the next saved line, let's reset the trigger to default
      if (trigReceived){ // event marker
        strcpy(curTrig, defaultTrig);
        trigReceived = false;
        Serial.println("DEBUG #104");

      }
      // if we are sending sample at the current count freq, send back
      if (SEND_SAMPLES){
        if (sampleCount % returnFreq == 0){
          if (!JSON){
            sendPacket();
          } else {
            sendJsonPacket();
          }
        }
      }
      sampleCount += 1;
      lastUpdateTime = millis(); // Update the timestamp for main loop - move this to the top
    }
  }
  // update main loop time 
//  lastUpdateTime = millis(); // Update the timestamp for main loop - move this to the top
}
