import sys 
import json
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import cv2, imutils
import time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtNetwork import QTcpSocket, QHostAddress
from PyQt5.QtCore import QTimer

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from_class = uic.loadUiType("main/main.ui")[0]

# const
PARK_SEQ = 1 

#주차장 상태 받아오기 위한 설정 
#  0 = vacant, 1 = occupy, 2 = charge 3= fire
entrancedoor = 0 
exitdoor = 0
park_1 = 0
park_2 = 0
park_3 = 0
park_4 = 0


class CameraThread(QThread):
    frame_update = pyqtSignal(QImage)

    def __init__(self, stream_url):
        super().__init__()
        self.stream_url = stream_url
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.stream_url)
        if not cap.isOpened():
            print("Failed to connect to camera stream")
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
                print("Failed to read frame")

        cap.release()

    def stop(self):
        self.running = False

# :small_blue_diamond: 싱글톤 패턴을 사용한 소켓 매니저 (소켓 1개만 사용)
class SocketManager:
    _instance = None  # 싱글톤 인스턴스
    socket = None     # 공유 소켓 객체
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SocketManager, cls).__new__(cls)
            cls.socket = QTcpSocket()  # 하나의 소켓만 생성
            cls.socket.connectToHost(QHostAddress("192.168.0.22"), 5000)
            if not cls.socket.waitForConnected(3000):  # 3초 대기 후 연결 확인
                print(":x: 서버 연결 실패:", cls.socket.errorString())
        return cls._instance
    def send_data(self, json_data):
        """ 데이터를 서버에 JSON 형식으로 전송 """
        if self.socket.state() == QTcpSocket.ConnectedState:
            send_data = "admin/"+json.dumps(json_data)
            print(f":outbox_tray: Sending: {send_data}")
            self.socket.write(send_data.encode('utf-8'))
            self.socket.flush()
        else:
            print(":x: 소켓 연결이 끊어졌습니다.")

# :small_blue_diamond: 소켓에서 응답을 수신하는 스레드
class SocketThread(QThread):
    data_received = pyqtSignal(str)  # UI에 전달할 데이터 시그널
    def __init__(self):
        super().__init__()
        self.socket = SocketManager().socket  # 공유 소켓 사용
        self.is_running = True
    def run(self):
        while self.is_running:
            if self.socket.waitForReadyRead(3000):  # 최대 3초 대기
                response = self.socket.readAll().data().decode('utf-8').strip()
                if response:
                    self.data_received.emit(response)
    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()

# :small_blue_diamond: 회원가입 UI
class SignWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/sign.ui", self)
        self.btnSign.clicked.connect(self.signup)
        # 공유 소켓을 사용하는 응답 수신 스레드 실행
        self.socket_thread = SocketThread()
        self.socket_thread.data_received.connect(self.handle_response)
        self.socket_thread.start()
    def signup(self):
        user_data = {
            "park_seq": PARK_SEQ,
            "type": "SingUp",
            "user_name": self.Editname.text(),
            "car_number": self.Editcarnum.text(),
            "car_rfid": self.EditRFID.text(),
            "user_phone": self.Editnum.text(),
            "car_category": self.Editcategory.text(),
            "pass_expiration_date": self.EditEnd.text()
        }
        SocketManager().send_data(user_data)

    def handle_response(self, response):
        """ 서버에서 받은 응답을 UI에 표시 """
        print(":inbox_tray: 서버 응답:", response)
        try:
            response_data = json.loads(response)
            QMessageBox.information(self, "응답", f"서버 메시지: {response_data.get('message', '응답 없음')}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")
    def closeEvent(self, event):
        """ 창을 닫을 때 스레드 종료 """
        self.socket_thread.stop()
        event.accept()

# 주차장 설정 
class SettingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/setting.ui", self)

        self.btnSettingConfirm.clicked.connect(self.parksetting)
        self.socket = QTcpSocket(self)

    def parksetting(self):

        user_data = {
            "park_seq":PARK_SEQ,
            "type" : "parking_setting",
            "park_name" : self.editparkname.text()
        }

        json_data = "admin/"+json.dumps(user_data)
        print("Sending : ", json_data)

        self.socket.connectToHost(QHostAddress("192.168.0.22"), 5000) 
        
        if self.socket.waitForConnected(3000):  # 3초 대기
            self.socket.write(json_data.encode('utf-8'))
            self.socket.flush()
            print("주차장 설정 데이터 전송 완료")

            QTimer.singleShot(100, self.close)
        else:
            print("서버 연결 실패:", self.socket.errorString())
            QTimer.singleShot(100, self.close)


