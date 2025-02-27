import sys
import json
import time
import warnings
import cv2  # CameraThread에서 사용
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread, pyqtSignal, QDate
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QHeaderView, QLineEdit, QDateTimeEdit
from PyQt5.QtGui import QPixmap, QImage
from PyQt5 import uic
from PyQt5.QtNetwork import QTcpSocket
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDateTime 

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
            cls._instance.socket.connectToHost("192.168.0.21", 5000)
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


class WindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("user/user.ui", self)
        self.currentRequestType = None
        self.btnSearch.clicked.connect(self.selectInOutHistory)
        self.btnConfirm.clicked.connect(self.close)


        self.EditStart.setCalendarPopup(True)
        self.EditStart.setDate(QDate.currentDate())
        self.EditEnd.setCalendarPopup(True)
        self.EditEnd.setDate(QDate.currentDate())
        
        #입차 시간 
        self.EditIntime.setCalendarPopup(True)
        self.EditOuttime.setCalendarPopup(True)

        self.network_manager = SocketManager()
        self.network_manager.get_receiver().data_received.connect(self.handle_response)
        self.groupBox.setVisible(False)
        self.Parking.setVisible(False)
        self.OUT.setVisible(False)
        self.last_response = None

    def selectInOutHistory(self):
        # UI 초기화
        self.groupBox.setVisible(False)
        self.Parking.setVisible(False)
        self.OUT.setVisible(False)
        
        user_data = {
            "client": "UserWindow",  # 식별자 추가
            "park_id": 1,
            "type": "selectUserHistory",
            "car_number": self.editCarnum.text()
        }
        
        print(f"[updateUserInfoWindow] selectUserInfo() 요청 전송: {user_data}\n")
        self.network_manager.send_data(user_data)
        self.groupBox.setVisible(True)
        
    def handle_response(self, data):
        try:
            response = json.loads(data)
            if response.get("type") == "selectUserHistory":
                history_data = response.get("data", [])
                if not history_data:  # 데이터가 비어있다면
                    QMessageBox.warning(self, "알림", "해당하는 유저 정보가 없습니다.")
                    return
                
                history = history_data[0]  # 첫 번째 데이터 사용
                # 입차/출차 시간 가져오기 (기본값: "0000-00-00 00:00:00")
                indatetime = history.get("indatetime", "0000-00-00T00:00:00")
                outdatetime = history.get("outdatetime", "0000-00-00T00:00:00")
                
                # QDateTime으로 변환
                intime_dt = QDateTime.fromString(indatetime, "yyyy-MM-ddTHH:mm:ss")
                outtime_dt = QDateTime.fromString(outdatetime, "yyyy-MM-ddTHH:mm:ss")
                
                # UI 업데이트
                self.EditIntime.setDateTime(intime_dt)
                self.EditOuttime.setDateTime(outtime_dt)
                
                pass_start_date = history.get("pass_start_date", "0000-00-00")
                pass_expiration_date = history.get("pass_expiration_date", "0000-00-00")
                
                self.EditStart.setDate(QDate.fromString(pass_start_date, "yyyy-MM-dd"))
                self.EditEnd.setDate(QDate.fromString(pass_expiration_date, "yyyy-MM-dd"))
                
                # 입차/출차 여부에 따라 Parking, OUT 표시 조정
                has_indatetime = indatetime != "0000-00-00T00:00:00"
                has_outdatetime = outdatetime != "0000-00-00T00:00:00"
                
                self.Parking.setVisible(has_indatetime)  # 입차 기록이 있으면 Parking 표시
                self.OUT.setVisible(has_indatetime and has_outdatetime)  # 출차 기록까지 있으면 OUT 표시
                
                self.groupBox.setVisible(True)  # 데이터가 있을 때만 표시
            
        except json.JSONDecodeError as e:
            print(f"[WindowClass] JSON Decode Error: {e}\n")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindows = WindowClass()
    myWindows.show()
    sys.exit(app.exec_())

