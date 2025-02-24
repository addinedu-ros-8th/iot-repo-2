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
# 관리자 로그인 
class adminLoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/adminLogin.ui", self)
        
        # 네트워크 스레드
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()

        self.id = ""
        self.pw = ""

        # self.Loginbtn.clicked.connect(self.adminLogin)
        self.Loginbtn.clicked.connect(self.checkadmin)
    
    # def adminLogin(self):
    #     user_data = {
    #         "type": "adminLogin",
    #         "adminID" :self.IDEdit.text(),
    #         "adminPW" :self.PWEdit.text() 
    #     }
    #     self.network_thread.send_data(user_data)
    #     self.checkadmin()
    #     self.Loginbtn.clicked.connect(self.close)

    
    # def handle_response(self, response):
    #     print(f"Server Response: {response}")
    #     try:
    #         response_data = json.loads(response)
    #         QMessageBox.information(self, "응답", f"서버 메시지: {response_data.get('message', '응답 없음')}")
    #     except json.JSONDecodeError:
    #         QMessageBox.warning(self, "오류", "잘못된 서버 응답")

        
    def handle_response(self, response):
        print(":inbox_tray: 서버 응답:", response)
        try:
            response_data = json.loads(response)
            QMessageBox.information(self, "응답", f"서버 메시지: {response_data.get('message', '응답 없음')}")
            
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")

    def checkadmin(self):
        input_id = self.IDEdit.text() if isinstance(self.IDEdit, QLineEdit) else ""
        input_pw = self.PWEdit.text() if isinstance(self.PWEdit, QLineEdit) else ""
        
        if input_id == self.id and input_pw == self.pw:
            self.open_admin_window()
        else:
            QMessageBox.warning(self, "로그인 실패", "ID 또는 비밀번호가 다릅니다.")

    def open_admin_window(self):
        stream_url = "http://172.28.219.150:5001/feed1"
        self.admin_window = WindowClass(stream_url)
        self.admin_window.show()
        self.close()

# 유저인포 
class UserInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/UserInfo.ui", self)
        # 공유 소켓을 사용하는 응답 수신 스레드 실행
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()

        # 버튼
        self.SignUserInfobtn.clicked.connect(self.openSignUserInfo)
        self.updateUserInfobtn.clicked.connect(self.OpenupdateUserInfo)

        #조회 
        self.searchbtn.clicked.connect(self.selectUserInfo)
        
        #close 
        self.conformbtn.clicked.connect(self.close)

    def selectUserInfo(self):
        """ 유저 정보를 서버로 전송 """
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectUserInfo",
            "user_name": self.nameEdit.text(),
            "car_number": self.carnumEdit.text()
        }
        
        self.network_thread.send_data(user_data)

    def openSignUserInfo(self):
        self.SignUserInfoWindow = SignUserInfoWindow() 
        self.SignUserInfoWindow.show()       

    def OpenupdateUserInfo(self):
            self.updateUserInfoWindow = updateUserInfoWindow()
            self.updateUserInfoWindow.show()  
            
    def handle_response(self, response):
        print(f"📥 서버 응답: {response}")  # 원본 응답 확인
        
        try:
            response_data = json.loads(response)
            print(f"파싱된 데이터: {response_data}")  # JSON 변환 결과 확인
            
            if not response_data:  
                QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            else:
                QMessageBox.information(self, "응답", f"서버에서 {len(response_data)}개의 결과를 받았습니다.")
                self.visibleUserInfo(response_data)
        
        except json.JSONDecodeError as e:
            print(f"🚨 JSON 디코딩 오류: {e}")
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")


    # 서버에서 DB 정보 받아와 테이블 출력 
    def visibleUserInfo (self, response_data): 
        print(f"📊 테이블에 출력할 데이터: {response_data}")  # 디버깅용
        self.Usertable.setRowCount(len(response_data))  # 행 개수 설정
        self.Usertable.setColumnCount(len(response_data[0]))  # 컬럼 개수 설정 (딕셔너리 키 개수)
        self.Usertable.setHorizontalHeaderLabels(response_data[0].keys())  # 헤더 설정
        for row, item in enumerate(response_data):
            for col, key in enumerate(item.keys()):
                self.Usertable.setItem(row, col, QTableWidgetItem(str(item[key])))  # 데이터 삽입
        
        print("\n전송 완료")
        
        # for item in response_data:
        #     print(f"이름: {item['user_name']}, 차량번호: {item['car_number']}")
        #     print("\n")
        #     print("------------------------------------------------------")

        # print("-----------------------------------------------------------")

        
                






