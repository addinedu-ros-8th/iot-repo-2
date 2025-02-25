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
from PyQt5.QtCore import QDate
from PyQt5.QtCore import QTimer

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from_class = uic.loadUiType("main/main.ui")[0]

socket_url = "192.168.0.22"

Park_ID =1

class CameraThread(QThread):
    frame_update = pyqtSignal(QImage)

    def __init__(self, ):
        super().__init__()
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

class NetworkThread(QThread):
    """ 서버와 통신하는 스레드 """
    data_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.socket = QTcpSocket()
        self.socket.readyRead.connect(self.read_response)

    def connect_server(self, ip="192.168.0.22", port=5000):
        self.socket.connectToHost(ip, port)
        if not self.socket.waitForConnected(3000):  
            print("서버 연결 실패:", self.socket.errorString())

    def send_data(self, json_data):
        """ 서버에 JSON 데이터 전송 """
        if self.socket.state() == QTcpSocket.ConnectedState:
            send_data = "admin/" + json.dumps(json_data)
            print(f"Sending: {send_data}")
            self.socket.write(send_data.encode('utf-8'))
            self.socket.flush()
        else:
            print("소켓 연결 끊김")

    def read_response(self):
        """ 서버 응답 읽기 """
        response = self.socket.readAll().data().decode('utf-8').strip()
        if response:
            self.data_received.emit(response)

class WindowClass(QMainWindow, from_class):
    def __init__(self, stream_url):
        super().__init__()
        self.setupUi(self)  # UI 설정 적용

        self.pixmap = QPixmap()

        # CCTV 제어
        self.camera_thread = CameraThread(stream_url)
        self.camera_thread.frame_update.connect(self.updateCamera)
        self.camera_thread.start()
        
        #카메라 움직이기 

        #BTN
        # self.UserInfobtn.clicked.connect(self.EnterUserInfo) # 유저 정보 
        self.btnSearch.clicked.connect(self.selectInOutHistory) # 조회버튼

        
      # 네트워크 스레드
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()

        self.Start()


    # 유저 데이터 
        self.eventcombo.clear()
        self.eventcombo.addItems(["일반", "화재", "미정기"])  

        # 날짜 선택 위젯 설정
        self.dateStart.setCalendarPopup(True)  # 달력 팝업 활성화
        self.dateStart.setDate(QDate.currentDate())  # 기본값: 오늘 날짜
        self.dateEnd.setCalendarPopup(True)  # 달력 팝업 활성화
        self.dateEnd.setDate(QDate.currentDate())  # 기본값: 오늘 날짜


    #미니맵 초기 세팅
        self.pixmap = QPixmap()
        self.pixmap.load('data/minimap.png')
        self.minimap.setPixmap(self.pixmap)
        self.minimap.resize(self.pixmap.width(), self.pixmap.height())

        self.parkingstate = QPixmap("data/parkingimg.png")
        self.vacantstate = QPixmap("data/vacant.png")
        """기본 상태 vacant 세팅"""
        self.displayLed1.setPixmap(self.vacantstate)
        self.displayLed2.setPixmap(self.vacantstate)
        self.displayLed3.setPixmap(self.vacantstate)
        self.dispalyLed4.setPixmap(self.vacantstate)

        self.minimapdisplay()

    def handle_response(self, response):
        print(f"Server Response: {response}")
        try:
            response_data = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON 디코딩 오류: {e}")
            response_data = response
            
        # response_data가 dict인 경우 parking state 체크
        if isinstance(response_data, dict):
            # 주차 상태 관련 키가 있는지 확인
            if all(key in response_data for key in ["space1", "space2", "space3", "space4"]):
                self.update_minimap(response_data)
            else:
                # 예: user_name, car_number 등 다른 데이터 처리
                self.editName.setText(response_data.get("user_name", ""))
                self.editCarnum.setText(response_data.get("car_number", ""))
                self.visibleInOutHistory(response_data)
            
        elif isinstance(response_data, list):
            if response_data:
                first = response_data[0]
                if isinstance(first, dict) and all(key in first for key in ["space1", "space2", "space3", "space4"]):
                    self.update_minimap(first)
                    
                else:
                    if isinstance(first, dict):
                        self.editName.setText(first.get("user_name", ""))
                        self.editCarnum.setText(first.get("car_number", ""))
                    
                    self.visibleInOutHistory(response_data)
            
            else:
                QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
                
        elif isinstance(response_data, str):
            self.lineEdit.setText(response_data)
            print("서버에서 받은 단순 텍스트 응답:", response_data)
        else:
            QMessageBox.warning(self, "오류", "알 수 없는 데이터 형식의 서버 응답입니다.")
        

    # 입출차 기록 정보 보내기 
    def selectInOutHistory(self):
        """User Data 보내주기"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectInOutHistory",
            "user_name": self.editName.text(),
            "car_number": self.editCarnum.text(),
            # "event_category": self.eventcombo.currentText(),  
            "pass_start_date": self.dateStart.date().toString("yyyy-MM-dd-HH:mm:ss"), 
            "pass_expiration_date": self.dateEnd.date().toString("yyyy-MM-dd-HH:mm:ss")

        }

        self.network_thread.send_data(user_data)
        self.visibleInOutHistory()


    # 네트워크 관리 

    def Start(self):
        """시작하면 주차장 상황 정보를 받기위해 """
        user_data = {
            "admin1": 'admin1',
            "park_id" : Park_ID , 
            "type" : "ping"
        }

        self.network_thread.send_data(user_data)



    # 서버에서 DB 정보 받아와 테이블 출력 
    def visibleInOutHistory(self, response_data):
        if not isinstance(response_data, list) or not response_data:
            QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            self.InoutTable.setRowCount(0)  # 테이블 초기화
            return
            
        column_names = list(response_data[0].keys())  # 첫 번째 항목의 키를 컬럼 이름으로 사용
        self.InoutTable.setRowCount(len(response_data))
        self.InoutTable.setColumnCount(len(column_names))
        self.InoutTable.setHorizontalHeaderLabels(column_names)
        
        for row, item in enumerate(response_data):
            for col, key in enumerate(column_names):
                self.InoutTable.setItem(row, col, QTableWidgetItem(str(item.get(key, ""))))  # 값이 없으면 빈 문자열
        
        self.InoutTable.resizeColumnsToContents()
        self.InoutTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        print("\n📊 테이블 데이터 출력 완료")

    # 미니맵 제어 
    def getParkingstate(self) : 
        """주차공간상태요청"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectspacestate",

        }
        self.network_thread.send_data(user_data)
   
    def minimapdisplay(self, parking_status_list=[0, 0, 0, 0]): 

        space = [0,0,0,0]
        if spaces[1] == 1:
            displayLed1.setPixmap(self.parkingstate)
        else:  
            displayLed1.setPixmap(self.vacantstate)
        if spaces[2] == 2:
            displayLed2.setPixmap(self.parkingstate)
        else:  
            displayLed2.setPixmap(self.vacantstate)
        if spaces[3] == 1:
            displayLed3.setPixmap(self.parkingstate)
        else: 
            displayLed3.setPixmap(self.vacantstate)
        if spaces[4] == 1:
            displayLed4.setPixmap(self.parkingstate)
        else:  
            displayLed4.setPixmap(self.vacantstate)
  
    #유저 인포 창 열기 
    def EnterUserInfo(self): 
        self.userinfo_window = UserInfoWindow()
        self.userinfo_window.show()

    
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
    
    #cctv 제어 

    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindows = WindowClass()
    myWindows.show()
    sys.exit(app.exec_())