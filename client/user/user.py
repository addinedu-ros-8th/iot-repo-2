import sys
import json
import cv2
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtNetwork import QTcpSocket, QHostAddress
from PyQt5 import uic

from_class = uic.loadUiType("user/user.ui")[0]

PARK_SEQ = 1

class NetworkThread(QThread):
    """ 서버와 통신하는 스레드 """
    data_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.socket = QTcpSocket()
        self.socket.readyRead.connect(self.read_response)

    def connect_server(self, ip="kimmossi.tplinkdns.com", port=5000):
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
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # 네트워크 스레드
        self.network_thread = NetworkThread()
        self.network_thread.data_received.connect(self.handle_response)
        self.network_thread.connect_server()

        self.groupBox.setVisible(False)  # 초기 숨김
        self.btnSearch.clicked.connect(self.searchuser)
        
    def handle_response(self, response):
        """ 서버 응답 처리 """
        print(f"Server Response: {response}")
        try:
            response_data = json.loads(response)
            QMessageBox.information(self, "응답", f"서버 메시지: {response_data.get('message', '응답 없음')}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "오류", "잘못된 서버 응답")

    def searchuser(self):
        user_data = {
            "park_seq": PARK_SEQ,
            "type": "userGUI_search",
            "user_name": self.editName.text(),
            "car_number": self.editCarnum.text()
        }
        self.network_thread.send_data(user_data)
        self.btnConfirm.clicked.connect(self.close)

    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindows = WindowClass()
    myWindows.show()

    sys.exit(app.exec_())