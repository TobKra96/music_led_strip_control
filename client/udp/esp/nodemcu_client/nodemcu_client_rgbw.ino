#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <NeoPixelBus.h>

// Set to the number of LEDs in your LED strip
#define NUM_LEDS 284
// Maximum number of packets to hold in the buffer. Don't change this.
#define BUFFER_LEN 1024
// Toggles FPS output (1 = print FPS over serial, 0 = disable output)
#define PRINT_FPS 1

//NeoPixelBus settings
const uint8_t PixelPin = 3;  // make sure to set this to the correct pin, ignored for Esp8266(set to 3 by default for DMA)

// Wifi and socket settings
const char* ssid     = "xxx";
const char* password = "xxx";
unsigned int localPort = 7777;
char packetBuffer[BUFFER_LEN];

// LED strip
NeoPixelBus<NeoGrbwFeature, Neo800KbpsMethod> ledstrip(NUM_LEDS, PixelPin);

WiFiUDP port;

// Network information
// IP must match the IP in config.py in python folder
IPAddress ip(x, x, x, x);
// Set gateway to your router's gateway
IPAddress gateway(x, x, x, x);
IPAddress subnet(x, x, x, x);

void setup() {
    Serial.begin(115200);
    Serial.println("Serial Begin");

    ledstrip.Begin();//Begin output
    ledstrip.Show();//Clear the strip for use
    welcomeLight();


    // Connect to wifi and print the IP address over serial
    wl_status_t state;
    bool isOn = false;
    int timeoutCounter = 0;
    bool reconnected = false;
    int stateLED = 0;

    wifiConnect();
    while (WiFi.status() != WL_CONNECTED) {
      reconnected = false;
      stateLED = -1;
      if(timeoutCounter >= 20){
        reconnected = true;
        delay(500);
        wifiDisconnect();
        delay(500);
        wifiConnect();
        delay(500);
        timeoutCounter = 0;
      }

      state = WiFi.status();

      if(state == WL_CONNECTED){
        stateLED = 0;
        Serial.println("WL_CONNECTED");
      }
      else if(state == WL_NO_SHIELD){
        stateLED = 1;
        Serial.println("WL_NO_SHIELD");
      }
      else if(state == WL_IDLE_STATUS){
        stateLED = 2;
        Serial.println("WL_IDLE_STATUS");
      }
      else if(state == WL_NO_SSID_AVAIL){
        stateLED = 3;
        Serial.println("WL_NO_SSID_AVAIL");
      }
      else if(state == WL_SCAN_COMPLETED){
        stateLED = 4;
        Serial.println("WL_SCAN_COMPLETED");
      }
      else if(state == WL_CONNECTED){
        stateLED = 5;
        Serial.println("WL_CONNECTED");
      }
      else if(state == WL_CONNECT_FAILED){
        stateLED = 6;
        Serial.println("WL_CONNECT_FAILED");
      }
      else if(state == WL_CONNECTION_LOST){
        stateLED = 7;
        Serial.println("WL_CONNECTION_LOST");
      }
      else if(state == WL_DISCONNECTED){
        stateLED = 8;
        Serial.println("WL_DISCONNECTED");
      }
      /*
      if (state == WL_NO_SHIELD) {  // WiFi.begin wasn't called yet
        wifiConnect();

      } else if (state == WL_CONNECT_FAILED) {  // WiFi.begin has failed (AUTH_FAIL)
        wifiDisconnect();
      }
      */

      delay(500);
      Serial.print(".");
      showConnection(isOn, reconnected, stateLED);
      isOn = !isOn;
      timeoutCounter++;
    }
    Serial.println("");
    Serial.print("Connected to ");
    Serial.println(ssid);
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    port.begin(localPort);
}

uint8_t N = 0;
#if PRINT_FPS
    uint16_t fpsCounter = 0;
    uint32_t secondTimer = 0;
#endif

void loop() {
    // Read data over socket
    int packetSize = port.parsePacket();
    // If packets have been received, interpret the command
    if (packetSize) {
        int len = port.read(packetBuffer, BUFFER_LEN);
        int n = 0;
        for(int i = 0; i < len; i+=3, i+=4) {
            RgbColor pixel((uint8_t)packetBuffer[i], (uint8_t)packetBuffer[i+1], (uint8_t)packetBuffer[i+2], (uint8_t)packetBuffer[i+3]);
            ledstrip.SetPixelColor(n, pixel);
            n++;
        }
        ledstrip.Show();
        #if PRINT_FPS
            fpsCounter++;
            Serial.print("/");//Monitors connection(shows jumps/jitters in packets)
        #endif
    }
    #if PRINT_FPS
        if (millis() - secondTimer >= 1000U) {
            secondTimer = millis();
            Serial.printf("FPS: %d\n", fpsCounter);
            fpsCounter = 0;
        }
    #endif
}

void welcomeLight(){
  Serial.println("Enter welcomeLigth()");
  uint8_t r = 0;
  uint8_t g = 0;
  uint8_t b = 0;

  for(uint8_t i = 0; i < 255; i++) {

    for(int n = 0; n < NUM_LEDS; n++) {
            RgbColor pixel(r, g, b);
            ledstrip.SetPixelColor(n, pixel);
        }
    ledstrip.Show();

    r++;
    g++;
    b++;

    delay(20);
  }
  Serial.println("Leave welcomeLigth()");
}

void showConnection(bool ledIsOn, bool reconnected, int stateLed){
  uint8_t r = 255;
  uint8_t g = 255;
  uint8_t b = 255;
  // [Connecting; Reconnected; stateLED; stateLED; stateLED; stateLED; stateLED; stateLED; stateLED; stateLED; stateLED; stateLED;...]
  if(ledIsOn)
  {
    RgbColor pixelOne(255, 0, 0);
    ledstrip.SetPixelColor(0, pixelOne);
  }
  else{
    RgbColor pixelOne(0, 0, 0);
    ledstrip.SetPixelColor(0, pixelOne);
  }

  if(reconnected)
  {
    RgbColor pixelTwo(0, 0, 255);
    ledstrip.SetPixelColor(1, pixelTwo);
  }
  else{
    RgbColor pixelTwo(0, 0, 0);
    ledstrip.SetPixelColor(1, pixelTwo);
  }

  if(stateLed == -1){
    for(int n = 2; n < 12; n++) {
           RgbColor pixel(0, 255, 0);
           ledstrip.SetPixelColor(n, pixel);
     }
  }
  else{
    for(int n = 2; n < 12; n++) {
           RgbColor pixel(255, 255, 255);
           ledstrip.SetPixelColor(n, pixel);
     }

     int stateLedWithOffset = stateLed + 2;
     RgbColor pixel(0, 255, 0);
     ledstrip.SetPixelColor(stateLedWithOffset, pixel);
  }

  for(int n = 12; n < NUM_LEDS; n++) {
           RgbColor pixel(r, g, b);
           ledstrip.SetPixelColor(n, pixel);
           }
  ledstrip.Show();
}

void wifiConnect(){
  Serial.println("Start wifi connection");
  WiFi.config(ip, gateway, subnet);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.println("wifi begin");
}

void wifiDisconnect(){
  Serial.println("Disconnecting WiFi");
  WiFi.disconnect(true);
}
