/*
  This example creates a BLE central that scans for a peripheral with a Test Service
  If that contains floatValue characteristics the value can be seen in the Serial Monitor or Plotter.

  The circuit:
  - Arduino Nano 33 BLE or Arduino Nano 33 IoT board.

  This example code is in the public domain.
*/

#include <ArduinoBLE.h>

//----------------------------------------------------------------------------------------------------------------------
// BLE UUIDs
//----------------------------------------------------------------------------------------------------------------------

#define BLE_UUID_IMU_SERVICE               "917649A0-D98E-11E5-9EEC-0002A5D5C51B"
#define BLE_UUID_ORIENT                  "C8F88594-2217-0CA6-8F06-A4270B675D68"
#define BLE_UUID_ACCEL                   "C8F88594-2217-0CA6-8F06-A4270B675D24"
#define BLE_UUID_GYRO                    "C8F88594-2217-0CA6-8F06-A4270B675D32"
#define BLE_UUID_COUNT                     "C8F88594-2217-0CA6-8F06-A4270B675D82"

#define BLE_CHAR_NUM 3
#define BLE_MAX_PERIPHERALS 2
#define BLE_SCAN_INTERVALL 10000

#define FLOAT_BYTES 4
#define CHAR_DATA_SIZE 12

BLEDevice peripherals[BLE_MAX_PERIPHERALS];
BLECharacteristic orientCharacteristics[BLE_MAX_PERIPHERALS];
BLECharacteristic accelCharacteristics[BLE_MAX_PERIPHERALS];
BLECharacteristic gyroCharacteristics[BLE_MAX_PERIPHERALS];
BLECharacteristic countCharacteristics[BLE_MAX_PERIPHERALS];
int peripheralsConnected = 0;

bool orientUpdate[BLE_MAX_PERIPHERALS];
bool accelUpdate[BLE_MAX_PERIPHERALS];
bool gyroUpdate[BLE_MAX_PERIPHERALS];

//bool debugBool = true;
bool debugBool = false;

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

char_data_ut dataOrient[BLE_MAX_PERIPHERALS];
char_data_ut dataAccel[BLE_MAX_PERIPHERALS];
char_data_ut dataGyro[BLE_MAX_PERIPHERALS];

const int BLE_LED_PIN = LED_BUILTIN;
const int BLE_SCAN_LED_PIN = LED_BUILTIN;

short info[2] = { 0, 0 };

