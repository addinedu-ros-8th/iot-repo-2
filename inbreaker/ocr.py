import cv2
import easyocr

# EasyOCR 리더 생성 (한글만 인식)
reader = easyocr.Reader(['ko'])  

def main():
    # 웹캠에서 비디오 캡처
    cap = cv2.VideoCapture(0)  # 기본 웹캠 (0번)
    
    if not cap.isOpened():
        print("웹캠을 열 수 없습니다.")
        return
    
    while True:
        # 웹캠에서 프레임 캡처
        ret, frame = cap.read()
        
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break

        # 실시간 화면 표시
        cv2.imshow("Webcam", frame)

        key = cv2.waitKey(1) & 0xFF  # 키 입력 감지

        if key == ord(' '):  # 스페이스 바를 누르면 OCR 실행
            easyocr_result = reader.readtext(frame, detail=0)  # 한글만 인식
            print(f"EasyOCR 결과: {easyocr_result}")

        elif key == ord('q'):  # 'q'를 누르면 종료
            break
    
    # 웹캠 릴리즈
    cap.release()
    cv2.destroyAllWindows()

# 실행