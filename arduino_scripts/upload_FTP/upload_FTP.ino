/******************************************************************************

ESP32-CAM remote image access via FTP. Take pictures with ESP32 and upload it via FTP making it accessible for the outisde network. 
Leonardo Bispo
July - 2019
https://github.com/ldab/ESP32_FTPClient

Distributed as-is; no warranty is given.

******************************************************************************/
#include "Arduino.h"
#include <WiFi.h>
#include <WiFiClient.h> 
#include <ESP32_FTPClient.h>
//#include "octocat.h"

#define WIFI_SSID "R12-253D"
#define WIFI_PASS "qpjcp67647"

//char ftp_server[] = "127.0.0.1";
char ftp_server[] = "192.168.0.179";
char ftp_user[]   = "esp32";
char ftp_pass[]   = "imu_dev";

// you can pass a FTP timeout and debbug mode on the last 2 arguments
ESP32_FTPClient ftp (ftp_server,ftp_user,ftp_pass, 5000, 2);

void setup()
{
  Serial.begin( 115200 );

  WiFi.begin( WIFI_SSID, WIFI_PASS );
  
  Serial.println("Connecting Wifi...");
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }
  Serial.println("");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  ftp.OpenConnection();

  // Get directory content
  ftp.InitFile("Type A");
  String list[128];
  ftp.ChangeWorkDir("/");
  ftp.ContentList("", list);
  Serial.println("\nDirectory info: ");
  for(int i = 0; i < sizeof(list); i++)
  {
    if(list[i].length() > 0)
      Serial.println(list[i]);
    else
      break;
  }

  // Make a new directory
  ftp.InitFile("Type A");
  ftp.MakeDir("my_new_dir");

//  // Create the new file and send the image
  ftp.ChangeWorkDir("my_new_dir");

  // Create the file new and write a string into it
  ftp.InitFile("Type A");
  ftp.NewFile("hello_world.txt");
  ftp.Write("Hello World");
  ftp.CloseFile();

  ftp.CloseConnection();
}

void loop()
{

}
