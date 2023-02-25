/**
 * 
 */

// CONSTANTS
#define UPDATE_RATE_HZ 10 // 100
#define USE_ASYNC_UDP false
#define ORIENT true
#define JSON true
#define DEBUG_BOOL true
#define CALIBRATE false

// Libraries for SD card
#include <FS.h>
#include <SD.h>
#include <SPI.h>

// Libraries for Comms
#include <WiFi.h>
#if USE_ASYNC_UDP
  #include <AsyncUDP.h>
#else
  #include <WiFiUdp.h>
#endif
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

//// Verdun
const char * ssid = "NETGEAR87";
const char * password = "7856@TasqeuP";
const char *host = "192.168.1.33";

//// Verdun
//const char * ssid = "NETGEAR87-5G-2";
//const char * password = "7856@TasqeuP";
//const char *host = "192.168.1.9";

//// natFlat
//const char * ssid = "R12-2552";
//const char * password = "qudfq89869";
//const char *host = "192.168.0.148";

// Montreal
//const char * ssid = "R12-253D";
//const char * password = "qpjcp67647";
//const char *host = "192.168.0.148";

//// JRH - buggy
//const char * ssid = "CISSSLAV-Recherche";
//const char * password = "Re3s3arch-2021$";

uint16_t portNum = 3333; // this should be 333x where x = number on IMU case

bool trigReceived = false;
int curTrig = 0;

float gx, gy, gz;
float ax, ay, az;
float mx, my, mz;

#if ORIENT
  float roll, pitch, heading;
  // pick your filter! slower == better quality output
  Adafruit_NXPSensorFusion filter; // slowest
  //Adafruit_Madgwick filter;  // faster than NXP
  //Adafruit_Mahony filter;  // fastest
#endif

int mainState; // NULL = setup not run, 0 = systems ready, 1 = started, 2 = done saving serve data
unsigned long sampleCount = 0;

WiFiUDP udp;

unsigned long lastUpdateTime = 0; // Timestamp at which updated data was last broadcast
unsigned int imuIndex = 1;
unsigned sensorReadTime = 0;
int trigNum = 0;

char filename[] = "/0001.txt";

char replyPacket[] = "Hi there! Got the message :-)";  // a reply string to send back
char incomingPacket[255];  // buffer for incoming packets

//// Functions ////
// Initialize WiFi
void initWifi(){
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println(F("Connected"));
  Serial.print(F("IP Address:"));
  Serial.println(WiFi.localIP());
  udp.begin(portNum); // Start the UDP interface
}

