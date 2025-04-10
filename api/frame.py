from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime
import base64
from api.camera import AxisCameraHandler

def handler(request):
    if request.method == 'GET':
        camera = AxisCameraHandler()
        frame_data = camera.capture_frame()
        
        if frame_data:
            # Generate a timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            
            # In serverless, we can't save files locally
            # Instead return the image data and filename
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'success': True,
                    'filename': filename,
                    'imageData': base64.b64encode(frame_data).decode('utf-8')
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'success': False, 'error': 'Failed to capture frame'})
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
        
        self.wfile.write(response.get('body', '').encode())