# 정보 수정 
class ModifyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/modify.ui", self)

        self.btnModify.clicked.connect(self.modify)
        self.socket = QTcpSocket(self)
        
        self.groupBox.setVisible(False)  # 처음엔 숨김


    def modify(self):

        user_data = {
            "park_seq":PARK_SEQ,
           "type" : "modify",
            "user_name": self.EditMname.text(),
            "car_number": self.EditMcarnum.text()
        }

        json_data = "admin/"+json.dumps(user_data)
        print("Sending : ", json_data)

        self.socket.connectToHost(QHostAddress("192.168.0.22"), 5000) 
        
        if self.socket.waitForConnected(3000):  # 3초 대기
            self.socket.write(json_data.encode('utf-8'))
            self.socket.flush()
            print("정보 수정 데이터 전송 완료")

        else:
            print("서버 연결 실패:", self.socket.errorString())


#화재경보 
# class FireWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         uic.loadUi("main/fire.ui", self)
        
#         self.conformbtn.clicked.



class WindowClass(QMainWindow, from_class):
    def __init__(self, stream_url):
        super().__init__()
        self.setupUi(self)  # UI 설정 적용

        self.pixmap = QPixmap()

        # CCTV 제어
        self.camera_thread = CameraThread(stream_url)
        self.camera_thread.frame_update.connect(self.updateCamera)
        self.camera_thread.start()

        #BTN
        self.btnEntrance.clicked.connect(self.EntranceDoor) # 입구열림
        self.btnExit.clicked.connect(self.ExitDoor) # 출구 열림
        self.btnSetting.clicked.connect(self.OpenSetting) # 주차장 설정  
        self.btnSign.clicked.connect(self.OpenSign) # 회원가입
        self.btnModify.clicked.connect(self.OpenModify) # 정보 수정
        # self.btnSearch.clicked.connect(self.OpenSearch) # 조회버튼

        # TCP / IP 
        self.socket = QTcpSocket(self)
        ip = '192.168.0.22'
        port = int(5000)

        self.socket.connectToHost(QHostAddress(ip), port)
        self.socket.readyRead.connect(self.read_response)
        # self.socket.errorOccurred.connect(self.display_error)

        #미니맵 배경
        self.pixmap = QPixmap()
        self.pixmap.load('data/minimap.png')
        self.minimap.setPixmap(self.pixmap)
        self.minimap.resize(self.pixmap.width(), self.pixmap.height())

    #     self.minimap_display() 

    # def minimap_display(self):
    #     # 아래 것들 TCP/IP로 전부 값 받아오기 
    #     # 0 = x, 1 = O, 2 = charge 3= fire
    #     entrancedoor == 0 
    #     exitdoor == 0
    #     park_1 == 0
    #     park_2 == 0
    #     park_3 == 0
    #     park_4 == 0 

        
        
        



    #입구 열림
    def EntranceDoor(self):
        message = 'admin/INOPEN'
        if not self.socket.isOpen():
            self.socket.connectToHost(QHostAddress('192.168.2.235'), 5000)
        if self.socket.waitForConnected(3000):
            bytes_written = self.socket.write(message.encode('utf-8'))
            self.socket.flush()
            if bytes_written > 0:
                print("Entrance door command sent.")
            else:
                print("Failed to send the message.")
        else:
            print(f"Connection failed: {self.socket.errorString()}")

    #출구 열림 
    def ExitDoor(self):
        message = 'admin/OUTOPEN'
        if not self.socket.isOpen():
            self.socket.connectToHost(QHostAddress('192.168.2.235'), 5000)
        if self.socket.waitForConnected(3000):
            bytes_written = self.socket.write(message.encode('utf-8'))
            self.socket.flush()
            if bytes_written > 0:
                print("Entrance door command sent.")
            else:
                print("Failed to send the message.")
        else:
            print(f"Connection failed: {self.socket.errorString()}")

    def read_response(self):
        response = self.socket.readAll().data().decode('utf-8')
        print(f"Server Response: {response}")


    #화재경보 열기 
    # #TCP/IP로 받아와서 
    # def OpenFire(self):
    #     ip = '192.168.2.235'
    #     port = int('5000')
    #     message = '1'

    #     self.socket.connectToHost(QHostAddress(ip), port)

    #     if self.socket.waitForConnected(3000):
    #         self.socket.write(message.encode('utf-8'))
    #         self.socket.flush()
    #     else:
    #         self.response_area.append('Fail!')




    # 주차장 설정 새 창 열기 
    def OpenSetting(self):
        self.setting_window = SettingWindow()
        self.setting_window.show()


    
    # 회원가입 창 열기 
    def OpenSign(self):
        self.sign_window = SignWindow()
        self.sign_window.show()

    
    # 정보 수정 창 열기 
    def OpenModify(self): 
        self.modify_window = ModifyWindow()
        self.modify_window.show()

    
    # cctv
    def cameraStart(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.cctv.setPixmap(pixmap)
        
    def updateCamera(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.cctv.setPixmap(pixmap)
        
    def closeEvent(self, event):
        self.camera_thread.stop()
        event.accept()
    


if __name__ == "__main__":
    stream_url = "http://172.28.219.150:5001/feed1"
    app = QApplication(sys.argv)
    myWindows = WindowClass(stream_url)
    myWindows.show()
    sys.exit(app.exec_())