// init IMU
void initIMU(){
  // Initialise serial connection for debugging  
  Serial.begin(115200);
  //Serial.println(__FILE__ __DATE__);

  lab.begin();

  if (!cal.begin()) {
    Serial.println("Failed to initialize calibration helper");
  } else if (! cal.loadCalibration()) {
    Serial.println("No calibration loaded/found");
  }
  
  Serial.println("Looking for a magnetometer");
  magnetometer = lab.getMagnetometer();
  if (! magnetometer) {
    Serial.println(F("Could not find a magnetometer!"));
    while (1) yield();
  }
  
  Serial.println("Looking for a gyroscope");
  gyroscope = lab.getGyroscope();
  if (! gyroscope) {
    Serial.println(F("Could not find a gyroscope!"));
    while (1) yield();
  }
  
  Serial.println("Looking for a accelerometer");
  accelerometer = lab.getAccelerometer();
  if (! accelerometer) {
    Serial.println(F("Could not find a accelerometer!"));
    while (1) yield();
  }
  
  accelerometer->printSensorDetails();
  gyroscope->printSensorDetails();
  magnetometer->printSensorDetails();

  if (ORIENT){
    filter.begin(UPDATE_RATE_HZ);
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
  Serial.print("SD Card Type: ");
  if(cardType == CARD_MMC){
    Serial.println("MMC");
  } else if(cardType == CARD_SD){
    Serial.println("SDSC");
  } else if(cardType == CARD_SDHC){
    Serial.println("SDHC");
  } else {
    Serial.println("UNKNOWN");
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

// Append data to the SD card
void appendFile(fs::FS &fs, const char * path, const char * message) {
  Serial.printf("Appending to file: %s\n", path);

  File file = fs.open(path, FILE_APPEND);
  if(!file) {
    Serial.println("Failed to open file for appending");
    return;
  }
  if(file.print(message)) {
    Serial.println("Message appended");
  } else {
    Serial.println("Append failed");
  }
  file.close();
}

void initSaving(){
  // If the file w/ name "filename" doesn't exist - Create a file on the SD card and write the data labels
  // -------------- need to add in a delete file if it does exist instead - need to be sure we aren't just appending to an old --------- //
  // https://forum.arduino.cc/t/while-not-working-as-expected-for-incrementing-sd-file-name/1035297 
  File file = SD.open(filename);
  if(!file) {
    Serial.println("File doesn't exist");
    Serial.println("Creating file...");
    if (!ORIENT){
      writeFile(SD, filename, "sampleCount, trigNum, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz");
    } else {
      writeFile(SD, filename, "sampleCount, trigNum, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz, roll, pitch, heading");
    }
  }
  else {
    Serial.println("File already exists");  
  }
  file.close();
}

void readSensor(){
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
   
    sensorReadTime = millis();
}

void sendJsonPacket(){
    DynamicJsonDocument doc(1024);
    doc["sampleCount"] = sampleCount;
    doc["trigNum"] = trigNum;
    doc["sensorReadTime"] = sensorReadTime;
    doc["aX"] = ax; doc["aY"] = ay; doc["aZ"] = az;
    doc["gX"] = gx; doc["gY"] = gy; doc["gZ"] = gz;
    doc["mX"] = mx; doc["mY"] = my; doc["mZ"] = mz;

    if (ORIENT){
      doc["roll"] = roll; doc["pitch"] = pitch; doc["heading"] = heading;
    }
    
    // Send JSON over UDP
    udp.beginPacket(host, portNum);
    serializeJson(doc, udp);
    udp.println();
    udp.endPacket();
}

void sendPacket(){
    udp.beginPacket(host, portNum);
    if (!ORIENT){
      udp.printf("%lu;%u;%lu;%f;%f;%f;%f;%f;%f;%f;%f;%f;", sampleCount, trigNum, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz);
    } else {
      udp.printf("%lu;%u;%lu;%f;%f;%f;%f;%f;%f;%f;%f;%f;%f,%f;%f;", sampleCount, trigNum, sensorReadTime, ax, ay, az, gx, gy, gz, mx, my, mz, roll, pitch, heading);
    }
    udp.endPacket();
}

void saveSample(){
    //Concatenate all info separated by commas
    dataMessage = String(ax) + "," + String(ay) + "," + String(az)+ "," + String(gx) + "," + String(gy) + "," + String(gz) + "," + String(mx) + "," + String(my) + "," + String(mz) + "\r\n";
//    Serial.print("Saving data: ");
//    Serial.println(dataMessage);

    // Append the data to file -------- need to change so it stays open and append doesn't have to open each call
    appendFile(SD, filename, dataMessage.c_str());
}


////// The behaviour of the AsynchUDP should depend on the central state variable
////// That determines the expected format of data to be send/recieving 

////// behaviour for AsynchUDP handling connection status request /////////////
/*
 * receive string starting with "9000"   
 * send back string of "9001"
 */
////// behaviour for AsynchUDP start command /////////////
/* - change local filename - https://www.tutorialspoint.com/replace-characters-in-a-string-in-arduino#:~:text=The%20.,new%20string%20containing%20the%20changes.
 * receive string starting with "5000" // eventually add in filename ("0000", sampling rate, nth sampling being served back to server 
 * set centralState = 1; // this should begin the sampling of imu + saving to / receiving 
 * 
 */

////// behaviour for AsynchUDP handling trig /////////////

/*
 * receive string starting with "9000"  
 * set curTrig to the value of trig
 * set trigReceived = true;
 * send back string starting w
 */

void setup() {
  initWifi();
  initIMU();
  initSD();
  mainState = 0; // ready for first contact
}

void loop() {
  if((millis() - lastUpdateTime) > (1000 / UPDATE_RATE_HZ)){
    if (mainState == 0){
      udp.beginPacket(host, portNum);
      udp.printf(replyPacket);
      udp.endPacket();

      int packetSize = udp.parsePacket();
      if (packetSize){
        // receive incoming UDP packets
        Serial.printf("Received %d bytes from %s, port %d\n", packetSize, udp.remoteIP().toString().c_str(), udp.remotePort());
        int len = udp.read(incomingPacket, 255);
        if (len > 0)
        {
          incomingPacket[len] = 0;
        }
        Serial.printf("UDP packet contents: %s\n", incomingPacket);
    
        // send back a reply, to the IP address and port we got the packet from
        udp.beginPacket(udp.remoteIP(), udp.remotePort());
        udp.printf(replyPacket);
        udp.endPacket();
      }
      
    } else if (mainState == 1){
      readSensor();
  
      if (trigReceived){
        trigNum = curTrig;
        trigReceived = false;
      }
  
      if (!JSON){
        sendPacket();
      } else {
        sendJsonPacket();
      }
  
      saveSample();
  
      trigNum = 0;
    }
    
    // Update the timestamp for main loop
    lastUpdateTime = millis();
  }
}
