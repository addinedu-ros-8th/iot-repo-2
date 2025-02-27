import sys
import json
import time
import warnings
import cv2  # CameraThread에서 사용
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread, pyqtSignal, QDate
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QHeaderView, QLineEdit, QLabel
from PyQt5.QtGui import QPixmap, QImage
from PyQt5 import uic
from PyQt5.QtNetwork import QTcpSocket
from PyQt5.QtCore import QEvent


warnings.filterwarnings("ignore", category=DeprecationWarning)

# ------------------------------------------------------------------
# SocketManager: 단일 소켓과 네트워크 스레드를 생성 및 공유하는 싱글톤 클래스
# ------------------------------------------------------------------
class SocketManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SocketManager, cls).__new__(cls)
            cls._instance.socket = QTcpSocket()
            # 서버 IP와 포트 (예: "192.168.0.22", 6000)
            cls._instance.socket.connectToHost("192.168.102.121", 5000)
            if not cls._instance.socket.waitForConnected(3000):
                print(f"[SocketManager] Socket connection failed: {cls._instance.socket.errorString()}\n")
            else:
                print("[SocketManager] Socket connected.\n")
            # 전역 네트워크 스레드 생성 – 메인 스레드에서 작동
            cls._instance.network_thread = NetworkThread(cls._instance.socket)
            cls._instance.network_thread.start()
        return cls._instance

    def send_data(self, data):
        if self._instance.socket.state() == QTcpSocket.ConnectedState:
            # 전송할 데이터를 JSON 문자열로 만들어 접두어("admin/")를 붙임
            send_data = "admin/" + json.dumps(data)
            print(f"[SocketManager] Sending: {send_data}\n")
            self._instance.socket.write(send_data.encode('utf-8'))
            self._instance.socket.flush()
        else:
            print("[SocketManager] Socket is not connected.\n")

    def get_receiver(self):
        return self._instance.network_thread

# ------------------------------------------------------------------
# NetworkThread: QTcpSocket의 readyRead 시그널을 처리하여 데이터를 emit하는 클래스
# ------------------------------------------------------------------
class NetworkThread(QThread):
    data_received = pyqtSignal(str)
    
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        # 메인 스레드에서 작동하므로 바로 readyRead에 연결
        self.socket.readyRead.connect(self.read_response)
    
    def read_response(self):
        data = self.socket.readAll().data().decode('utf-8').strip()
        if data:
            print(f"[NetworkThread] Raw received data: {data}\n")
            # 여러 JSON 객체가 연속되어 있을 경우 개별적으로 분리
            json_objects = self.split_json_objects(data)
            for obj in json_objects:
                print(f"[NetworkThread] Parsed JSON object: {obj}\n")
                self.data_received.emit(obj)
    
    def split_json_objects(self, data):
        """Brace 카운팅 방식으로 연속된 JSON 문자열을 분리."""
        objects = []
        brace_count = 0
        start_index = None
        in_string = False
        escape = False
        
        for i, char in enumerate(data):
            if char == '"' and not escape:
                in_string = not in_string
            if not in_string:
                if char == '{':
                    if brace_count == 0:
                        start_index = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_index is not None:
                        objects.append(data[start_index:i+1])
                        start_index = None
            if char == '\\' and not escape:
                escape = True
            else:
                escape = False
        return objects

# ------------------------------------------------------------------
# CameraThread: CCTV 스트림을 읽어 QImage로 변환하여 emit (cv2 필요)
# ------------------------------------------------------------------
class CameraThread(QThread):
    frame_update = pyqtSignal(QImage)

    def __init__(self, stream_url):
        super().__init__()
        self.stream_url = stream_url
        self.running = True
        self.recording = False  # 녹화 여부
        self.video_writer = None  # 비디오 저장 객체

    def run(self):
        cap = cv2.VideoCapture(self.stream_url)
        if not cap.isOpened():
            print("[CameraThread] Failed to connect to camera stream\n")
            return
        while self.running:
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qimage = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.frame_update.emit(qimage)
            else:
                print("[CameraThread] Failed to read frame\n")
        cap.release()

    def stop(self):
        self.running = False

