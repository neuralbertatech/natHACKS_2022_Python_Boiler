#include "WiFi.h"
#include "AsyncUDP.h"

//// Verdun
//const char * ssid = "NETGEAR87-5G-2";
//const char * password = "7856@TasqeuP";

// Montreal
const char * ssid = "R12-253D";
const char * password = "qpjcp67647";
//const char *host = "192.168.0.148";

//// Verdun
// const char * ssid = "NETGEAR87";
// const char * password = "7856@TasqeuP";
//// const char *host = "192.168.1.33";

AsyncUDP udp;

int mainState = 0; // NULL = setup not run, 0 = systems ready, 1 = started, 2 = done saving serve data
//char fileName[] = "/0000.txt";
char fileName[9];

void setup()
{
    Serial.begin(115200);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    if (WiFi.waitForConnectResult() != WL_CONNECTED) {
        Serial.println("WiFi Failed");
        while(1) {
            delay(1000);
        }
    }
    if(udp.listen(3333)) {
        Serial.print("UDP Listening on IP: ");
        Serial.println(WiFi.localIP());
        udp.onPacket([](AsyncUDPPacket packet) {
            Serial.print("UDP Packet Type: ");
            Serial.print(packet.isBroadcast()?"Broadcast":packet.isMulticast()?"Multicast":"Unicast");
            Serial.print(", From: ");
            Serial.print(packet.remoteIP());
            Serial.print(":");
            Serial.print(packet.remotePort());
            Serial.print(", To: ");
            Serial.print(packet.localIP());
            Serial.print(":");
            Serial.print(packet.localPort());
            Serial.print(", Length: ");
            Serial.print(packet.length());
            Serial.print(", Data: ");
            Serial.write(packet.data(), packet.length());
            Serial.println();
            //reply to the client
            packet.printf("Got %u bytes of data", packet.length());

            // check command      :   4000,       0,           0,            0
            //                    ex. 4000,       0,           0,            0

            // initiation command :   5000,   fname, sample rate, nth returned
            //                    ex. 5000,    1000,          10,           10

            // trigger command    :   6000, curTrig,           0,            0  
            //                    ex. 6000,       6,           0,            0   
            
            // save command       :   7000,       0,           0,            0 
            // 

            char* curData = (char*)packet.data();

            int token1_value = atoi(strtok(curData, ","));
//            int token2_value = atoi(strtok(NULL, ","));
//            int token3_value = atoi(strtok(NULL, ","));
//            int token4_value = atoi(strtok(NULL, ","));

            if (token1_value == 4000){
              packet.printf("Command %u recieved, MCU is ready to go.", token1_value);
              mainState = 1;
              Serial.print("mainState changed to:");
              Serial.print(mainState);
            } else if (token1_value == 5000){
              mainState = 2;

//              char msg[11];
//              sprintf(msg,"/%s.txt",strtok(NULL, ","));
//              Serial.println(msg);

//              char fileName[10];
              sprintf(fileName,"/%s.txt",strtok(NULL, ","));
              Serial.println(fileName);

//              packet.printf("Command %u recieved, fname set to %u, sample rate set to %u, every %u th will be sent back.", token1_value, token2_value, token3_value, token4_value);

 
              Serial.print("mainState changed to:");
              Serial.print(mainState);
            } else if (token1_value == 6000){
              int token2_value = atoi(strtok(NULL, ","));
              packet.printf("Command %u recieved, trig # %u injected into IMU stream", token1_value, token2_value);
              mainState = 3;
              Serial.print("mainState changed to:");
              Serial.print(mainState);
            } else if (token1_value == 7000){
              packet.printf("Command %u recieved, stopping IMU sampling and uploading files via FTP", token1_value);
              mainState = 4;
              Serial.print("mainState changed to:");
              Serial.print(mainState);
            } else {
              packet.printf("Command %u recieved, invalid command", token1_value);
            }
        });
    }
}

void loop()
{
    delay(5000);
    //Send broadcast
    udp.broadcast("Anyone here?");
    Serial.print("mainState:");
    Serial.print(mainState);
    Serial.print("\n");

}
