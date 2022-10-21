#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>
#include "MadgwickAHRS.h"

// https://www.youtube.com/watch?v=BLvYFXoP33o&ab_channel=FemmeVerbeek

// Madgwick
Madgwick filter;
// sensor's sample rate is fixed at 119 Hz:
const float sensorRate = 119;
//const float sensorRate = 100;

bool debugBool = true;
//bool debugBool = false;

float roll, pitch, heading;

// BLE Service
BLEService imuService("917649A0-D98E-11E5-9EEC-0002A5D5C51B"); // Custom UUID

// BLE Characteristic
BLECharacteristic orientCharacteristic("C8F88594-2217-0CA6-8F06-A4270B675D68", BLERead | BLENotify, 24);
BLECharacteristic accelCharacteristic("C8F88594-2217-0CA6-8F06-A4270B675D24", BLERead | BLENotify, 24);
BLECharacteristic gyroCharacteristic("C8F88594-2217-0CA6-8F06-A4270B675D32", BLERead | BLENotify, 24);
BLEIntCharacteristic countCharacteristic( "C8F88594-2217-0CA6-8F06-A4270B675D82", BLERead | BLEWrite );

#define CHAR_DATA_SIZE 12

typedef struct __attribute__( ( packed ) )
{
  float X;
  float Y;
  float Z;
} char_data_t;

typedef union
{
  char_data_t values;
  uint8_t bytes[ CHAR_DATA_SIZE ];
} char_data_ut;

char_data_ut dataOrient;
char_data_ut dataAccel;
char_data_ut dataGyro;

// if a data structure for count is desired
/*
#define CHAR_COUNT_SIZE 4

typedef struct __attribute__( ( packed ) )
{
  int imuCount;
} char_count_t;

typedef union
{
  char_count_t values;
  uint8_t bytes[ CHAR_COUNT_SIZE ];
} char_count_ut;

char_count_ut dataCount;
*/

int imuCount = 0;

long previousMillis = 0;  // last timechecked, in ms
unsigned long micros_per_reading, micros_previous;

bool dataRateSet = false;

void setup() {
  Serial.begin(115200);    // initialize serial communication

  pinMode(LED_BUILTIN, OUTPUT); // initialize the built-in LED pin to indicate when a central is connected

  // begin initialization
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  if (!BLE.begin()) {
    Serial.println("starting BLE failed!");
    while (1);
  }

  // Setup bluetooth
  BLE.setDeviceName("ArduinoIMU");
  BLE.setLocalName("ArduinoIMU");
  BLE.setAdvertisedService(imuService);
  imuService.addCharacteristic(orientCharacteristic);
  imuService.addCharacteristic(accelCharacteristic);
  imuService.addCharacteristic(gyroCharacteristic);
  imuService.addCharacteristic(countCharacteristic);
  
  BLE.addService(imuService);
  
// Temp integration //
//  floatValueCharacteristic.writeValue( floatValue );
//  amplitudeCharacteristic.writeValue( amplitude );
// Temp integration //

  // start advertising
  BLE.advertise();
  Serial.println("Bluetooth device active, waiting for connections...");

  //Accelerometer setup
  IMU.setAccelFS(2);
  IMU.setAccelODR(5);
  IMU.setAccelOffset(0.005545, 0.011194, 0.006048);
  IMU.setAccelSlope (0.992231, 0.975594, 0.968433);
  //Gyrsoscope setup
  IMU.gyroUnit = DEGREEPERSECOND;
  IMU.setGyroFS(2);
  IMU.setGyroODR(5);
  IMU.setGyroOffset (-0.359619, 0.019531, -0.643402);
  IMU.setGyroSlope (1.267381, 1.138717, 1.126608);
  //Mangetometer setupde
  IMU.setMagnetFS(0);
  IMU.setMagnetODR(8);
  IMU.setMagnetOffset(41.749268, 10.369263, 19.472656);
  IMU.setMagnetSlope (1.137004, 1.115131, 1.274473);

  float sensorRate = min(IMU.getGyroODR(),IMU.getMagnetODR());

  if ( debugBool ) {
//    Serial.println("Gyro settting ");  
    Serial.print("Gyroscope FS= ");   Serial.print(IMU.getGyroFS());
    Serial.print("Gyroscope ODR=");   Serial.println(IMU.getGyroODR());
    Serial.print("Gyro unit=");       Serial.println(IMU.gyroUnit);
    Serial.print("SensorRate");       Serial.print(sensorRate);
  }
  
  // The slowest ODR determines the sensor rate, Accel and Gyro share their ODR
  // start the filter to run at the sample rate:
  filter.begin(sensorRate);
 
  //  // or start the filter to run at the set sample rate:
  //  filter.begin(119);
  delay(1000);

  if ( debugBool ) {
    Serial.print("Accelerometer sample rate = ");
    Serial.print(IMU.accelerationSampleRate());
    Serial.println(" Hz");
    Serial.println();
    Serial.println("Acceleration in G's");
    Serial.println("X\tY\tZ");
    Serial.print("Gyroscope sample rate = ");
    Serial.print(IMU.gyroscopeSampleRate());
    Serial.println(" Hz");
    Serial.println();
    Serial.println("Gyroscope in degrees/second");
    Serial.println("X\tY\tZ");
    Serial.print("Magnetic field sample rate = ");
    Serial.print(IMU.magneticFieldSampleRate());
    Serial.println(" uT");
    Serial.println();
    Serial.println("Magnetic Field in uT");
    Serial.println("X\tY\tZ");
  }
  micros_per_reading = 1000000 / 119; // make dynamic to the actual 
  micros_previous = micros();


}

