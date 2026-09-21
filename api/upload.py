import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Lấy độ dài của dữ liệu gửi lên
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            base64_image = data.get('image')
            if not base64_image:
                raise ValueError("Không tìm thấy dữ liệu ảnh")

            # Lấy API Key từ biến môi trường của Vercel (Bảo mật tuyệt đối)
            # Nếu chưa cài biến môi trường, nó sẽ dùng key tạm của bạn
            IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "81704eee7071f65bd94552592df15c3c")
            
            # Đóng gói và gửi request lên ImgBB
            url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
            payload = urllib.parse.urlencode({'image': base64_image}).encode('utf-8')
            
            req = urllib.request.Request(url, data=payload, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            # Trả kết quả về cho frontend
            if result.get('success'):
                img_url = result['data']['url']
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "url": img_url}).encode('utf-8'))
            else:
                raise Exception("Lỗi từ máy chủ ImgBB")

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
