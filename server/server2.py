import socket
import threading
import pymysql
import json
import time
import os
import signal
import easyocr
import cv2
from datetime import date, datetime
import re


# 📌 OCR 객체 생성 (한국어 & 영어 지원)
reader = easyocr.Reader(['ko', 'en'])

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5000

client_sockets = {"in": None, "out": None, "admin": None, "parking1": None,"parking2": None,"parking3": None,"parking4": None}

car_count = 4

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

# ✅ OCR 수행 함수
def perform_ocr():
    print("📷 OCR 시작...")
    
    camera_url = 'http://192.168.102.249:5001/feed1'
    cap = cv2.VideoCapture(camera_url)
    
    if not cap.isOpened():
        print("❌ 카메라 스트림을 열 수 없습니다.")
        return "Error: Camera Stream Not Available"
    
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if ret:
            result = reader.readtext(frame)
            texts = [detection[1] for detection in result]

            if texts:
                print(f"📜 OCR 결과: {texts}")
                return " ".join(texts)

            break  # 성공적으로 OCR 수행했으면 루프 종료
        
        elif time.time() - start_time > 10:
            print("❌ 10초 내에 영상 프레임을 읽을 수 없습니다.")
            return "Error: Failed to Capture Image"
    
    cap.release()
    return "No Text Detected"

