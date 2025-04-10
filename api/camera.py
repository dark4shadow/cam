from http.server import BaseHTTPRequestHandler
import requests
import cv2
import numpy as np
import time
import os
import json
from datetime import datetime

class AxisCameraHandler:
    """Handler for Axis IP camera feeds."""
    def __init__(self, camera_ip="24.134.3.9", username=None, password=None):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.stream_url = f"http://{camera_ip}/axis-cgi/mjpg/video.cgi"
        self.auth = None
        if username and password:
            self.auth = (username, password)
    
    def capture_frame(self):
        """Capture a single frame from the camera and return as JPEG bytes."""
        try:
            bytes_data = bytes()
            stream = requests.get(self.stream_url, auth=self.auth, stream=True, timeout=5)
            
            if 'multipart/x-mixed-replace' in stream.headers.get('Content-Type', ''):
                for chunk in stream.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    jpg_start = bytes_data.find(b'\xff\xd8')
                    jpg_end = bytes_data.find(b'\xff\xd9')
                    
                    if jpg_start != -1 and jpg_end != -1:
                        jpg_data = bytes_data[jpg_start:jpg_end+2]
                        return jpg_data
            return None
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None

# Serverless handler function
def handler(request):
    if request.method == 'GET':
        camera = AxisCameraHandler()
        frame_data = camera.capture_frame()
        
        if frame_data:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'image/jpeg',
                    'Cache-Control': 'no-store'
                },
                'body': frame_data,
                'isBase64Encoded': True
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to capture frame'})
            }
    else:
        return {'statusCode': 405, 'body': 'Method not allowed'}

# Vercel handler
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = handler(self)
        self.send_response(response.get('statusCode', 200))
        
        for key, value in response.get('headers', {}).items():
            self.send_header(key, value)
        self.end_headers()
        
        if response.get('isBase64Encoded', False):
            self.wfile.write(response['body'])
        else:
            self.wfile.write(response.get('body', '').encode())