void setup()
{
  Serial.begin( 9600 );
  while ( !Serial ); // waits for serial connect before continuing

  if ( debugBool ) {
    Serial.println("Serial is initialized");
  }
  
  pinMode( BLE_SCAN_LED_PIN, OUTPUT );

  BLE.begin();

  digitalWrite( BLE_SCAN_LED_PIN, HIGH );
  BLE.scanForUuid( BLE_UUID_IMU_SERVICE );

  int peripheralCounter = 0;
  unsigned long startMillis = millis();
  while ( millis() - startMillis < BLE_SCAN_INTERVALL && peripheralCounter < BLE_MAX_PERIPHERALS )
  {
    BLEDevice peripheral = BLE.available();

    if ( peripheral )
    {
      if ( peripheral.localName() == "ArduinoIMU" )
      {
        if ( debugBool ) {
          Serial.println(peripheral.address());
        }
        boolean peripheralAlreadyFound = false;
        for ( int i = 0; i < peripheralCounter; i++ )
        {
          if ( peripheral.address() == peripherals[i].address() )
          {
            peripheralAlreadyFound = true;
          }
        }
        if ( !peripheralAlreadyFound )
        {
          peripherals[peripheralCounter] = peripheral;
          peripheralCounter++;
        }
      }
    }
  }

  // to start we will write a ready command to the serial port  
  // to show the Python we are ready to recieve the number of expected IMU 
  // which we will then write to a countCharacteristics on each of the peripherals
  // will in turn determine the rate at which data is served
  // ideally we then have dynamically eliminated a bottle-neck on the BLE
  // writing and recieving - such that the Central is parsing data faster than 
  // being served

  /*
    int x;
    bool initPeripheralsReady = false;
    delay(1000);  // waits for a second - for the Python script to clear the serial buffer
    // send init code - signals ready to receive
    info[1] = 2;
    for (int x = 0; x < 2; x++){
      byte packetArray[2] = {
        ((uint8_t*)&info[x])[0],
        ((uint8_t*)&info[x])[1],
      };
      Serial.write(packetArray, sizeof(packetArray));
    }
    
    while ( !initPeripheralsReady) {
      while (!Serial.available());
      x = Serial.readString().toInt();
      initPeripheralsReady = true;
    }
   */

  BLE.stopScan();
  digitalWrite( BLE_SCAN_LED_PIN, LOW );
  // iterate through all the detected matched peripherals
  for ( int i = 0; i < peripheralCounter; i++ )
  {
    peripherals[i].connect();
    peripherals[i].discoverAttributes();
    
    // here is where we write the countCharacteristics on each of the peripherals    
    BLECharacteristic countCharacteristic = peripherals[i].characteristic( BLE_UUID_COUNT );
    if ( countCharacteristic )                                                                                                   
    {
      static int imuCount = 4;
      countCharacteristics[i] = countCharacteristic;
      countCharacteristics[i].subscribe(); 
      delay(1000); // waits for a second
      countCharacteristics[i].writeValue( &imuCount, 4 );
    }
    // iterate through all Notify characteristics of each IMU and subscribe   
    BLECharacteristic orientCharacteristic = peripherals[i].characteristic( BLE_UUID_ORIENT );
    if ( orientCharacteristic )                                                                                                   
    {
      orientCharacteristics[i] = orientCharacteristic;
      orientCharacteristics[i].subscribe();
      orientCharacteristics[i].readValue( dataOrient[i].bytes, CHAR_DATA_SIZE );
      if ( debugBool ) {
        Serial.println("printing orient values for board number: ");
        Serial.println(i);
        Serial.println("init heading: ");
        Serial.println(dataOrient[i].values.X);
        Serial.println("init pitch: ");
        Serial.println(dataOrient[i].values.Y);
        Serial.println("init roll: ");
        Serial.println(dataOrient[i].values.Z);
      }
    }
    
    BLECharacteristic accelCharacteristic = peripherals[i].characteristic( BLE_UUID_ACCEL );
    if ( accelCharacteristic )
    {
      accelCharacteristics[i] = accelCharacteristic;
      accelCharacteristics[i].subscribe();
      accelCharacteristics[i].readValue( dataAccel[i].bytes, CHAR_DATA_SIZE );
      if ( debugBool ) {
        Serial.println("printing accel values for board number: ");
        Serial.println(i);
        Serial.println("init ax: ");
        Serial.println(dataAccel[i].values.X);
        Serial.println("init ay: ");
        Serial.println(dataAccel[i].values.Y);
        Serial.println("init az: ");
        Serial.println(dataAccel[i].values.Z);
      }
    }
    
    BLECharacteristic gyroCharacteristic = peripherals[i].characteristic( BLE_UUID_GYRO );
    if ( gyroCharacteristic )
    {
      gyroCharacteristics[i] = gyroCharacteristic;
      gyroCharacteristics[i].subscribe();
      gyroCharacteristics[i].readValue( dataGyro[i].bytes, CHAR_DATA_SIZE );
      if ( debugBool ) {
        Serial.println("printing gyro values for board number: ");
        Serial.println(i);
        Serial.println("init gx: ");
        Serial.println(dataGyro[i].values.X);
        Serial.println("init gy: ");
        Serial.println(dataGyro[i].values.Y);
        Serial.println("init gz: ");
        Serial.println(dataGyro[i].values.Z);
      }
    }
  }
  peripheralsConnected = peripheralCounter;
}