# 라즈베리파이 RFID 인식시 변환 필요
def convert_rfid_format(rfid_string):
    # 'RFID ' 제거 후, 16진수 숫자만 추출
    hex_string = rfid_string.replace("RFID ", "")  # 'RFID ' 제거

    # 8자리까지만 추출
    hex_string = hex_string[6:-2]

    print(hex_string)
  
    # 변환 로직 적용 (앞의 0 제거 후 소문자로 변환)
    first_part = hex_string[0:2].lstrip("0").lower()  # 앞의 0 제거 후 소문자로 변환
    second_part = hex_string[2:4].lstrip("0").lower()  
    third_part = hex_string[4:6].lstrip("0").lower()  
    fourth_part = hex_string[6:8].lstrip("0").lower()  

    # 빈 문자열이 되면 '0'로 설정 (예: "00" → "0")
    first_part = first_part if first_part else "0"
    second_part = second_part if second_part else "0"
    third_part = third_part if third_part else "0"
    fourth_part = fourth_part if fourth_part else "0"

    # 최종 결과 조합
    return f"{first_part} {second_part} {third_part} {fourth_part}"

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

            if data.startswith("in/") :
                
                point, uuid = data.split("/")
                
                client_sockets[point] = client_socket

                uuid = convert_rfid_format(uuid)
                print("in " + uuid)

                ocr_result = perform_ocr()

                print("ocr_result" + ocr_result)
                # 차단기 오픈 여부 검사
                query = f"""
                    SELECT 
                        *
                    FROM 
                        parking_smoothly.user_info
                    WHERE 
                        car_uuid = '{uuid}' AND 
                        car_number = '{ocr_result}' AND
                        pass_expiration_date >= now()
                """
                result = executeQuery(query)

                print(result)

                if(result and car_count > 0):
                    # send_message_to_client(point, str(car_count) + "PASS")

                    # 차량 출입 기록
                    query = f"""
                                INSERT INTO parking_smoothly.car_inout_history (
                                    park_id, user_id, inout_car_number, inout_car_uuid
                                ) VALUES (
                                    '1',
                                    '{result[0]['user_id']}',
                                    '{ocr_result}',
                                    '{uuid}'
                                );
                            """
                    result = executeQuery(query)

                # else:
                    # send_message_to_client(point, str(car_count) + "FAIL")

            elif data.startswith("out/"):
                point, message = data.split("/")

                client_sockets[point] = client_socket

                if message == "PING":
                    send_message_to_client(point, "000PONG")

                elif message in ["OPENOK", "CLOSEOK", "PASSOK"]:
                    print(f"✅ {point.upper()} 응답 확인: {message}")
                else: 
                    print(f"✅ {point.upper()} 등록됨 (IP: {addr})")
                    print(f"🆔 감지된 message: {message} (위치: {point.upper()})")

                    # 입출차 조회 

                    query = f"""
                                SELECT 
                                    inout_id,
                                    user_id,
                                    indatetime,
                                    in_picture,
                                    outdatetime,
                                    out_picture,
                                    inout_car_number,
                                    inout_car_uuid 
                                FROM 
                                    parking_smoothly.car_inout_history
                                WHERE 
                                    inout_car_uuid = '{message}' AND 
                                    outdatetime is NULL
                            """
                    
                    result = executeQuery(query)
                    if len(result) != 0:
                        query = f"""
                                UPDATE parking_smoothly.car_inout_history
                                SET outdatetime = now()
                                WHERE inout_id = {result[0]["inout_id"]};
                            """
                        resultMsg = executeQuery(query)   

                        query = f"""
                                SELECT 
                                    DATEDIFF(pass_expiration_date , NOW()) AS remaining_days 
                                FROM 
                                    parking_smoothly.user_info
                                WHERE
                                    user_id = {result[0]["user_id"]};
                            
                            """
                        result = executeQuery(query)   

                        remaining_days = int(result[0]["remaining_days"])

                        if(remaining_days < 10):
                            remaining_days = "00" + str(remaining_days)
                        elif(remaining_days < 100):
                            remaining_days = "0" + str(remaining_days)

                        send_message_to_client(point, remaining_days + "PASS")
                    else:
                        send_message_to_client(point, "000FAIL")

            # ✅ 관리자 요청 처리 (모든 요청을 JSON으로 처리)
            elif data.startswith("admin/"):

                client_sockets["admin"] = client_socket

                try:
                    jsonData = json.loads(data[6:])  # "admin/" 부분을 제외하고 JSON 파싱
                    print("📌 DB 데이터 수신:\n", json.dumps(jsonData, indent=4, ensure_ascii=False))

                    request_type = jsonData.get("type")

                    # 🚗 출입문 제어 요청
                    if request_type == "INOPEN":
                        send_message_to_client("in", str(car_count) + "PASS")
                    elif request_type == "OUTOPEN":
                        send_message_to_client("out", str(car_count) + "PASS")

                    # 🛠 사용자 정보 삽입
                    elif request_type == "insertUserInfo":
                        query = f"""
                            INSERT INTO parking_smoothly.user_info (
                                park_id, user_name, car_number, car_uuid, user_phone, car_category, pass_start_date, pass_expiration_date
                            ) VALUES (
                                '{jsonData["park_id"]}', '{jsonData["user_name"]}', '{jsonData["car_number"]}', 
                                '{jsonData["car_uuid"]}', '{jsonData["user_phone"]}', '{jsonData["car_category"]}', 
                                '{jsonData["pass_start_date"]}', '{jsonData["pass_expiration_date"]}'
                            );
                        """
                        result = executeQuery(query)

                    # 🔍 사용자 정보 조회
                    elif request_type == "selectUserInfo":
                        query = "SELECT park_id, user_id, user_name, car_number, car_uuid, useㅣr_phone, car_category, pass_start_date, pass_expiration_date FROM parking_smoothly.user_info"
                        conditions = []

                        if "user_id" in jsonData and jsonData.get("user_id", "").strip():
                            conditions.append(f"user_id = {jsonData['user_id']}")
                        if "user_name" in jsonData and jsonData.get("user_name", "").strip():
                            conditions.append(f"user_name = '{jsonData['user_name']}'")
                        if "car_number" in jsonData and jsonData.get("car_number", "").strip():
                            conditions.append(f"car_number = '{jsonData['car_number']}'")
                        if "car_uuid" in jsonData and jsonData.get("car_uuid", "").strip():
                            conditions.append(f"car_uuid = '{jsonData['car_uuid']}'")
                        if "user_phone" in jsonData and jsonData.get("user_phone", "").strip():
                            conditions.append(f"user_phone = '{jsonData['user_phone']}'")
                        if "car_category" in jsonData and jsonData.get("car_category", "").strip():
                            conditions.append(f"car_category = '{jsonData['car_category']}'")
                        if "pass_expiration_start" in jsonData and "pass_expiration_end" in jsonData and jsonData.get("pass_expiration_start", "").strip() and jsonData.get("pass_expiration_end", "").strip():
                            conditions.append(f"pass_expiration_date BETWEEN '{jsonData['pass_expiration_start']}' AND '{jsonData['pass_expiration_end']}'")

                        if conditions:
                            query += " WHERE " + " AND ".join(conditions)
                        query += ";"
                        result = executeQuery(query)

                    # 📌 주차 공간 상태 조회
                    elif request_type == "selectSpaceState":
                        query = """
                            SELECT s.user_id, s.space_name, s.time AS max_date, s.state, u.user_name, u.car_number
                            FROM (
                                SELECT space_name, MAX(time) AS max_date
                                FROM parking_smoothly.space_state
                                GROUP BY space_name
                            ) AS t
                            JOIN parking_smoothly.space_state AS s ON s.space_name = t.space_name AND s.time = t.max_date
                            LEFT JOIN parking_smoothly.user_info AS u ON s.user_id = u.user_id;
                        """
                        result = executeQuery(query)

                    # ✏️ 사용자 정보 업데이트
                    elif request_type == "updateUserInfo":
                        query = f"""
                            UPDATE parking_smoothly.user_info
                            SET user_name = '{jsonData["user_name"]}', car_number = '{jsonData["car_number"]}', 
                                car_uuid = '{jsonData["car_uuid"]}', user_phone = '{jsonData["user_phone"]}', 
                                car_category = '{jsonData["car_category"]}', pass_expiration_date = '{jsonData["pass_expiration_date"]}'
                            WHERE user_id = {jsonData["user_id"]};
                        """
                        result = executeQuery(query)

                    # 📜 주차 이벤트 조회
                    elif request_type == "selectEvent":
                        query = "SELECT * FROM parking_smoothly.parking_event_history;"
                        result = executeQuery(query)

                    # 🚗 입출차 기록 조회
                    elif request_type == "selectInOutHistory":
                        query = """
                                    SELECT 
                                        inout_id,
                                        user_id,
                                        indatetime,
                                        in_picture,
                                        outdatetime,
                                        out_picture,
                                        inout_car_number,
                                        inout_car_uuid 
                                    FROM 
                                        parking_smoothly.car_inout_history
                                """
                        conditions = []

                        if "inout_id" in jsonData and jsonData.get("inout_id", "").strip():
                            conditions.append(f"inout_id = {jsonData['inout_id']}")
                        if "user_id" in jsonData and jsonData.get("user_id", "").strip():
                            conditions.append(f"user_id = {jsonData['user_id']}")
                        if "inout_car_number" in jsonData and jsonData.get("inout_car_number", "").strip():
                            conditions.append(f"inout_car_number = '{jsonData['inout_car_number']}'")
                        if "inout_car_uuid" in jsonData and jsonData.get("inout_car_uuid", "").strip():
                            conditions.append(f"inout_car_uuid = '{jsonData['inout_car_uuid']}'")
                        if "indatetime_start" in jsonData and "indatetime_end" in jsonData and jsonData.get("indatetime_start", "").strip() and jsonData.get("indatetime_end", "").strip():
                            conditions.append(f"indatetime BETWEEN '{jsonData['indatetime_start']}' AND '{jsonData['indatetime_end']}'")
                        if "outdatetime_start" in jsonData and "outdatetime_end" in jsonData and jsonData.get("outdatetime_start", "").strip() and jsonData.get("outdatetime_end", "").strip():
                            conditions.append(f"outdatetime BETWEEN '{jsonData['outdatetime_start']}' AND '{jsonData['outdatetime_end']}'")

                        if conditions:
                            query += " WHERE " + " AND ".join(conditions)
                        query += ";"
                        result = executeQuery(query)

                    # 🏓 PING 요청 처리
                    elif request_type == "ping":
                        result = {"park_id": 1, "type": "pong"}
                    

                    else:
                        print("⚠️ 알 수 없는 admin 요청:", jsonData)
                        result = {"status": "error", "message": "Invalid request type"}

                except json.JSONDecodeError:
                    print("❌ JSON 파싱 오류:", data)
                    result = {"status": "error", "message": "Invalid JSON format"}

                except Exception as e:
                    print("❌ 요청 처리 중 오류 발생:", str(e))
                    result = {"status": "error", "message": str(e)}

                # 📤 응답 전송
                resultMessage = {
                    "type": request_type if 'request_type' in locals() else "unknown",
                    "client": jsonData.get("client", "unknown"),
                    "data": result
                }

                if client_socket:
                    json_str = json.dumps(resultMessage, default=date_converter, ensure_ascii=False)
                    print("📤 응답 전송:", json_str)
                    client_socket.sendall(json_str.encode("utf-8"))

            # 주차 공간 처리
            elif data.startswith("parking/"):
                point, park_id, category, message = data.split("/",3)
                print(f"point : {point}, category : {category}, message : {message}")
                
                client_sockets[point] = client_socket

                if category.startswith("space"):
                    message, uuid = message.split("/",1)
                    print("category space")
                    
                    # "enable"이면 해당 공간을 사용 가능(1), "disable"이면 사용 불가능(0)으로 설정
                    state = None
                    if message == "disable":
                        state = 0
                    elif message == "available":
                        state = 1
                    
                    if len(uuid) > 0:
                        table_name = "parking_smoothly.user_info"
                        sql = f"""
                                SELECT 
                                        user_id
                                FROM
                                    {table_name}
                                WHERE car_uuid = '{uuid}'
                                
                            """
                        result = executeQuery(sql)
                        user_id = int(result[0]['user_id'])
                    else:
                        user_id = "null"

                    if state is not None:
                        # 해당 주차공간(DB의 space_state 테이블에서 space_name과 일치)을 업데이트
                        table_name = "parking_smoothly.space_state"
                        sql = f"""
                                INSERT INTO {table_name} (
                                            park_id,
                                            user_id,
                                            space_name,
                                            state
                                        ) VALUES (
                                            '{park_id}',
                                            {user_id},
                                            '{category}',
                                            '{state}'
                                        );
                            """
                        resultMessage = executeQuery(sql)
                        print(f"DB insert result: {resultMessage}")
                        
                        # 전체 사용 가능한 주차공간의 수를 DB에서 계산 (state 컬럼이 1인 공간의 합)
                        select_sql = """
                                        SELECT COALESCE(SUM(s.state), 0) AS available
                                        FROM parking_smoothly.space_state AS s
                                        JOIN (
                                            SELECT space_name, MAX(time) AS max_date
                                            FROM parking_smoothly.space_state
                                            GROUP BY space_name
                                        ) AS t
                                        ON s.space_name = t.space_name       
                                        AND s.time = t.max_date                                 
                                        WHERE s.state = 1;
                                    """
                        result = executeQuery(select_sql)
                        print(result)
                        if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
                            car_count = int(result[0]['available'])
                        else:
                            car_count = 0
                        
                        # 사용 가능 수가 0 ~ 4 사이인지 보정
                        if car_count > 4:
                            car_count = 4
                        elif car_count < 0:
                            car_count = 0
                                                
                        # send_message_to_client("in", str(car_count) + "COUNT")

                        query = """
                            SELECT s.user_id, s.space_name, s.time AS max_date, s.state, u.user_name, u.car_number
                            FROM (
                                SELECT space_name, MAX(time) AS max_date
                                FROM parking_smoothly.space_state
                                GROUP BY space_name
                            ) AS t
                            JOIN parking_smoothly.space_state AS s ON s.space_name = t.space_name AND s.time = t.max_date
                            LEFT JOIN parking_smoothly.user_info AS u ON s.user_id = u.user_id;
                        """
                        result = executeQuery(query)

                        adminSendMessage = {
                            "type": "selectSpaceState",
                            "client": "WindowClass",
                            "data": result
                        }

                        send_message_to_client("admin", json.dumps(adminSendMessage, ensure_ascii=False, default=str))

                elif category.startswith("flame"):
                    if message == "detected":
                        print("fire !!!!!!!!!!!!!!!!")
                        table_name = "parking_smoothly.space_state"
                        query = f"""
                                    SELECT 
                                        space_id
                                    FROM
                                        {table_name}
                                    WHERE space_name = 'space{category[5]}'
                                    ORDER BY time DESC LIMIT 1
                                """

                        result = executeQuery(query)
                        
                        print(f"resultMessage: {result}")
                        space_id = int(result[0]['space_id'])
                        table_name = "parking_smoothly.parking_event_history"
                        query = f"""
                                    INSERT INTO {table_name} (
                                            space_id,
                                            event_category,
                                            event_info
                                    ) VALUES (
                                            '{space_id}',
                                            'space{category[5] } flame',
                                            '{message}'
                                        );
                                """
                        resultMessage = executeQuery(query)
                        print("{resultMessage : " + str(resultMessage))
                        # admin에게 화재 발생 전송  
                        
                        adminSendMessage = {
                            "type": "firedetect",
                            "client": "WindowClass",
                            "data": "space" + category[5] + " flame detect"
                        }

                        send_message_to_client("admin", json.dumps(adminSendMessage, ensure_ascii=False, default=str))

    except Exception as e:
        print(f"❌ 오류 발생 ({addr}):")
        print(e)

    remove_client(client_socket)
    client_socket.close()

# ✅ 클라이언트 연결 제거 함수
def remove_client(client_socket):
    global client_sockets
    for point in list(client_sockets.keys()):
        if client_sockets[point] == client_socket:
            client_sockets[point] = None
            print(f"🔻 클라이언트 제거됨: {point.upper()}")

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

            # admin에게 보내는 전송은 응답을 받지 않음
            if(point == "admin") :
                return

            # PONG, COUNT 메시지 응답을 기다리지 않음
            if any(keyword in message for keyword in ["PONG","COUNT"]) :
                return

            # 응답을 기다림
            client_sockets[point].settimeout(timeout)
            response = client_sockets[point].recv(1024).decode("utf-8").strip()
            client_sockets[point].settimeout(None)  # 타임아웃 해제

            print(f"📥 응답 수신: {response}")
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

def date_converter(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"Type {type(o)} not serializable")


# ✅ TCP 서버 실행
if __name__ == "__main__":
    tcp_server()