# :small_blue_diamond: 회원가입 
class SignUserInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/SignUserInfo.ui", self)
        self.Editcategory.clear()
        self.Editcategory.addItems(["일반차", "전기차"])  

        # 날짜 선택 위젯 설정
        self.EditStart.setCalendarPopup(True)  # 달력 팝업 활성화
        self.EditStart.setDate(QDate.currentDate())  # 기본값: 오늘 날짜
        self.EditEnd.setCalendarPopup(True)  # 달력 팝업 활성화
        self.EditEnd.setDate(QDate.currentDate())  # 기본값: 오늘 날짜

        #전화번호/차량 번호 가이드라인 제공

        # 버튼 클릭 시 정보 전송
        self.btnConfirm.clicked.connect(self.insertUserInfo)

        # 공유 소켓을 사용하는 응답 수신 스레드 실행
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()

    
    def insertUserInfo(self):
        user_data = {
            "park_id" : Park_ID ,
            "type": "insertUserInfo",
            "user_name": self.Editname.text(),
            "car_number": self.Editcarnum.text(),
            "car_uuid": self.EditRFID.text(),
            "user_phone": self.Editnum.text(),
            "car_category": self.Editcategory.currentText(),  
            "pass_start_date": self.EditStart.date().toString("yyyy-MM-dd"), 
            "pass_expiration_date": self.EditEnd.date().toString("yyyy-MM-dd")  
        }
        self.network_thread.send_data(user_data)
        self.btnConfirm.clicked.connect(self.close)

    
    def handle_response(self, response):
        print(f"Server Response: {response}")
        try:
            response_data = json.loads(response)
            QMessageBox.information(self, "응답", f"서버 메시지: {response_data.get('message', '응답 없음')}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")



