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

    def connect_server(self, ip="192.168.0.22", port=5000):
        self.socket.connectToHost(QHostAddress(ip), port)
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

        self.groupBox.setVisible(False)  # 초기 숨김



    def modify(self):
        user_data = {
            "park_seq": PARK_SEQ,
            "type": "modify",
            "user_name": self.EditMname.text(),
            "car_number": self.EditMcarnum.text()
        }
        self.network_thread.send_data(user_data)
        self.btnConfirm.clicked.connect(self.close)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindows = WindowClass()
    myWindows.show()

    sys.exit(app.exec_())