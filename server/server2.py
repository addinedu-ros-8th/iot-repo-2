import os
import signal
import socket
import threading
import pymysql
import json
import time

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5000

client_sockets = {"in": None, "out": None, "admin": None, "parking": None}
car_count = 4
park_seq = 1

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "parking_smoothly",
    "charset": "utf8mb4"
}

# ✅ 서버 실행 전에 5000번 포트를 사용 중인 프로세스 자동 해제
def free_port(port):
    try:
        result = os.popen(f"lsof -t -i :{port}").read().strip()
        if result:
            pids = result.split("\n")
            for pid in pids:
                print(f"🔴 기존 프로세스 종료: {pid}")
                os.kill(int(pid), signal.SIGKILL)
    except Exception as e:
        print(f"⚠️ 포트 해제 중 오류 발생: {e}")

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

# ✅ TCP 서버 실행 함수
def tcp_server():
    free_port(SERVER_PORT)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 🚀 빠른 재시작 가능
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.listen(5)
    print(f"🚀 TCP 서버 실행 중... {SERVER_IP}:{SERVER_PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"✅ 연결됨: {addr}")
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

# ✅ 요청 처리 함수
def handle_client(client_socket, addr):
    global client_sockets
    global car_count
    global park_seq

    try:
        while True:
            data = client_socket.recv(1024).decode("utf-8").strip()
            if not data:
                print(f"❌ {addr} 연결 종료됨!")
                break

            print(f"🔹 [{addr}] 수신된 데이터: {data}")
            
            time.sleep(0.1)

            # 차단기 in 입구 out 출구
            if data.startswith("in/") or data.startswith("out/"):
                point, message = data.split("/")
                client_sockets[point] = client_socket

                if message == "PING":
                    send_message_to_client(point, str(car_count) + "PONG")

                elif message in ["OPENOK", "CLOSEOK", "COUNTOK"]:
                    print(f"✅ {point.upper()} 응답 확인: {message}")
                else: 
                    print(f"✅ {point.upper()} 등록됨 (IP: {addr})")
                    print(f"🆔 감지된 message: {message} (위치: {point.upper()})")
                    send_message_to_client(point, str(car_count) + "PASS")

            # 관리자 화면
            elif data.startswith("admin/"):
                point, message = data.split("/")
                client_sockets[point] = client_socket
                if message == "INOPEN":
                    send_message_to_client("in", str(car_count) + "PASS")
                elif message == "OUTOPEN":
                    send_message_to_client("out", str(car_count) + "PASS")
                else:
                    try:
                        jsonData = json.loads(message)
                        print("📌 DB 데이터 수신:\n", json.dumps(jsonData, indent=4, ensure_ascii=False))
                        if jsonData["type"] == "signup":
                            jsonData.pop("type", None)

                            table_name = "parking_smoothly.user_info"
                            columns = ", ".join(jsonData.keys())
                            values = ", ".join(f"'{value}'" if isinstance(value, str) else str(value) for value in jsonData.values())
                            query = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
                            resultMessage = executeQuery(query)
                        else :
                            print("admin 오류:", message)
                    except json.JSONDecodeError:
                        print("❌ JSON 파싱 오류:", message)
                    finally :
                          if(client_socket != None):
                            client_socket.sendall(json.dumps(resultMessage).encode("utf-8"))

            # 주차 공간
            elif data.startswith("parking/"):
                point, category, message = data.split("/",2)
                
                print(f"point : {point}, category : {category}, message : {message}")

                if(category.startswith("space")):
                    print(f"category space")
                    if(category.startswith("space")):
                        if(message == "disable"):
                            car_count = car_count - 1                                                
                        elif(message == "enable"):
                            car_count = car_count + 1
                    if(car_count > 4) : 
                        car_count = 4
                    elif(car_count < 0 ):
                        car_count = 0
                        
                    send_message_to_client("in", str(car_count) + "COUNT")

                elif(category.startswith("flame")):
                    if(message == "detected"):
                        print(f"message detected")
                        print("fire !!!!!!!!!!!!!!!!")

                        table_name = "parking_smoothly.parking_event_history"
                        query = f"INSERT INTO {table_name} (park_seq,event_category) VALUES ({park_seq}, '{category} {message}');"
                        print(query)
                        resultMessage = executeQuery(query)
                        print("{resultMessage : " + str(resultMessage))
                        # admin에게 화제 발생 전송        
                        send_message_to_client("admin", "fire detection")

    except Exception as e:
        print(f"❌ 오류 발생 ({addr}):")
        print(e)

    remove_client(client_socket)
    client_socket.close()

# ✅ 클라이언트 연결 제거 함수
def remove_client(client_socket):
    global client_sockets
    for direction in list(client_sockets.keys()):
        if client_sockets[direction] == client_socket:
            client_sockets[direction] = None
            print(f"🔻 클라이언트 제거됨: {direction.upper()}")

# ✅ 데이터베이스 실행 함수
def executeQuery(query):
    print("📌 실행할 SQL:\n", query)
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  

    try:
        cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            response = cursor.fetchall()
        else:
            conn.commit()
            response = {"status": "success", "message": "Query executed successfully"}

    except Exception as e:
        response = {"status": "fail", "message": str(e)}         
    
    finally:      
        cursor.close()
        conn.close()
        return response

# ✅ 메시지 전송 후 응답 수신
def send_message_to_client(point, message, timeout=5):
    if client_sockets[point]:
        try:
            client_sockets[point].sendall((message + "\n").encode("utf-8"))
            print(f"📩 메시지 전송: {message} ({point.upper()})")

            if any(keyword in message for keyword in ["PONG","COUNT"]):
                return

            # 응답을 기다림
            client_sockets[point].settimeout(timeout)
            response = client_sockets[point].recv(1024).decode("utf-8").strip()
            client_sockets[point].settimeout(None)  # 타임아웃 해제

            print(f"📥 ESP32 응답 수신: {response}")
            return response

        except socket.timeout:
            print(f"⚠️ {point.upper()} 응답 시간 초과")
            return "Timeout"
        except Exception as e:
            print(f"❌ 클라이언트 메시지 전송 오류: {e}")
            return "Error"
    else:
        print(f"❌ {point.upper()} 클라이언트 없음")
        return "No Client"


# ✅ TCP 서버 실행
if __name__ == "__main__":
    tcp_server()
