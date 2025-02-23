import os
import signal
import socket
import threading
import pymysql
import json
import time

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5000

client_sockets = {"in": None, "out": None, "admin": None, "parking1": None,"parking2": None,"parking3": None,"parking4": None}

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
    server_socket.listen(10)
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

                        if jsonData["type"] == "insertUserInfo":
                            jsonData.pop("type", None)

                            table_name = "parking_smoothly.user_info"
                            query = f"""
                                        INSERT INTO {table_name} (
                                            user_name,
                                            car_number,
                                            car_uuid,
                                            user_phone,
                                            car_category,
                                            pass_expiration_date
                                        ) VALUES (
                                            '{jsonData["user_name"]}',
                                            '{jsonData["car_number"]}',
                                            '{jsonData["car_uuid"]}',
                                            '{jsonData["user_phone"]}',
                                            '{jsonData["car_category"]}',
                                            '{jsonData["pass_expiration_date"]}'
                                        );
                                    """
                            resultMessage = executeQuery(query)

                        elif(jsonData["type"] == "selectUserInfo"):
                            jsonData.pop("type", None)
                            
                            table_name = "parking_smoothly.user_info"                            
                            query = f"""
                                SELECT 
                                    user_id,
                                    user_name,
                                    car_number,
                                    car_uuid,
                                    user_phone,
                                    car_category,
                                    pass_expiration_date
                                FROM {table_name}
                            """

                            conditions = []
                            if "user_id" in jsonData:
                                conditions.append(f"user_id = {jsonData['user_id']}")
                            if "user_name" in jsonData:
                                conditions.append(f"user_name = '{jsonData['user_name']}'")
                            if "car_number" in jsonData:
                                conditions.append(f"car_number = '{jsonData['car_number']}'")
                            if "car_uuid" in jsonData:
                                conditions.append(f"car_uuid = '{jsonData['car_uuid']}'")
                            if "user_phone" in jsonData:
                                conditions.append(f"user_phone = '{jsonData['user_phone']}'")
                            if "car_category" in jsonData:
                                conditions.append(f"car_category = '{jsonData['car_category']}'")
                            if "pass_expiration_start" in jsonData and "pass_expiration_end" in jsonData:
                                conditions.append(f"pass_expiration_date BETWEEN '{jsonData['pass_expiration_start']}' AND '{jsonData['pass_expiration_end']}'")

                            # 조건이 존재하면 WHERE 절 추가
                            if conditions :
                                query += " WHERE " + " AND ".join(conditions)
                            
                            query += ";"

                            resultMessage = executeQuery(query)

                        elif(jsonData["type"] == "updateUserInfo"):
                            jsonData.pop("type", None)

                            table_name = "parking_smoothly.user_info"

                            query = f"""
                                        UPDATE 
                                            parking_smoothly.user_info
                                        SET 
                                            user_name = '{jsonData["user_name"]}',
                                            car_number = '{jsonData["car_number"]}',
                                            car_uuid = '{jsonData["car_uuid"]}',
                                            user_phone = '{jsonData["user_phone"]}',
                                            car_category = '{jsonData["car_category"]}',
                                            pass_expiration_date = '{jsonData["pass_expiration_date"]}'
                                        WHERE user_id = {jsonData[""]};
                                    """
                            # resultMessage = executeQuery(query)

                        elif(jsonData["type"] == "selectEvent"):
                            jsonData.pop("type", None)
                            
                            table_name = "parking_smoothly.parking_event_history"
                            query = f"select * from {table_name};"

                            # resultMessage = executeQuery(query)

                        elif(jsonData["type"] == "selectInOutHistory"):
                            jsonData.pop("type", None)
                            
                            table_name = "parking_smoothly.car_inout_history"                            
                            query = f"""
                                SELECT 
                                    inout_id,
                                    user_id,
                                    indatetime,
                                    in_picture,
                                    outdatetime,
                                    out_picture,
                                    car_number,
                                    car_uuid,
                                    parking_pay,
                                    charging_pay
                                FROM {table_name}
                            """

                            conditions = []
                            
                            if "inout_id" in jsonData:
                                conditions.append(f"inout_id = {jsonData['inout_id']}")
                            if "user_id" in jsonData:
                                conditions.append(f"user_id = {jsonData['user_id']}")
                            if "car_number" in jsonData:
                                conditions.append(f"car_number = '{jsonData['car_number']}'")
                            if "car_uuid" in jsonData:
                                conditions.append(f"car_uuid = '{jsonData['car_uuid']}'")
                            
                            # 입차시간 및 출차시간 범위 필터링 가능
                            if "indatetime_start" in jsonData and "indatetime_end" in jsonData:
                                conditions.append(f"indatetime BETWEEN '{jsonData['indatetime_start']}' AND '{jsonData['indatetime_end']}'")
                            if "outdatetime_start" in jsonData and "outdatetime_end" in jsonData:
                                conditions.append(f"outdatetime BETWEEN '{jsonData['outdatetime_start']}' AND '{jsonData['outdatetime_end']}'")

                            # WHERE 절 추가
                            if conditions:
                                query += " WHERE " + " AND ".join(conditions)
                            
                            query += ";"

                            resultMessage = executeQuery(query)

                        elif(jsonData["type"] == ""):
                            jsonData.pop("type", None)

                        else :
                            print("admin 오류:", message)
                    except json.JSONDecodeError:
                        print("❌ JSON 파싱 오류:", message)
                    finally :
                          if(client_socket != None):
                            client_socket.sendall(json.dumps(resultMessage).encode("utf-8"))

            # 주차 공간 처리
            elif data.startswith("parking/"):
                point, category, message = data.split("/", 2)
                print(f"point : {point}, category : {category}, message : {message}")

                if category.startswith("space"):
                    print("category space")
                    
                    # "enable"이면 해당 공간을 사용 가능(1), "disable"이면 사용 불가능(0)으로 설정
                    new_state = None
                    if message == "disable":
                        new_state = 0
                    elif message == "available":
                        new_state = 1
                    
                    if new_state is not None:
                        # 해당 주차공간(DB의 space_state 테이블에서 space_name과 일치)을 업데이트
                        table_name = "parking_smoothly.space_state"
                        update_sql = f"UPDATE {table_name} SET state = {new_state} WHERE space_name = '{category}'"
                        resultMessage = executeQuery(update_sql)
                        print(f"DB update result: {resultMessage}")
                        
                        # 전체 사용 가능한 주차공간의 수를 DB에서 계산 (state 컬럼이 1인 공간의 합)
                        select_sql = "SELECT SUM(state) as available FROM  parking_smoothly.space_state where state = 1;"
                        result = executeQuery(select_sql)
                        print(result)
                        if result and isinstance(result, list) and len(result) > 0:
                            car_count = int(result[0]['available'])
                        else:
                            car_count = 0
                        
                        # 사용 가능 수가 0 ~ 4 사이인지 보정
                        if car_count > 4:
                            car_count = 4
                        elif car_count < 0:
                            car_count = 0
                                                
                        send_message_to_client("in", str(car_count) + "COUNT")

                elif category.startswith("flame"):
                    if message == "detected":
                        print("fire !!!!!!!!!!!!!!!!")
                        table_name = "parking_smoothly.parking_event_history"
                        query = f"INSERT INTO {table_name} (event_category) VALUES ('{category} {message}');"
                        print(query)
                        resultMessage = executeQuery(query)
                        print("{resultMessage : " + str(resultMessage))
                        # admin에게 화재 발생 전송        
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