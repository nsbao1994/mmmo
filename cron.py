from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # TODO: Ở các bước tiếp theo, code tự động gọi Shopee API, 
        # viết bài bằng Gemini và đẩy lên Firebase sẽ nằm ở đây!
        
        # Hiện tại, trả về phản hồi để báo Vercel biết code đã chạy thành công
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        
        response = {
            "status": "success",
            "message": "Cronjob đã chạy. Hệ thống MMO sẵn sàng!"
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))