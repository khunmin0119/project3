"""
FastAPI + WebRTC 기반 실시간 영상 처리 서버
작업자는 스마트폰 브라우전에서 접속만 하면 됨
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import cv2
import numpy as np
import base64
import json

app = FastAPI()

CLIENT_HTML = """
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body>
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas" style="display:none"></canvas>
    <img id="result" style="width:100%">
    
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const result = document.getElementById('result');
        
        // 카메라 시작
        navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: 1920, height: 1080 }
        }).then(stream => {
            video.srcObject = stream;
        });
        
        // WebSocket으로 프레임 전송
        const ws = new WebSocket(`ws://${location.host}/ws`);
        
        setInterval(() => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            
            canvas.toBlob(blob => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(blob);
                }
            }, 'image/jpeg', 0.7);
        }, 200);  // 5 FPS로 전송 (현장 검사에 충분)
        
        ws.onmessage = (event) => {
            // AI 결과 오버레이된 이미지 수신
            result.src = 'data:image/jpeg;base64,' + event.data;
        };
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(CLIENT_HTML)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        # 스마트폰에서 프레임 수신
        data = await websocket.receive_bytes()
        frame = cv2.imdecode(
            np.frombuffer(data, np.uint8),
            cv2.IMREAD_COLOR
        )
        
        # AI 추론
        results = model(frame)
        annotated = results[0].plot()
        
        # 결과 이미지를 스마트폰으로 전송
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64 = base64.b64encode(buffer).decode()
        await websocket.send_text(b64)