# 화재 감지 녹화
    def start_recording(self):
        if not self.recording:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"cctv/fire_event_{timestamp}.avi"
            cap = cv2.VideoCapture(self.stream_url)
            width = int(cap.get(3))
            height = int(cap.get(4))
            self.video_writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*"XVID"), 20.0, (width, height))
            self.recording = True
            print(f"[CameraThread] 녹화 시작: {filename}")

    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            print("[CameraThread] 녹화 종료")       



# ------------------------------------------------------------------
# adminLoginWindow: 관리자 로그인 창 (UI 파일 main/adminLogin.ui 필요)
# ------------------------------------------------------------------
class adminLoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/adminLogin.ui", self)
        # 공유 소켓 사용
        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)
        self.Loginbtn.clicked.connect(self.checkadmin)
        self.id = ""   # 예시 ID (필요시 수정)
        self.pw = ""   # 예시 PW (필요시 수정)
        self.last_response = None

    def checkadmin(self):
        input_id = self.IDEdit.text() if isinstance(self.IDEdit, QLineEdit) else ""
        input_pw = self.PWEdit.text() if isinstance(self.PWEdit, QLineEdit) else ""
        print(f"[adminLoginWindow] 입력된 ID: {input_id}, PW: {input_pw}\n")
        if input_id == self.id and input_pw == self.pw:
            print("[adminLoginWindow] 로그인 성공. 관리자 창 오픈.\n")
            self.open_admin_window()
        else:
            print("[adminLoginWindow] 로그인 실패.\n")
            QMessageBox.warning(self, "로그인 실패", "ID 또는 비밀번호가 다릅니다.")

    def open_admin_window(self):
        stream_url = "http://192.168.102.150:5000/feed2"
        self.admin_window = WindowClass(stream_url)
        self.admin_window.show()
        self.close()

    def handle_response(self, response):

        try:
            response_message = json.loads(response)
            if response_message.get("client", "") == "adminLoginWindow":
                response_data = json.loads(response_message.get("data", "{}"))
                if response_data is not None and response_data:
                    print(f"[adminLoginWindow] 서버 응답: {response}\n")                
                # else:
                #     QMessageBox.information(self, "응답", f"서버 메시지: {response_message.get('message', '응답 없음')}")
        except Exception as e:
            print(f"[adminLoginWindow] 예외 발생: {e}")


