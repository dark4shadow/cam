import requests
import cv2
import numpy as np
import time
import os
from datetime import datetime
from flask import Flask, Response, render_template
from pyngrok import ngrok

class AxisCameraHandler:
    """
    Handler for Axis IP camera feeds.
    """
    def __init__(self, camera_ip="24.134.3.9", username=None, password=None):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.stream_url = f"http://{camera_ip}/axis-cgi/mjpg/video.cgi"
        self.auth = None
        if username and password:
            self.auth = (username, password)
    
    def test_connection(self):
        """Test if the camera is accessible."""
        try:
            response = requests.get(self.stream_url, auth=self.auth, stream=True, timeout=5)
            response.raise_for_status()
            return True
        except (requests.RequestException, ConnectionError) as e:
            print(f"Camera connection error: {e}")
            return False

    def capture_frame(self):
        """Capture a single frame from the camera."""
        try:
            bytes_data = bytes()
            stream = requests.get(self.stream_url, auth=self.auth, stream=True, timeout=10)
            
            if 'multipart/x-mixed-replace' in stream.headers.get('Content-Type', ''):
                for chunk in stream.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    jpg_start = bytes_data.find(b'\xff\xd8')
                    jpg_end = bytes_data.find(b'\xff\xd9')
                    
                    if jpg_start != -1 and jpg_end != -1:
                        jpg_data = bytes_data[jpg_start:jpg_end+2]
                        nparr = np.frombuffer(jpg_data, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        return img
            return None
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None
    
    def save_frame(self, folder="captures"):
        """Capture and save a frame to disk."""
        img = self.capture_frame()
        if img is not None:
            os.makedirs(folder, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{folder}/capture_{timestamp}.jpg"
            cv2.imwrite(filename, img)
            print(f"Frame saved to {filename}")
            return filename
        return None
    
    def generate_frames(self):
        """Generate frames for streaming."""
        while True:
            frame = self.capture_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                time.sleep(0.1)

# Flask app for streaming
app = Flask(__name__)
camera_handler = AxisCameraHandler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(camera_handler.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Add this route to your Flask app
@app.route('/capture')
def capture():
    filename = camera_handler.save_frame()
    success = filename is not None
    return {'success': success, 'filename': filename}

if __name__ == "__main__":
    # Create a tunnel to your local server
    try:
        # Try ngrok first
        public_url = ngrok.connect(5000)
        print(f' * Public URL: {public_url}')
    except Exception as e:
        print(f"Ngrok error: {e}")
        print("Running without tunneling. Access locally at http://localhost:5000")
        # You could implement alternative tunneling here
    
    app.run(host='0.0.0.0', port=5000, debug=True)