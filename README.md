![header](https://capsule-render.vercel.app/api?type=wave&color=auto&height=300&section=header&text=Parking%20Smoothly&fontSize=90)

# **TCP/IP를 활용한 IoT 스마트 주차장**

* 2025.02.07 ~ 2025.02.27
  
## 1. 기획 


### 1-1. 개발 동기


**가산 디지털 단지 내부의 주차장의 불편함** 


* 주차공간을 찾다가 없어서 나온 적이 많음 
* 어디에, 어떤 **주차 공간**이 **비어있는지** 한 눈에 보길 원함

  
**TCP 통신으로 실시간으로 주차장의 상황 정보를 전달하는 IoT 기반의 스마트 주차장을 만들자!**




### 1-2. 팀멤버와 역할

![image](https://github.com/user-attachments/assets/289575f6-7eaf-4909-822b-16e1e0589e3c)


### 1-3. 일정 


![image](https://github.com/user-attachments/assets/47b83d1c-7337-419b-b8a9-b510adaea2a9)


### 1-5.  개발 환경  

||내용|
|------|---|
|개발 환경|UBUNTU 22.04, VSCODE, ESP32 DEVKIT, 아두이노 스케치|
|개발 언어|python, c++|
|UI|PYQTS|
|DBMS|MYSQL|
|협업|GIT, GITBUB, SLACK, CONFLUENCE, JIRA|
|하드웨어|ESP32 DEVKIT 3개, ESP32 camera, 브래드보드, 보드 연결 핀, 3색 LED 3개, 서보모터 2개, QLED 2개, RFID 리더기, 카드 4개|

---

# 2. 설계 

### 2-1. 기능 리스트 


![image](https://github.com/user-attachments/assets/c95f4e43-3a6b-4d30-9313-08b47c8b93d1)


### 2-2. System Architecture


![image](https://github.com/user-attachments/assets/d5023243-714a-4b3d-90e4-13b9cba70a60)


### 2-3. HW Architecture

![image](https://github.com/user-attachments/assets/ed58fcaf-d178-461d-804c-e85d4d3b0f81)


### 2-4. SW Architecture

![image](https://github.com/user-attachments/assets/d2117523-fafa-4875-98dc-579af64833f1)


### 2-5. Data Structure


![image](https://github.com/user-attachments/assets/a5f0d7aa-62ca-4b2c-9531-04fef4e20a01)


### 2-6. UI Design


[figma](https://www.figma.com/design/oNSstSfl0fghC9PGpqPavT/Figma-basics?node-id=1669-162202&t=jxnTshg6gdd7RcFc-1)


![image](https://github.com/user-attachments/assets/bb0623a4-2caf-41e1-b7d6-be69be93d192)


### 2-7. I/F

![image](https://github.com/user-attachments/assets/c74deeb9-6e37-401c-9aa2-a438447169da)


---


# 3. 구현 결과 


## 1. 하드웨어 


## 1-1. 입구 


![IMG_1](./image/1.gif)

![IMG_2](./image/2.gif)


* 정기권이 없으면 안 열어준다.


### 만차
![3](./image/3.gif)

* 만차일 시 OLED에 표시하고 열어주지 않는다.


### 1-2. 출구 

![7](./image/7.gif)



### 1-3. 주차
![4](./image/4.gif)


주차된 수에 따라 OLED가 바뀐다. 


### 1-4. 화재 
![5](./image/5.gif)

자동으로 화재가 난 곳으로 카메라를 돌린다.


***


## 2. GUI

### 2-0. 로그인
![image](https://github.com/user-attachments/assets/53a1c861-e2ce-47a0-b688-776e17e3999b)



### 2-1. 메인화면
![image](https://github.com/user-attachments/assets/c8f395d0-fe1d-4d14-a025-27e99a638458)


어느정도 차가 찼는지에 따라 미니맵이 바뀐다.


![image](https://github.com/user-attachments/assets/471452fa-03bf-4e94-be7c-3c4667ca732d)


주차된 공간에 마우스를 가져다대면 주차된 차량 정보를 확인 가능하다.



### 2-2. 회원정보 
![image](https://github.com/user-attachments/assets/86a0e7a5-16d2-4676-b3f5-188718f5b335)



### 2-3. 회원가입 
![image](https://github.com/user-attachments/assets/45708cd9-54db-469e-9f36-a94c8caaa962)



### 2-4.회원수정 
![image](https://github.com/user-attachments/assets/892d46e5-c405-441a-a3e1-41690fb19d70)



### 2-6. 화재 알람
![image](https://github.com/user-attachments/assets/f18b5eea-132b-4eb6-ad51-a6d975a35bad)


![image](https://github.com/user-attachments/assets/ec0b8652-af47-40d1-9a57-78ec0c2d1fcf)



![fire_event_20250227_183053](https://github.com/user-attachments/assets/a9fb0a6d-a20d-4373-89e0-23ddbc60f3eb)

영상이 자동으로 저장된다.


### 2-7. 이벤트 기록
![image](https://github.com/user-attachments/assets/f6c2025b-c2bb-43d3-9a9e-3cbffeb7562e)


***


## 3. User GUI 


## 3-1. main User GUI  
![image](https://github.com/user-attachments/assets/222a1f6a-2226-4424-8fe5-6399cd5a83e2)


### 3-1-1. 입출차 기록이 없는 경우
![image](https://github.com/user-attachments/assets/d1513e8a-5101-40d9-adb4-d1d7f1193d7f)



### 3-1-2. 출차 기록이 없는 경우
![image](https://github.com/user-attachments/assets/5e7330a3-ceeb-43fa-924b-495148e746d4)



### 3-1-3. 입출차 기록이 없는 경우


마지막 기록으로 보여준다


![image](https://github.com/user-attachments/assets/92d7192f-42fa-4c8e-8b40-5656aeb44514)
