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
        column_names = ["주차장 ID", "이름", "차량 번호", "차량 UUID", "전화번호", "차량 종류", "정기권 시작일", "정기권 만기일"]

        print(f"📊 테이블에 출력할 데이터: {response_data}")  # 디버깅용
        self.Usertable.setRowCount(len(response_data))  # 행 개수 설정
        self.Usertable.setColumnCount(len(column_names))  # 컬럼 개수 설정 (딕셔너리 키 개수)
        self.Usertable.setHorizontalHeaderLabels(column_names)  # 헤더 설정
        for row, item in enumerate(response_data):
            for col, key in enumerate(item.keys()):
                self.Usertable.setItem(row, col, QTableWidgetItem(str(item[key])))  # 데이터 삽입

        self.Usertable.resizeColumnsToContents()        
        self.Usertable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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

        self.currentRequestType = None

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

    def UpdateUserInfo(self):
        """User Data 보내주기"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "updateUserInfo",
            "user_name": self.Editname.text(),
            "car_number": self.Editcarnum.text(),
            "car_uuid": self.Edituuid.text(),
            "user_phone": self.Editnum.text(),
            "car_category": self.Editcategory.currentText(),  
            "pass_start_date": self.EditStart.date().toString("yyyy-MM-dd"), 
            "pass_expiration_date": self.EditEnd.date().toString("yyyy-MM-dd")  
        }

        self.network_thread.send_data(user_data)


    def handle_response(self, response):
        print(f"Server Response: {response}")
        print(f"Current Request Type: {self.currentRequestType}")
        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답 (JSON 파싱 실패)")
            return

        # currentRequestType에 따라 분기 처리
        if self.currentRequestType == "selectUserInfo":
            self.handle_select_response(response_data)

        elif self.currentRequestType == "updateUserInfo":
            self.handle_update_response(response_data)

        else:
            print(response_data)
            self.handle_select_response(response_data)

    def handle_select_response(self, response_data):
        """조회 응답 처리"""
        if not response_data:
            QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            return

        if isinstance(response_data, list) and response_data:
            response_data = response_data[0]
        elif not isinstance(response_data, dict):
            # 예상치 못한 형식이면 그대로 반환
            QMessageBox.warning(self, "오류", "조회 결과가 딕셔너리 형식이 아닙니다.")
            return

        # groupBox 표시
        self.groupBox.setVisible(True)

        # 조회된 값을 UI에 채워넣기
        self.Edituuid.setText(response_data.get("user_id", ""))
        self.Editname.setText(response_data.get("user_name", ""))
        self.Editcarnum.setText(response_data.get("car_number", ""))
        self.Edituuid.setText(response_data.get("car_uuid", ""))
        self.Editnum.setText(response_data.get("user_phone", ""))


        # 콤보박스 값 설정 (없으면 기본값)
        category = response_data.get("car_category", "일반차")
        if category in ["일반차", "전기차"]:
            self.Editcategory.setCurrentText(category)
        else:
            self.Editcategory.setCurrentIndex(0)

        # 날짜 문자열 -> QDate로 변환
        start_str = response_data.get("pass_start_date", "")
        end_str = response_data.get("pass_expiration_date", "")

        if start_str:
            try:
                year, month, day = map(int, start_str.split("-"))
                self.EditStart.setDate(QDate(year, month, day))
            except ValueError:
                pass  # 변환 실패하면 무시

        if end_str:
            try:
                year, month, day = map(int, end_str.split("-"))
                self.EditEnd.setDate(QDate(year, month, day))
            except ValueError:
                pass

    def handle_update_response(self, response_data):
        """수정 응답 처리"""
        if isinstance(response_data, dict) and response_data.get("result") == "success":
            QMessageBox.information(self, "성공", "회원 정보 수정이 완료되었습니다.")
            self.close()  # 창 닫기
        else:
            QMessageBox.warning(self, "실패", "회원 정보 수정에 실패했습니다.")








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
        self.Start()

    # 유저 데이터 
        self.eventcombo.clear()
        self.eventcombo.addItems(["일반", "화재", "미정기"])  

        # 날짜 선택 위젯 설정
        self.dateStart.setCalendarPopup(True)  # 달력 팝업 활성화
        self.dateStart.setDate(QDate.currentDate())  # 기본값: 오늘 날짜
        self.dateEnd.setCalendarPopup(True)  # 달력 팝업 활성화
        self.dateEnd.setDate(QDate.currentDate())  # 기본값: 오늘 날짜


    #미니맵
   #미니맵
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

        self.getParkingstate()

    def getParkingstate(self) : 
        """주차공간상태요청"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectspacestate",
        }

        self.network_thread.send_data(user_data)

    # 미니맵 제어 
    def minimapdisplay(self, response_data): 
        self.parkingstate = QPixmap("data/parkingimg.png")
        self.vacantstate = QPixmap("data/vacant.png")
        """ 서버서 정보 실시간으로 받아오기 """
        led_mapping = {
            "space1": self.displayLed1,
            "space2": self.displayLed2,
            "space3": self.displayLed3,
            "space4": self.displayLed4
        }
        if not isinstance(response_data, list):
            print("🚨 응답이 리스트 형식이 아님:", response_data)
            return
        for row in response_data:
            space_name = row.get("space_name")  # 예: 'space1'
            state = row.get("state")           # 예: 1 또는 0

        # 4) 해당 space_name에 대응되는 LED 라벨 가져오기
        led_label = led_mapping.get(space_name)
        if led_label is None:
            print(f"🚨 매핑되지 않은 space_name: {space_name}")

        # 5) state가 1이면 parking 이미지를, 0이면 vacant 이미지를 세팅
        if state == 1:
            led_label.setPixmap(self.parkingstate)
        else:
            led_label.setPixmap(self.vacantstate)


    


    # 입출차 기록 정보 보내기 
    def selectInOutHistory(self):
        """User Data 보내주기"""
        user_data = {
            "park_id" : Park_ID ,
            "type": "selectInOutHistory",
            "user_name": self.editName.text(),
            "car_number": self.editCarnum.text(),
            "event_category": self.eventcombo.currentText(),  
            "pass_start_date": self.dateStart.date().toString("yyyy-MM-dd-HH:mm:ss"), 
            "pass_expiration_date": self.dateEnd.date().toString("yyyy-MM-dd-HH:mm:ss"),

        }

        self.network_thread.send_data(user_data)
    
    # 서버에서 DB 정보 받아와 테이블 출력 
    def visibleInOutHistory (self, response_data): 
        for item in response_data:
            print(f"이름: {item['user_name']}, 차량번호: {item['car_number']}")
            print("\n")
            print("------------------------------------------------------")

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


    def Start(self):
        """시작하면 주차장 상황 정보를 받기위해 """
        user_data = {
            "admin1": 'admin1',
            "park_id" : Park_ID , 
            "type" : "ping"
        }

        self.network_thread.send_data(user_data)


    # 네트워크 관리 
    def handle_response(self, response):
        print(f"Server Response: {response}")
        try:
            response_data = json.loads(response)
            if not response_data:  # 빈 리스트일 경우
                QMessageBox.information(self, "응답", "서버에서 일치하는 데이터를 찾지 못했습니다.")
            elif isinstance(response_data, str):
                # 단순 텍스트인 경우, lineEdit에 출력
                self.lineEdit.setText(response_data)
                print("서버에서 받은 단순 텍스트 응답:", response_data)
            elif all(key in response_data for key in ["space1", "space2", "space3", "space4"]):
                self.minimapdisplay(response_data)
                print("서버에서 받은 미니맵 데이터 :", response_data)
            else:
                QMessageBox.information(self, "응답", f"서버에서 {len(response_data)}개의 결과를 받았습니다.")
                self.visibleInOutHistory(response_data)

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