from flask import Flask, Response
import cv2
import threading
import time

app = Flask(__name__)

# Initialize video capture with desired resolution
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1440)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 830)

frame_buffer = None
lock = threading.Lock()

def update_frames():
    global frame_buffer
    while True:
        success, frame = cap.read()
        if not success:
            break
        with lock:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_buffer = buffer.tobytes()
        time.sleep(1 / 30.0)

@app.route('/feed0')
def video_feed1():
    def generate():
        while True:
            with lock:
                if frame_buffer is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_buffer + b'\r\n')
            time.sleep(1 / 30.0)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/feed1')
def video_feed2():
    def generate():
        while True:
            with lock:
                if frame_buffer is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_buffer + b'\r\n')
            time.sleep(1 / 30.0)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    app.run(host='0.0.0.0', port=5001)

if __name__ == '__main__':
    threading.Thread(target=update_frames, daemon=True).start()
    threading.Thread(target=run_flask).start()

