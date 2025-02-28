#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <WiFiClient.h>

// 📌 RFID 핀 설정
#define SS_PIN 5   
#define RST_PIN 22 

MFRC522 mfrc522(SS_PIN, RST_PIN); 

// 📌 Wi-Fi 설정
const char* ssid = "AndroidHotspot6520";    
const char* password = "65206520";

// 📌 서버 및 Raspberry Pi 설정
const char* serverIP = "192.168.102.121";  // 서버 IP
const int serverPort = 5000;  

const char* raspberryPiIP = "192.168.102.249";  // Raspberry Pi IP
const int raspberryPiPort = 6000;  // Port for Raspberry Pi connection

WiFiClient serverClient;
WiFiClient raspberryPiClient;

// 📌 초음파 센서 핀 설정
const int trigPin1 = 27;
const int echoPin1 = 26;

// 📌 LED & 불꽃 센서 핀 설정
const int greenLedPin = 25;
const int redLedPin = 33;
const int flameSensorPin = 32;

// 📌 거리 측정 변수
long duration;
int distance;

String lastStatus = "";  // 마지막 상태
bool prevFlameStatus = false;  // 이전 불꽃 상태

void setup() 
{
    Serial.begin(115200);  
    SPI.begin();  
    mfrc522.PCD_Init();  
    
    // Wi-Fi 연결
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) 
    {
        delay(1000);
        Serial.println("Connecting to WiFi...");
    }
    Serial.println("Connected to WiFi");

    // 서버 연결 시도
    if (serverClient.connect(serverIP, serverPort)) 
    {
        Serial.println("Connected to server");
    } 
    else 
    {
        Serial.println("Connection to server failed!");
    }

    // Raspberry Pi 연결 시도
    if (raspberryPiClient.connect(raspberryPiIP, raspberryPiPort)) 
    {
        Serial.println("Connected to Raspberry Pi");
    } 
    else 
    {
        Serial.println("Connection to Raspberry Pi failed!");
    }

    // 핀 모드 설정
    pinMode(trigPin1, OUTPUT);
    pinMode(echoPin1, INPUT);
    pinMode(greenLedPin, OUTPUT);
    pinMode(redLedPin, OUTPUT);
    pinMode(flameSensorPin, INPUT);
}

void loop() 
{
    // 📌 초음파 센서를 사용하여 주차 상태 확인
    digitalWrite(trigPin1, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin1, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin1, LOW);
    duration = pulseIn(echoPin1, HIGH);
    distance = duration * 0.034 / 2;  

    // 📌 초음파 값에 따른 LED 상태 변경
    if (distance <= 5) 
    {
        digitalWrite(greenLedPin, LOW); // 초록불 끄기
        digitalWrite(redLedPin, HIGH);  // 빨간불 켜기
    } 
    else 
    {
        digitalWrite(greenLedPin, HIGH); // 초록불 켜기
        digitalWrite(redLedPin, LOW);    // 빨간불 끄기
    }

    String uidString = ""; // RFID UID 문자열 초기화
    bool rfidDetected = false; // RFID 감지 여부 플래그

    // 📌 RFID 태그 인식 시 UID 저장
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) 
    {
        Serial.print("카드 UID: ");
        for (byte i = 0; i < mfrc522.uid.size; i++) 
        {
            Serial.print(mfrc522.uid.uidByte[i], HEX);
            Serial.print(" ");
            uidString += String(mfrc522.uid.uidByte[i], HEX) + " ";
        }
        Serial.println();
        rfidDetected = true; // RFID 감지됨
    }

    String parkingStatus;
    String message;

    // 📌 상태에 따른 메시지 전송
    if (distance <= 5 && rfidDetected) 
    {
        // 초음파와 RFID 모두 감지: disable 상태, RFID ID 전송
        parkingStatus = "disable";
        message = "parking/1/space1/" + parkingStatus + "/" + uidString;
        if (lastStatus != message)  // 상태가 변경된 경우에만 메시지 전송
        {
            sendMessageToBoth(message);  // 메시지 전송
            lastStatus = message;  // 현재 상태로 업데이트
        }
    } 
    else if (distance > 5 && !rfidDetected) 
    {
        // 초음파와 RFID 모두 비감지: enable 상태, RFID 공백 전송
        parkingStatus = "available";
        message = "parking/1/space1/" + parkingStatus + "/ ";
        if (lastStatus != message)  // 상태가 변경된 경우에만 메시지 전송
        {
            sendMessageToBoth(message);  // 메시지 전송
            lastStatus = message;  // 현재 상태로 업데이트
        }
    }

    // RFID 카드 멈추기
    mfrc522.PICC_HaltA();

    // 📌 불꽃 센서 상태 확인
    int flameStatus = digitalRead(flameSensorPin);
    bool currentFlameStatus = (flameStatus == LOW);  // 불꽃이 감지되면 LOW
    if (currentFlameStatus != prevFlameStatus) {
        prevFlameStatus = currentFlameStatus;
        if (currentFlameStatus) {
            sendMessageToBoth("parking/1/flame1/detected");
        } else {
            sendMessageToBoth("parking/1/flame1/none");
        }
    }

    delay(100);  
}

// 📌 서버와 Raspberry Pi로 메시지 전송 함수
void sendMessageToBoth(const String& message) 
{
    if (serverClient.connected()) 
    {
        serverClient.print(message);  
        serverClient.flush();  
        Serial.print("Sent to server: ");
        Serial.println(message);
    } 
    else 
    {
        Serial.println("Lost connection to server.");
        while (!serverClient.connect(serverIP, serverPort)) 
        {
            Serial.println("Reconnecting to server...");
            delay(1000);  
        }
        Serial.println("Reconnected to server");
    }

    if (raspberryPiClient.connected()) 
    {
        raspberryPiClient.print(message);  
        raspberryPiClient.flush();  
        Serial.print("Sent to Raspberry Pi: ");
        Serial.println(message);
    } 
    else 
    {
        Serial.println("Lost connection to Raspberry Pi.");
        while (!raspberryPiClient.connect(raspberryPiIP, raspberryPiPort)) 
        {
            Serial.println("Reconnecting to Raspberry Pi...");
            delay(1000);  
        }
        Serial.println("Reconnected to Raspberry Pi");
    }
}