# 회원 정보 수정 
class updateUserInfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main/updateUserInfo.ui", self)

        #btn 
        self.btnSearch.clicked.connect(self.selectUserInfo)
        self.btnupdate.clicked.connect(self.UpdateUserInfo)
        
        self.Editcategory.clear()
        self.Editcategory.addItems(["일반차", "전기차"])  

        # 날짜 선택 위젯 설정
        self.EditStart.setCalendarPopup(True)  # 달력 팝업 활성화
        self.EditStart.setDate(QDate.currentDate())  # 기본값: 오늘 날짜
        self.EditEnd.setCalendarPopup(True)  # 달력 팝업 활성화
        self.EditEnd.setDate(QDate.currentDate())  # 기본값: 오늘 날짜

        #전화번호/차량 번호 가이드라인 제공
        
        # 네트워크 스레드
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()
        self.groupBox.setVisible(False)  # 처음엔 숨김

    def selectUserInfo(self):
        """ 유저 정보를 서버로 전송 """
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectUserInfo",
            "user_name": self.EditOriginName.text(),
            "car_number": self.EditOrigincarnum.text()
        }
        
        self.network_thread.send_data(user_data)
        self.groupBox.setVisible(True)
        self.visibleUserInfo()

        
    def handle_response(self, response):
        print(f"Server Response: {response}")
        try:
            response_data = json.loads(response)
            if not response_data:  # 빈 리스트일 경우
                QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            else:
                QMessageBox.information(self, "응답", f"서버에서 {len(response_data)}개의 결과를 받았습니다.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")

    def visibleUserInfo(self):
        """유저 정보 받아와 보여주기"""
        print("정보 출력")

    def UpdateUserInfo(self):
        """User Data 보내주기"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "UpdateUserInfo",
            "user_name": self.Editname.text(),
            "car_number": self.Editcarnum.text(),
            "car_uuid": self.Edituuid.text(),
            "user_phone": self.Editnum.text(),
            "car_category": self.Editcategory.currentText(),  
            "pass_start_date": self.EditStart.date().toString("yyyy-MM-dd"), 
            "pass_expiration_date": self.EditEnd.date().toString("yyyy-MM-dd")  
        }

        self.network_thread.send_data(user_data)

        #만일 수정 성공시
        #     수정 성공이라 떠주고 
        #      종료 
        #만일 수정 실패시 
        #     수정실패라 뜨고 
        #     다시 연결 시도

        self.btnupdate.clicked.connect(self.close)







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
        self.UserInfobtn.clicked.connect(self.EnterUserInfo) # 유저 정보 
        self.btnSearch.clicked.connect(self.selectInOutHistory) # 조회버튼

        
      # 네트워크 스레드
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()

    # 유저 데이터 
        self.eventcombo.clear()
        self.eventcombo.addItems(["일반", "화재", "미정기"])  

        # 날짜 선택 위젯 설정
        self.dateStart.setCalendarPopup(True)  # 달력 팝업 활성화
        self.dateStart.setDate(QDate.currentDate())  # 기본값: 오늘 날짜
        self.dateEnd.setCalendarPopup(True)  # 달력 팝업 활성화
        self.dateEnd.setDate(QDate.currentDate())  # 기본값: 오늘 날짜


    #미니맵
        self.pixmap = QPixmap()
        self.pixmap.load('data/minimap.png')
        self.minimap.setPixmap(self.pixmap)
        self.minimap.resize(self.pixmap.width(), self.pixmap.height())

        self.minimapdisplay()

    # 미니맵 제어 
    def minimapdisplay(self): 
        self.parkingstate = QPixmap("data/parkingimg.png")
        self.vacantstate = QPixmap("data/vacant.png")
        """기본 상태 vacant 세팅"""
        # self.display_led1.setPixmap(self.vacantstate)
        # self.display_led2.setPixmap(self.vacantstate)
        # self.display_led3.setPixmap(self.vacantstate)
        # self.display_led4.setPixmap(self.vacantstate)


        """ 서버서 정보 실시간으로 받아오기 """
        # parking_status = [0, 1, 2]  
        # 1 = parking, 0 = vacant, 2 = fire
        
        # display_leds = [self.displayLed1, self.displayLed2, self.displayLed3, self.displayLed4]
        
        # for i in range(len(parking_status)):
        #     if parking_status[i] == 1:  # 주차 중
        #         display_leds[i].setPixmap(self.parkingstate)
        #     elif parking_status[i] == 0:  # 빈 자리
        #         display_leds[i].setPixmap(self.vacantstate)
        #     elif parking_status[i] == 2:  # 화재 발생
        #         display_leds[i].setPixmap(self.firestate)
        #         # 불났다고 서버에 전송하는 로직 추가
        #         self.send_fire_alert(i + 1)  
        #     else:
        #         print(f"Error: 주차장 {i+1} 상태 값 오류")
    
    # def send_fire_alert(self, parking_lot_number):
    #     """ 화재 발생 시 서버에 알림 전송 """
    #     alert_message = {"event": "fire", "parking_lot": parking_lot_number}
    #     self.network_thread.send_data(json.dumps(alert_message))
        

    # 입출차 기록 정보 보내기 
    def selectInOutHistory(self):
        """User Data 보내주기"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectInOutHistory",
            "user_name": self.editName.text(),
            "car_number": self.editCarnum.text(),
            "car_category": self.eventcombo.currentText(),  
            "pass_start_date": self.dateStart.date().toString("yyyy-MM-dd"), 
            "pass_expiration_date": self.dateEnd.date().toString("yyyy-MM-dd"),

        }

        self.network_thread.send_data(user_data)
        self.visibleInOutHistory()
    
    # 서버에서 DB 정보 받아와 테이블 출력 
    def visibleInOutHistory (self): 
        print("정보 출력")
        # data = {
        #     "type" : self.
        # }




    # 네트워크 관리 
    def handle_response(self, response):
        print(f"Server Response: {response}")
        try:
            response_data = json.loads(response)
            if not response_data:  # 빈 리스트일 경우
                QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            else:
                QMessageBox.information(self, "응답", f"서버에서 {len(response_data)}개의 결과를 받았습니다.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")


    #유저 인포 창 열기 
    def EnterUserInfo(self): 
        self.userinfo_window = UserInfoWindow()
        self.userinfo_window.show()

    def read_response(self):
        response = self.socket.readAll().data().decode('utf-8')
        print(f"Server Response: {response}")


    
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
    stream_url = "http://172.28.219.150:5001/feed1"
    app = QApplication(sys.argv)
    myWindows = adminLoginWindow()
    myWindows.show()
    sys.exit(app.exec_())