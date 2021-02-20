#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <NeoPixelBus.h>

// Set to the number of LEDs in your LED strip
#define NUM_LEDS 60
// Maximum number of packets to hold in the buffer. Don't change this.
#define BUFFER_LEN 1024
// Toggles FPS output (1 = print FPS over serial, 0 = disable output)
#define PRINT_FPS 1

//NeoPixelBus settings
const uint8_t PixelPin = 3;  // make sure to set this to the correct pin, ignored for Esp8266(set to 3 by default for DMA)

// LED strip
NeoPixelBus<NeoGrbFeature, Neo800KbpsMethod> ledstrip(NUM_LEDS, PixelPin);

char* ssid = "xxx";
char* password =  "xxx";
char* mqttServer = "x.x.x.x";
int mqttPort = 1883;
char* mqttUser = "xxx";
char* mqttPassword = "xxx";

WiFiClient espClient;
PubSubClient client(espClient);

#if PRINT_FPS
  uint16_t fpsCounter = 0;
  uint32_t secondTimer = 0;
#endif

void callback(char* topic, byte* payload, unsigned int length) {
  int n = 0;
  for(int i = 0; i < length; i+=3)
  {
    if(n < NUM_LEDS){
    RgbColor pixel((uint8_t)payload[i], (uint8_t)payload[i+1], (uint8_t)payload[i+2]);
    ledstrip.SetPixelColor(n, pixel);
    n++;
    }
  }
  ledstrip.Show();
  #if PRINT_FPS
    fpsCounter++;
    Serial.print("/");//Monitors connection(shows jumps/jitters in packets)
  #endif


}

void setup() {

  Serial.begin(115200);
  Serial.println("Ledstrip begin");
  ledstrip.Begin();

  Serial.println("Wifi begin");
  WiFi.begin(ssid, password);

  Serial.println("Get Wifi status");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi..");
  }
  Serial.println("Connected to the WiFi network");

  client.setServer(mqttServer, mqttPort);
  client.setCallback(callback);

  while (!client.connected()) {
    Serial.println("Connecting to MQTT...");

    if (client.connect("ESP32Client")) {

      Serial.println("connected");

    } else {

      Serial.print("failed with state ");
      Serial.print(client.state());
      delay(2000);

    }
  }

  client.subscribe("led/device_a");

}

void loop() {
  client.loop();

  #if PRINT_FPS
    if (millis() - secondTimer >= 1000U) {
      secondTimer = millis();
      Serial.printf("FPS: %d\n", fpsCounter);
      fpsCounter = 0;
    }
  #endif
}
