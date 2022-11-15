int LED = 13;
int data;

void setup()
{
  Serial.begin(9600);
  pinMode(LED,OUTPUT);
  digitalWrite(LED,LOW);
}

void loop()
{
  while(Serial.available())
  {
    data = Serial.read();
  }

  if(data == '1')
  {
    digitalWrite(LED,HIGH);
    Serial.println("Arduino says the LED is turned on");
  }

  else if(data == '0')
  {
    digitalWrite(LED,LOW);
    Serial.println("Arduino says the LED is turned off");
  }
}