# ------------------------------------------------------------------
# WindowClass: 메인 창 (UI 파일 main/main.ui 필요)
# ------------------------------------------------------------------
from_class = uic.loadUiType("main/main.ui")[0]
class WindowClass(QMainWindow, from_class):
    def __init__(self, stream_url):
        super().__init__()
        self.setupUi(self)
        self.pixmap = QPixmap()
        self.last_response = None

        self.Startdate.setCalendarPopup(True)
        self.Startdate.setDate(QDate.currentDate())
        self.Enddate.setCalendarPopup(True)
        self.Enddate.setDate(QDate.currentDate())

        # CCTV 제어
        self.camera_thread = CameraThread(stream_url)
        self.camera_thread.frame_update.connect(self.updateCamera)
        self.camera_thread.start()
        
        # 버튼 연결
        self.UserInfobtn.clicked.connect(self.EnterUserInfo)
        self.btnSearch.clicked.connect(self.selectInOutHistory)
        self.eventbtn.clicked.connect(self.EnterEventInfo)
        
        # 공유 소켓 사용
        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)
        self.Start()

        # 미니맵 및 LED 이미지 설정
        self.pixmap.load('data/minimapimg.png')
        self.minimap.setPixmap(self.pixmap)
        # QLabel 크기에 맞게 이미지 조정
        self.scaled_pixmap = self.pixmap.scaled(self.minimap.size(), 
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.minimap.setPixmap(self.scaled_pixmap)
        self.minimap.resize(self.scaled_pixmap.width(), self.scaled_pixmap.height())
    
        self.parkingstate = QPixmap("data/parkingimg.png")
        self.vacantstate = QPixmap("data/vacant.png")
        self.displayLed1.setPixmap(self.vacantstate)
        self.displayLed2.setPixmap(self.vacantstate)
        self.displayLed3.setPixmap(self.vacantstate)
        self.displayLed4.setPixmap(self.vacantstate)
        self.getParkingstate()

        self.Edit1.setVisible(False)
        self.Edit2.setVisible(False)
        self.Edit3.setVisible(False)
        self.Edit4.setVisible(False)


    def Start(self):
        user_data = {
            "client": "WindowClass",   # 식별자 추가
            "park_id": 1,
            "type": "ping"
        }
        print(f"[WindowClass] Start() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)

    def selectInOutHistory(self):
        user_data = {
            "client": "WindowClass",   # 식별자 추가
            "park_id": 1,
            "type": "selectInOutHistory",
            "user_name": self.editName.text(),
            "indatetime_start ": self.Startdate.date().toString("yyyy-MM-dd"),
            "indatetime_end": self.Enddate.date().toString("yyyy-MM-dd"),
            "inout_car_number": self.editCarnum.text(),
        }
        print(f"[WindowClass] selectInOutHistory() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)

    def getParkingstate(self):
        user_data = {"client": "WindowClass", "park_id": 1, "type": "selectSpaceState"}
        print(f"[WindowClass] getParkingstate() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)

    def handle_response(self, response):
        try:
            response_message = json.loads(response)  # response가 문자열일 경우 JSON 변환
            if response_message.get("client", "") == "WindowClass":
                response_data = response_message.get("data", [])

                response_type = response_message.get("type", "")
                if response_type == "firedetect":
                    print(f"[WindowClass] 🔥 화재 감지! 감지 위치: {response_data}")
                    self.fireEvent(response_data)  # 팝업 띄우기 & 위치 전달
                    #녹화시작
                    self.camera_thread.start_recording()
                    return  # 화재 감지는 중복 체크 없이 여기서 종료
                if response_type == "selectSpaceState": 
                    self.minipopup(response_data)
                    if isinstance(response_data, list):  # 서버에서 리스트로 보내는 경우
                        # 리스트 데이터를 딕셔너리 형태로 변환하여 minimapdisplay 호출
                        minimap_data = {item["space_name"]: item["state"] for item in response_data}
                        print(f"[WindowClass] 변환된 미니맵 데이터: {minimap_data}\n")
                        self.minimapdisplay(minimap_data)  # 변환한 데이터를 minimapdisplay()에 전달
                else:
                    self.visibleInOutHistory(response_data)
        
        except json.JSONDecodeError:
            print(f"[WindowClass] JSON 파싱 오류: {response}")
        
        except Exception as e:
            print(f"[WindowClass] 예외 발생: {e}")


    def minimapdisplay(self, response_data):
        led_mapping = {
            "space1": self.displayLed1,
            "space2": self.displayLed2,
            "space3": self.displayLed3,
            "space4": self.displayLed4
        }
        if not isinstance(response_data, dict):
            print(f"[WindowClass] 응답 형식 오류: {response_data}\n")
            return
        for space, state in response_data.items():
            led_label = led_mapping.get(space)
            if led_label:
                if state == 0:
                    led_label.setPixmap(self.parkingstate)
                    # #마우스 이벤트
                    led_label.installEventFilter(self)

                else:
                    led_label.setPixmap(self.vacantstate)

                    #마우스 이벤트 
                    led_label.mouseMoveEvent = None
                    self.hideCarInfo(None, space)
                    led_label.removeEventFilter(self)
    
    #팝업 관련 

    def minipopup(self, response_data):
        """ 차량 정보를 latest_state에 저장 """
        self.latest_state = {item["space_name"]: item for item in response_data}  # 전체 정보 저장
        # print( "[minipopup data] 미니팝업에 저장된 데이터 : ",  self.latest_state)        
    
    def eventFilter(self, obj, event):
        """ 마우스 hover 이벤트 처리 """
        led_mapping = {
            "space1": self.displayLed1,
            "space2": self.displayLed2,
            "space3": self.displayLed3,
            "space4": self.displayLed4
        }
        
        space = next((key for key, val in led_mapping.items() if val == obj), None)
        
        if space:
            if event.type() == QEvent.Enter:  # 마우스가 올라왔을 때
                self.showCarInfo(event, space)
            elif event.type() == QEvent.Leave:  # 마우스가 벗어났을 때
                self.hideCarInfo(event, space)
                
        return super().eventFilter(obj, event)   

                    
    def showCarInfo(self, event, space):
        """ 마우스를 올렸을 때 차량 정보 표시 """
        edit_mapping = {
            "space1": self.Edit1,
            "space2": self.Edit2,
            "space3": self.Edit3,
            "space4": self.Edit4
        }
        
        if space in edit_mapping and space in self.latest_state:
            edit_widget = edit_mapping[space]
            car_info = self.latest_state[space]  
            print(f"[DEBUG] space={space}, car_info={car_info}")
            
            if car_info:
                edit_widget.setText(f"{car_info['user_name']} / {car_info['car_number']}")
                edit_widget.setVisible(True)
            else:
                print(f"[ERROR] 차량 정보 없음: space={space}")

    def hideCarInfo(self, event, space):

        edit_mapping = {
            "space1": self.Edit1,
            "space2": self.Edit2,
            "space3": self.Edit3,
            "space4": self.Edit4
        }
        
        if space in edit_mapping:
            edit_widget = edit_mapping[space]
            edit_widget.setVisible(False)  # 숨김 처리
                    
    def visibleInOutHistory(self, response_data):
        if not isinstance(response_data, list) or not response_data:
            print("[WindowClass] 유효한 입출차 데이터가 없음.")
            self.InoutTable.setRowCount(0)
            return
            
        columns = ["user_name", "indatetime", "outdatetime", "inout_car_number", "inout_car_uuid"]
        column_headers = ["이름", "입차 시간", "출차 시간", "차 번호", "차 UUID"]
        
        self.InoutTable.setRowCount(len(response_data))
        self.InoutTable.setColumnCount(len(columns))
        self.InoutTable.setHorizontalHeaderLabels(column_headers)
        for row, item in enumerate(response_data):
            for col, key in enumerate(columns):
                value = item.get(key, "없음")  # None 값 대비 기본값 설정
                self.InoutTable.setItem(row, col, QTableWidgetItem(str(value)))
        
        self.InoutTable.resizeColumnsToContents()
        
        self.InoutTable.setColumnWidth(0, 50)   # 이름
        self.InoutTable.setColumnWidth(1, 180)  # 입차 시간
        self.InoutTable.setColumnWidth(2, 180)  # 출차 시간
        self.InoutTable.setColumnWidth(3, 120)  # 차 번호
        self.InoutTable.setColumnWidth(4, 150)  # 차 UUID
        
        self.InoutTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
    def EnterUserInfo(self):
        print("[WindowClass] EnterUserInfo() 호출\n")
        self.userinfo_window = UserInfoWindow()
        self.userinfo_window.show()

    def updateCamera(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.cctv.setPixmap(pixmap)

    def closeEvent(self, event):
        print("[WindowClass] 창 종료. 카메라 스레드 중지.\n")
        self.camera_thread.stop()
        event.accept()
    
        # 이벤트 기록 창 열기 
    def EnterEventInfo(self): 
        self.event_window = EventWindow()
        self.event_window.show()

    def fireEvent(self, fire_location):
        print(f"[WindowClass] 화재 감지! firepopup 창 띄우기 (위치: {fire_location})") 
        self.firepopup_window = firepopup(fire_location, self)  # 위치 전달
        self.firepopup_window.confirmbtn.clicked.connect(self.stopRecording)  # 확인 버튼 연결
        self.firepopup_window.show()
    
    def stopRecording(self):
        print("[WindowClass] 화재 이벤트 종료 - 녹화 중지")
        self.camera_thread.stop_recording()


# ------------------------------------------------------------------
# UserInfoWindow: 회원 정보 창 (UI 파일 main/UserInfo.ui 필요)
# ------------------------------------------------------------------

class UserInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/UserInfo.ui", self)
        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)

        self.SignUserInfobtn.clicked.connect(self.openSignUserInfo)
        self.updateUserInfobtn.clicked.connect(self.OpenupdateUserInfo)

        self.searchbtn.clicked.connect(self.selectUserInfo)
        self.conformbtn.clicked.connect(self.close)
        self.last_response = None

    def selectUserInfo(self):
        user_data = {
            "client": "UserInfoWindow",  # 식별자 추가
            "park_id": 1,
            "type": "selectUserInfo",
            "user_name": self.nameEdit.text(),
            "car_number": self.carnumEdit.text()
        }
        print(f"[UserInfoWindow] selectUserInfo() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)

    def openSignUserInfo(self):
        print("[UserInfoWindow] openSignUserInfo() 호출\n")
        self.SignUserInfoWindow = SignUserInfoWindow()
        self.SignUserInfoWindow.show()

    def OpenupdateUserInfo(self):
        print("[UserInfoWindow] OpenupdateUserInfo() 호출\n")
        self.updateUserInfoWindow = updateUserInfoWindow()
        self.updateUserInfoWindow.show()

    def handle_response(self, response):

        try:
            response_message = json.loads(response)
            if response_message.get("client", "") == "UserInfoWindow":
                response_data = response_message.get("data", [])  # "data" 키 값을 직접 가져옴
                
                print(f"[UserInfoWindow] 서버 응답: {response_data}\n")
                self.visibleUserInfo(response_data)
        except json.JSONDecodeError as  e:
            print(f"[UserInfoWindow] JSON 디코딩 오류 발생: {e}")
        except Exception as e:
            print(f"[UserInfoWindow] 예외 발생: {e}")

    def visibleUserInfo(self, response_data):
        # 필요한 키 목록
        required_keys = ["user_name", "car_number", "car_uuid", "user_phone", "car_category", "pass_start_date", "pass_expiration_date"]
        
        # 테이블 컬럼 헤더 설정
        column_names = ["이름", "차량 번호", "차량 UUID", "전화번호", "차량 종류", "정기권 시작일", "정기권 만기일"]

        # 필요한 데이터만 추출
        filtered_data = [
            {key: item[key] for key in required_keys if key in item}
            for item in response_data
        ]

        # 테이블 행/열 설정
        self.Usertable.setRowCount(len(filtered_data))  # 행 개수 설정
        self.Usertable.setColumnCount(len(column_names))  # 컬럼 개수 설정
        self.Usertable.setHorizontalHeaderLabels(column_names)  # 헤더 설정

        # 데이터 삽입
        for row, item in enumerate(filtered_data):
            for col, key in enumerate(required_keys):
                self.Usertable.setItem(row, col, QTableWidgetItem(str(item.get(key, ""))))  # 데이터 삽입

        self.Usertable.resizeColumnsToContents()        
        self.Usertable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        print("\n[UserInfoWindow] 전송 완료")

        
        # for item in response_data:
        #     print(f"이름: {item['user_name']}, 차량번호: {item['car_number']}")
        #     print("\n")
        #     print("------------------------------------------------------")

        # print("-----------------------------------------------------------")


# ------------------------------------------------------------------
# SignUserInfoWindow: 회원가입 창 (UI 파일 main/SignUserInfo.ui 필요)
# ------------------------------------------------------------------
class SignUserInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/SignUserInfo.ui", self)
        self.Editcategory.clear()
        self.Editcategory.addItems(["일반차", "전기차"])
        self.EditStart.setCalendarPopup(True)
        self.EditStart.setDate(QDate.currentDate())
        self.EditEnd.setCalendarPopup(True)
        self.EditEnd.setDate(QDate.currentDate())
        self.btnConfirm.clicked.connect(self.insertUserInfo)
        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)
        self.last_response = None

    def insertUserInfo(self):
        user_data = {
            "client": "SignUserInfoWindow",  # 식별자 추가
            "park_id": 1,
            "type": "insertUserInfo",
            "user_name": self.Editname.text(),
            "car_number": self.Editcarnum.text(),
            "car_uuid": self.EditRFID.text(),
            "user_phone": self.Editnum.text(),
            "car_category": self.Editcategory.currentText(),
            "pass_start_date": self.EditStart.date().toString("yyyy-MM-dd"),
            "pass_expiration_date": self.EditEnd.date().toString("yyyy-MM-dd")
        }
        print(f"[SignUserInfoWindow] insertUserInfo() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)
        self.btnConfirm.clicked.connect(self.close)

    def handle_response(self, response):
        try:
            response_message = json.loads(response)
            if response_message.get("client", "") == "SignUserInfoWindow":
                response_data = response_message.get("data", {})

                # 만약 data가 문자열이면 JSON 변환
                if isinstance(response_data, str):
                    response_data = json.loads(response_data)

                if response_data:
                    print(f"[SignUserInfoWindow] 서버 응답: {response_data}\n")
                    
                    # status 값 확인 후 성공/실패 메시지 표시
                    status = response_data.get("status", "")
                    message = response_data.get("message", "응답 없음")
                    
                    if status == "success":
                        QMessageBox.information(self, "성공", f"✅ 성공: {message}")
                    elif status == "fail":
                        QMessageBox.warning(self, "실패", f"❌ 실패: {message}")
                    else:
                        QMessageBox.information(self, "알림", f"ℹ️ 응답 메시지: {message}")

        except Exception as e:
            print(f"[SignUserInfoWindow] 예외 발생: {e}")

# ------------------------------------------------------------------
# updateUserInfoWindow: 회원 정보 수정 창 (UI 파일 main/updateUserInfo.ui 필요)
# ------------------------------------------------------------------
class updateUserInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/updateUserInfo.ui", self)
        self.currentRequestType = None
        self.btnSearch.clicked.connect(self.selectUserInfo)
        self.btnupdate.clicked.connect(self.UpdateUserInfo)
        self.Editcategory.clear()
        self.Editcategory.addItems(["일반차", "전기차"])
        self.EditStart.setCalendarPopup(True)
        self.EditStart.setDate(QDate.currentDate())
        self.EditEnd.setCalendarPopup(True)
        self.EditEnd.setDate(QDate.currentDate())
        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)
        self.groupBox.setVisible(False)
        self.last_response = None

    def selectUserInfo(self):
        user_data = {
            "client": "updateUserInfoWindow",  # 식별자 추가
            "park_id": 1,
            "type": "selectUserInfo",
            "user_name": self.EditOriginName.text(),
            "car_number": self.EditOrigincarnum.text()
        }
        print(f"[updateUserInfoWindow] selectUserInfo() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)
        self.groupBox.setVisible(True)

    def UpdateUserInfo(self):
        user_data = {
            "client": "updateUserInfoWindow",  # 식별자 추가
            "park_id": 1,
            "type": "updateUserInfo",
            "user_id": self.user_id,
            "user_name": self.Editname.text(),
            "car_number": self.Editcarnum.text(),
            "car_uuid": self.Edituuid.text(),
            "user_phone": self.Editnum.text(),
            "car_category": self.Editcategory.currentText(),
            "pass_start_date": self.EditStart.date().toString("yyyy-MM-dd"),
            "pass_expiration_date": self.EditEnd.date().toString("yyyy-MM-dd")
        }
        print(f"[updateUserInfoWindow] UpdateUserInfo() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)

    def handle_response(self, response):
        print(f"[updateUserInfoWindow] Server Response: {response}\n")
        try:
            response_message = json.loads(response)
            if response_message.get("client", "") != "updateUserInfoWindow":
                print("[updateUserInfoWindow] 다른 클라이언트 응답 무시.\n")
                return
            if response_message.get("type") == "selectUserInfo":
                self.handle_select_response(json.loads(response_message.get("data", "{}")))
            elif response_message.get("type") == "updateUserInfo":
                self.handle_update_response(json.loads(response_message.get("data", "{}")))
            else:
                return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답 (JSON 파싱 실패)")
            return
   
    def handle_response(self, response):
        try:
            response_message = json.loads(response)
            if response_message.get("client", "") == "updateUserInfoWindow":                
                print(f"[updateUserInfoWindow] 서버 응답: {response}\n")  
                
                response_data = response_message.get("data", [])


                if response_message.get("type") == "selectUserInfo":
                    self.handle_select_response(response_data[0])  # 그대로 전달
                elif response_message.get("type") == "updateUserInfo":
                    self.handle_update_response(response_data)  # 그대로 전달

        except Exception as e:
            print(f"[updateUserInfoWindow] 예외 발생: {e}")


    
    def handle_select_response(self, response_data):
        print(f"[updateUserInfoWindow] handle_select_response() 응답 데이터: {response_data}\n")
        if not response_data:
            QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            return
        if isinstance(response_data, list) and response_data:
            response_data = response_data[0]
        elif not isinstance(response_data, dict):
            QMessageBox.warning(self, "오류", "조회 결과가 딕셔너리 형식이 아닙니다.")
            return
        
        self.user_id = response_data.get("user_id", "")
        self.groupBox.setVisible(True)        
        self.Editname.setText(response_data.get("user_name", ""))
        self.Editcarnum.setText(response_data.get("car_number", ""))
        self.Edituuid.setText(response_data.get("car_uuid", ""))
        self.Editnum.setText(response_data.get("user_phone", ""))
        category = response_data.get("car_category", "일반차")
        if category in ["일반차", "전기차"]:
            self.Editcategory.setCurrentText(category)
        else:
            self.Editcategory.setCurrentIndex(0)
        start_str = response_data.get("pass_start_date", "")
        end_str = response_data.get("pass_expiration_date", "")
        if start_str:
            try:
                year, month, day = map(int, start_str.split("-"))
                self.EditStart.setDate(QDate(year, month, day))
            except ValueError:
                pass
        if end_str:
            try:
                year, month, day = map(int, end_str.split("-"))
                self.EditEnd.setDate(QDate(year, month, day))
            except ValueError:
                pass

    def handle_update_response(self, response_data):
        print(f"[updateUserInfoWindow] handle_update_response() 응답 데이터: {response_data}\n")

        if isinstance(response_data, dict):
            status = response_data.get("status", "")
            message = response_data.get("message", "알 수 없는 오류가 발생했습니다.")

            if status == "success":
                QMessageBox.information(self, "성공", message)  # 성공 메시지 표시
                self.close()
            elif status == "fail":
                QMessageBox.warning(self, "실패", message)  # 실패 메시지 표시
            else:
                QMessageBox.warning(self, "오류", "잘못된 응답 형식입니다.")
        else:
            QMessageBox.warning(self, "오류", "서버 응답이 올바르지 않습니다.")
# ------------------------------------------------------------------
# eventWindow: 이벤트 창 (UI 파일 main/EventInfo.ui 필요)
# ------------------------------------------------------------------
class EventWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/EventInfo.ui", self)
        self.searchbtn.clicked.connect(self.selectEvent)
        self.conformbtn.clicked.connect(self.close)

        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)
        self.last_response = None

        # 콤보박스
        self.comboBox.clear()
        self.comboBox.addItems(["화재"])
        category_mapping = {
            "화재": "flame",
        }
        self.event_category = self.comboBox.currentText()
        self.event_category = category_mapping.get(self.event_category, self.event_category)  # 변환된 값 사용
        
        # 캘린더 
        self.EditStart.setCalendarPopup(True)
        self.EditStart.setDate(QDate.currentDate())
        self.EditEnd.setCalendarPopup(True)
        self.EditEnd.setDate(QDate.currentDate())

    def selectEvent(self):
        user_data = {
            "client": "eventWindow",  # 식별자 추가
            "park_id": 1,
            "type": "selectEvent",
            "event_category": self.event_category,
            "date_start": self.EditStart.date().toString("yyyy-MM-dd"),
            "date_end": self.EditEnd.date().toString("yyyy-MM-dd")
        }
        
        print(f"[updateEventWindow] selectEventInfo() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)
        
    def handle_response(self, response):
        try:
            response_message = json.loads(response)
        
        except json.JSONDecodeError as e:
            print(f"[UserInfoWindow] JSON 디코딩 오류 발생: {e}")
            return
        
        try:
            if response_message.get("client") == "eventWindow":
                response_data = response_message.get("data", [])  
                print(f"[EventInfoWindow] 서버 응답: {response_data}\n")
                self.visibleEventInfo(response_data)
        except Exception as e:
            print(f"[EventWindow] 예외 발생: {e}")
    
    def visibleEventInfo(self, response_data):
        required_keys = ["event_id", "space_id", "event_start_time", "event_category", "event_info"]
        column_names = ["이벤트 ID", "공간 ID", "시작 시간", "이벤트 유형", "이벤트 정보"]
        
        filtered_data = [{key: str(item.get(key, "")) for key in required_keys} for item in response_data]
        self.eventTable.setRowCount(len(filtered_data))
        self.eventTable.setColumnCount(len(column_names))
        self.eventTable.setHorizontalHeaderLabels(column_names)
        
        for row, item in enumerate(filtered_data):
            for col, key in enumerate(required_keys):
                self.eventTable.setItem(row, col, QTableWidgetItem(item[key]))
                
        self.eventTable.resizeColumnsToContents()
        self.eventTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        print("\n[EventWindow] 데이터 테이블 업데이트 완료")

# ------------------------------------------------------------------
# Firepopup: 화재이벤트팝업 (UI 파일 main/fire.ui 필요)
# ------------------------------------------------------------------
class firepopup(QMainWindow):
    def __init__(self, response_data, main_window):
        super().__init__()
        uic.loadUi("main/fire.ui", self)  # UI 파일 로드
        self.setWindowTitle("🔥 화재 경보")
        self.main_window = main_window

        # lineEdit 찾기
        self.label = self.findChild(QLabel, "label")
        if self.label:  
            self.label.setText(str(response_data))  # 받은 데이터 표시

        # 확인 버튼 클릭 시 화재 녹화 중지 이벤트 발생 
        #원래는 self.close만 줬다.
        self.confirmbtn.clicked.connect(self.CloseFireEvent)

    def CloseFireEvent(self):
        self.main_window.stopRecording()
        self.close()



# ------------------------------------------------------------------
# 메인 실행부
# ------------------------------------------------------------------
if __name__ == "__main__":
    stream_url = "http://192.168.102.150:5000/feed2"
    app = QApplication(sys.argv)
    myWindows = adminLoginWindow()
    myWindows.show()
    sys.exit(app.exec_())