#include <WiFi.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>

// ✅ Wi-Fi 정보
const char* ssid = "AndroidHotspot6520";       // Wi-Fi SSID
const char* password = "65206520"; // Wi-Fi 비밀번호

// ✅ 서버 정보 (Flask 서버)
const char* serverIP = "192.168.102.121";  
const int serverPort = 5000;  
WiFiClient client;

const String breaker_name = "out";
// ✅ OLED 설정 (I2C 핀)
#define SDA_PIN 4  // D4 → SDA
#define SCL_PIN 21 // D21 → SCL
U8G2_SSD1306_128X32_UNIVISION_F_HW_I2C u8g2(U8G2_R0, SCL_PIN, SDA_PIN, U8X8_PIN_NONE);

// ✅ RFID 설정
#define SS_PIN 5
#define RST_PIN 22
MFRC522 rfid(SS_PIN, RST_PIN);

// ✅ 서보 모터 설정
#define SERVO_PIN 13
Servo myServo;

// ✅ PING 전송을 위한 타이머 변수
unsigned long lastPingTime = 0;
const unsigned long pingInterval = 60000; // 1분 (60,000ms)
bool serverConnectState = true;

// ✅ 명령을 저장할 큐 (최대 10개 명령 저장 가능)
#define MAX_COMMAND_QUEUE 20
String commandQueue[MAX_COMMAND_QUEUE];  
int queueSize = 0;

void setup() {
  Serial.begin(115200);
  
  // ✅ Wi-Fi 연결
  WiFi.begin(ssid, password);
  Serial.print("Wi-Fi 연결 중");
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi 연결 완료!");
  Serial.print("📡 IP 주소: ");
  Serial.println(WiFi.localIP());

  // ✅ I2C 초기화 (OLED)
  Wire.begin(SDA_PIN, SCL_PIN);
  u8g2.begin();

  // ✅ SPI 초기화 (RFID)
  SPI.begin();
  rfid.PCD_Init();

  // ✅ 서보 모터 초기화
  myServo.attach(SERVO_PIN);
  myServo.write(0); // 초기 위치

  // ✅ 서버에 TCP 연결 시도
  connectToServer();

  // ✅ OLED 초기화 메시지 출력
  oledDisplay("초기화 완료");

  delay(500);

  oledDisplay("스무디 주차장");
}

void loop() {
  // ✅ 서버 연결 상태 체크 및 재연결
  if (!client.connected()) {
    Serial.println("🚨 서버 연결 끊김. 재연결 시도...");
    connectToServer();
  }

  // ✅ 1분마다 PING 전송 (서버 연결 유지)
  if (millis() - lastPingTime >= pingInterval) {
    sendPing();
    lastPingTime = millis();
  }

  // ✅ RFID 태그 감지
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    String uidStr = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      uidStr = uidStr + String(rfid.uid.uidByte[i], HEX) + " ";
    }
    Serial.println("📡 RFID 감지됨: " + uidStr);
    sendToServer(uidStr);
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }

  // ✅ 서버에서 명령 수신 후 처리 (큐 사용)
  receiveCommand();

  // ✅ ESP 안정성을 위해 짧은 대기시간 추가
  delay(50);
}

// 📡 서버에 TCP 연결
void connectToServer() {
  int retryCount = 0;
  while (!client.connect(serverIP, serverPort) && retryCount < 5) {
    Serial.println("❌ TCP 서버 연결 실패! 재시도...");
    delay(2000);
    retryCount++;
  }
  
  if (client.connected()) {
    Serial.println("🚀 TCP 서버 연결 성공!");
    client.print(breaker_name + "/PING\n");
    oledDisplay("서버 연결 성공");
    serverConnectState = true;
  } else {
    Serial.println("⛔ 서버 연결 실패!");
    oledDisplay("서버 연결 실패");
  }
}

// 📡 PING 메시지 전송
void sendPing() {
  if (!client.connected()) {
    Serial.println("❌ 서버에 연결되지 않음! 재연결 시도");
    connectToServer();
    return;
  }
  client.print(breaker_name + "/PING\n");
  Serial.println("🔄 PING 전송 (서버 연결 유지)");
}

// 📡 서버에서 명령 수신 (명령을 큐에 저장 후 순차적 처리)
void receiveCommand() {
  while (client.available()) {  
    String receivedMessage = client.readStringUntil('\n');  
    receivedMessage.trim();

    Serial.println("📩 서버 명령 수신: " + receivedMessage);

    if (queueSize < MAX_COMMAND_QUEUE) {  
      commandQueue[queueSize] = receivedMessage;
      queueSize++;
    } else {
      Serial.println("⚠️ 명령 버퍼 초과! 일부 메시지를 무시합니다.");
    }
  }

  if (queueSize > 0) {
    processCommand(commandQueue[0]);  
    for (int i = 1; i < queueSize; i++) {
      commandQueue[i - 1] = commandQueue[i];  
    }
    queueSize--;  
  }
}

// 📡 명령 처리 함수
void processCommand(String receivedMessage) {
  String command = "";
  String remainingDay = "";

  for (int i = 0; i < receivedMessage.length(); i++) {
    if (i < 3) {
      remainingDay += receivedMessage[i];
    } else {
      command += receivedMessage[i];
    }
  }

  Serial.println("남은 일자: " + remainingDay);
  Serial.println("명령: " + command);

  if (command == "PASS") 
  {
    Serial.println("🔓 차량 통과!");
    
    oledDisplay("안녕히가세요.");
    delay(1000);
    oledDisplay("남은 일자 : " + remainingDay);
    delay(1000);
    myServo.write(90);
    delay(2000);
    myServo.write(0);
    client.print(breaker_name + "/PASSOK\n");
    oledDisplay("스무디 주차장");
    
  }
  else if (command == "OPEN") 
  {
    Serial.println("🔓 차단기 열림!");
    myServo.write(90);
    oledDisplay("차단기 열림!");
    client.print(breaker_name + "/OPENOK\n");
  }
  else if (command == "CLOSE") 
  {
    Serial.println("🔒 차단기 닫힘!");
    myServo.write(0);
    oledDisplay("차단기 닫힘!");
    client.print(breaker_name + "/CLOSEOK\n");
  }  
  else if((command == "PONG"))
  {

  }
  else if((command == "FAIL"))
  {
    oledDisplay("입차기록 없음");
    client.print(breaker_name + "/FAILOK\n");
  }
  else {
    Serial.println("⚠️ 알 수 없는 명령: " + command);
  }
}

// 📡 서버로 UID 데이터 전송
void sendToServer(String uid) {
  if (client.connected()) {
    client.print(breaker_name + "/" + uid + "\n");
    Serial.println("✅ UID 전송 완료: " + uid);
  } else {
    Serial.println("❌ 서버에 연결되지 않음!");
  }
}

// ✅ OLED 출력 함수
void oledDisplay(String message) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_unifont_t_korean2);
  u8g2.drawUTF8(5, 25, message.c_str());
  u8g2.sendBuffer();
}