void loop()
{
  for ( int i = 0; i < peripheralsConnected; i++ ) {
    for ( int j = 0; j < BLE_CHAR_NUM; j++){
      if ( !orientUpdate[i] ) {
        if ( orientCharacteristics[i].valueUpdated() ) {
          orientCharacteristics[i].readValue( dataOrient[i].bytes, CHAR_DATA_SIZE );
          if ( debugBool ) {
            Serial.println("printing orient values for board number: ");
            Serial.println(i);
  
            Serial.println("heading: ");
            Serial.println(dataOrient[i].values.X);
            Serial.println("pitch: ");
            Serial.println(dataOrient[i].values.Y);
            Serial.println("roll: ");
            Serial.println(dataOrient[i].values.Z);
          }
          orientUpdate[i] = true;
        }
      }
      if ( !accelUpdate[i] ) {
        if ( accelCharacteristics[i].valueUpdated() ) {
          accelCharacteristics[i].readValue( dataAccel[i].bytes, CHAR_DATA_SIZE );
          if ( debugBool ) {
            Serial.println("printing accel values for board number: ");
            Serial.println(i);
            
            Serial.println("ax: ");
            Serial.println(dataAccel[i].values.X);
            Serial.println("ay: ");
            Serial.println(dataAccel[i].values.Y);
            Serial.println("az: ");
            Serial.println(dataAccel[i].values.Z);
          }
          accelUpdate[i] = true;
        }
      }
      if ( !gyroUpdate[i] ) {
        if ( gyroCharacteristics[i].valueUpdated() ) {
          gyroCharacteristics[i].readValue( dataGyro[i].bytes, CHAR_DATA_SIZE );
          if ( debugBool ) {
            Serial.println("printing gyro values for board number: ");
            Serial.println(i);
            
            Serial.println("gx: ");
            Serial.println(dataGyro[i].values.X);
            Serial.println("gy: ");
            Serial.println(dataGyro[i].values.Y);
            Serial.println("gz: ");
            Serial.println(dataGyro[i].values.Z);
          }
          gyroUpdate[i] = true;
        }
      }
    }
    if ( debugBool ) {
      Serial.println("Update bool array for the following board: ");
      Serial.println(i);
      Serial.println("Orient value");
      Serial.println(orientUpdate[i]);
      Serial.println("Accel value");
      Serial.println(accelUpdate[i]);
      Serial.println("Gyro value");
      Serial.println(orientUpdate[i]);
    }
    if ( orientUpdate[i] && accelUpdate[i] && gyroUpdate[i] ){
      orientUpdate[i] = false;
      accelUpdate[i] = false;
      gyroUpdate[i] = false;
      if ( !debugBool ) {
        info[0] = i;
        info[1] = 0;
        for (int x = 0; x < 2; x++){
          byte packetArray[2] = {
            ((uint8_t*)&info[x])[0],
            ((uint8_t*)&info[x])[1],
          };
          Serial.write(packetArray, sizeof(packetArray));
        }
        Serial.write(dataOrient[i].bytes, CHAR_DATA_SIZE);
  
        info[1] = 1;
        for (int x = 0; x < 2; x++){
          byte packetArray[2] = {
            ((uint8_t*)&info[x])[0],
            ((uint8_t*)&info[x])[1],
          };
          Serial.write(packetArray, sizeof(packetArray));
        }
        Serial.write(dataAccel[i].bytes, CHAR_DATA_SIZE);
  
        info[1] = 2;
        for (int x = 0; x < 2; x++){
          byte packetArray[2] = {
            ((uint8_t*)&info[x])[0],
            ((uint8_t*)&info[x])[1],
          };
          Serial.write(packetArray, sizeof(packetArray));
        }
        Serial.write(dataGyro[i].bytes, CHAR_DATA_SIZE); 
      }
    }
  }
}

//void gyro1CharacteristicWritten(BLEDevice central, BLECharacteristic characteristic) {
//  if (gyro1Characteristic.value()) {
//    short info[2] = { 0, 2 };
//    float gyro1Data[3];
//    gyro1Characteristic.readValue( &gyro1Data, 12 );
//  
//    for (int i = 0; i < 2; i++){
//      byte packetArray[2] = {
//        ((uint8_t*)&info[i])[0],
//        ((uint8_t*)&info[i])[1],
//      };
//      Serial.write(packetArray, sizeof(packetArray));
//    }
//    
//    for (int i = 0; i < 3; i++){
//      byte packetArray[4] = {
//        ((uint8_t*)&gyro1Data[i])[0],
//        ((uint8_t*)&gyro1Data[i])[1],
//        ((uint8_t*)&gyro1Data[i])[2],
//        ((uint8_t*)&gyro1Data[i])[3],
//      };
//      Serial.write(packetArray, sizeof(packetArray));
//    }
//  }
//}
