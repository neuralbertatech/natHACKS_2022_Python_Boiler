/**
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

#include <Adafruit_SensorLab.h>
#include <Adafruit_Sensor_Calibration.h>
#include <Adafruit_AHRS.h>

// pick your filter! slower == better quality output
Adafruit_NXPSensorFusion filter; // slowest
//Adafruit_Madgwick filter;  // faster than NXP
//Adafruit_Mahony filter;  // fastest

// CONSTANTS
#define FILTER_UPDATE_RATE_HZ 10 // 100

#define DEVICE_ADDRESS "02:00:00:00:00:00:00:02"

#define CHAR_DATA_SIZE 36

uint32_t timestamp;

Adafruit_SensorLab lab;
Adafruit_Sensor *accelerometer, *gyroscope, *magnetometer;

#if defined(ADAFRUIT_SENSOR_CALIBRATION_USE_EEPROM)
  Adafruit_Sensor_Calibration_EEPROM cal;
#else
  Adafruit_Sensor_Calibration_SDFat cal;
#endif

typedef struct __attribute__( ( packed ) )
{
  float aX;
  float aY;
  float aZ;
  float gX;
  float gY;
  float gZ;
  float roll;
  float pitch;
  float heading;
} char_data_t;

typedef union
{
  char_data_t values;
  uint8_t bytes[ CHAR_DATA_SIZE ];
} char_data_ut;

char_data_ut dataTrans;

// CONSTANTS
// The tag will update a server with its location information
// allowing it to be remotely tracked
// Wi-Fi credentials 

 const char * ssid = "NETGEAR87";
 const char * password = "7856@TasqeuP";

//const char * ssid = "CISSSLAV-Recherche";
//const char * password = "Re3s3arch-2021$";
const char *host = "192.168.1.33";
uint16_t portNum = 3333; //50000;

WiFiUDP udp;

unsigned long lastUpdateTime = 0; // Timestamp at which updated data was last broadcast
//unsigned int updateInterval = 200; // Time interval (in ms) between updates
unsigned int imuIndex = 1;

void setup() {

  // Initialise serial connection for debugging  
  Serial.begin(115200);
  Serial.println(__FILE__ __DATE__);

  Serial.println(F("Sensor Lab - IMU AHRS!"));
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

  filter.begin(FILTER_UPDATE_RATE_HZ);
  timestamp = millis();

  Wire.setClock(400000); // 400KHz
  
  // Start a Wi-Fi connection to update host with tag's location
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
  delay(500); // Short pause before starting main loop
  udp.begin(50000); // Start the UDP interface
}

void loop() {
  if((millis() - lastUpdateTime) > (1000 / FILTER_UPDATE_RATE_HZ)){
    //float roll, pitch, heading;
    float gx, gy, gz;
    
    // Read the motion sensors
    sensors_event_t accel, gyro, mag;
    accelerometer->getEvent(&accel);
    gyroscope->getEvent(&gyro);
    magnetometer->getEvent(&mag);
    //Serial.print("I2C took "); Serial.print(millis()-timestamp); Serial.println(" ms");
  
    cal.calibrate(mag);
    cal.calibrate(accel);
    cal.calibrate(gyro);
        
    // Gyroscope needs to be converted from Rad/s to Degree/s
    // the rest are not unit-important
    gx = gyro.gyro.x * SENSORS_RADS_TO_DPS;
    gy = gyro.gyro.y * SENSORS_RADS_TO_DPS;
    gz = gyro.gyro.z * SENSORS_RADS_TO_DPS;
  
    // Update the SensorFusion filter
    filter.update(gx, gy, gz, 
                  accel.acceleration.x, accel.acceleration.y, accel.acceleration.z, 
                  mag.magnetic.x, mag.magnetic.y, mag.magnetic.z);
    //Serial.print("Update took "); Serial.print(millis()-timestamp); Serial.println(" ms");

    dataTrans.values.aX = accel.acceleration.x;
    dataTrans.values.aY = accel.acceleration.y;
    dataTrans.values.aZ = accel.acceleration.z;

    dataTrans.values.gX = gx;
    dataTrans.values.gY = gy;
    dataTrans.values.gZ = gz;

    dataTrans.values.roll = filter.getRoll();
    dataTrans.values.pitch = filter.getPitch();
    dataTrans.values.heading = filter.getYaw();
    
    DynamicJsonDocument doc(1024);
    
    doc["id"] = imuIndex;
    doc["aX"] = dataTrans.values.aX;
    doc["aY"] = dataTrans.values.aY; 
    doc["aZ"] = dataTrans.values.aZ;
    
    doc["gX"] = dataTrans.values.gX;
    doc["gY"] = dataTrans.values.gY; 
    doc["gZ"] = dataTrans.values.gZ;
    
    doc["roll"] = dataTrans.values.roll;
    doc["pitch"] = dataTrans.values.pitch; 
    doc["heading"] = dataTrans.values.heading;
    
    // Send JSON to serial connection
    //serializeJson(doc, Serial);
    //Serial.println("");
  
    // Send JSON over UDP
    udp.beginPacket(host, portNum);
    serializeJson(doc, udp);
    udp.println();
    udp.endPacket();

    // Update the timestamp
    lastUpdateTime = millis();
//    dataTrans.values.aY = dataTrans.values.Y + 0.001;
  }
}