// send IMU data
void sendSensorData() {

  float ax, ay, az; // Acceleration
  float gx, gy, gz; // Gyroscope
  float mx, my, mz; // Magnometer

  // read orientation x, y and z eulers
  IMU.readAcceleration(ax, ay, az);
  IMU.readGyroscope(gx, gy, gz);
  IMU.readMagneticField(mx, my, mz);

  filter.update(gx, gy, gz, ax, ay, az, -mx, my, mz); //for all 3
  roll = filter.getRoll();
  pitch = filter.getPitch();
  heading = filter.getYaw();
  
  if ( debugBool ) {
    Serial.print("Orientation: ");
    Serial.print(heading);
    Serial.print(" ");
    Serial.print(pitch);
    Serial.print(" ");
    Serial.println(roll);
  }
  
  dataOrient.values.X = heading;
  dataOrient.values.Y = pitch;
  dataOrient.values.Z = roll;
  orientCharacteristic.writeValue( dataOrient.bytes, sizeof dataOrient.bytes);

  dataAccel.values.X = ax;
  dataAccel.values.Y = ay;
  dataAccel.values.Z = az;
  accelCharacteristic.writeValue( dataAccel.bytes, sizeof dataAccel.bytes);

  dataGyro.values.X = gx;
  dataGyro.values.Y = gy;
  dataGyro.values.Z = gz;
  gyroCharacteristic.writeValue( dataGyro.bytes, sizeof dataGyro.bytes);
}

void loop() {
  // wait for a BLE central
  BLEDevice central = BLE.central();

  // if a BLE central is connected to the peripheral:
  if (central) {
    if ( debugBool ) {
      Serial.print("Connected to central: ");
      // print the central's BT address:
      Serial.println(central.address());
      // turn on the LED to indicate the connection:
    }
    
    digitalWrite(LED_BUILTIN, HIGH);

  
    // while the central is connected:
    while (central.connected()) {
      if ( dataRateSet == false ){
        if ( countCharacteristic.written() ){
          int count;
          count = countCharacteristic.value();
          int rate_per_board = 100 / count;

          micros_per_reading = 1000000 / rate_per_board;
          if ( debugBool ) {
            Serial.print("rate_per_board: ");
            Serial.println(rate_per_board);
            Serial.print("micros_per_reading: ");
            Serial.println(micros_per_reading);
          }
          dataRateSet = true;
        }
      } else {
        unsigned long micros_now;
        micros_now = micros();
        if (micros_now - micros_previous >= micros_per_reading) {
          if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable() && IMU.magneticFieldAvailable()) { // XX
            sendSensorData();
//            micros_previous = micros_previous + micros_per_reading;
            micros_previous = micros_now;

            if ( debugBool ) {
              Serial.print("micros_per_reading: ");
              Serial.println(micros_per_reading);
            }
          }
        }
      }
    }
    
    // when the central disconnects, turn off the LED:
    digitalWrite(LED_BUILTIN, LOW);
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }
}
