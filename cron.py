import os
import json
import time
from http.server import BaseHTTPRequestHandler
from google import genai
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# 1. Khởi tạo Firebase (Chỉ khởi tạo 1 lần để tránh lỗi khi Vercel chạy lại hàm)
if not firebase_admin._apps:
    # Lấy thông tin chứng chỉ Firebase từ biến môi trường của Vercel
    firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    
    # Parse chuỗi JSON thành dictionary
    firebase_cert = json.loads(firebase_cert_str)
    
    cred = credentials.Certificate(firebase_cert)
    
    # Đã sửa lại đường link Database URL chuẩn
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/' 
    })

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 2. Khởi tạo Gemini Client
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            if not gemini_api_key:
                raise ValueError("Chưa thiết lập biến môi trường GEMINI_API_KEY")
                
            client = genai.Client(api_key=gemini_api_key)

            # 3. Kịch bản Prompt mẫu
            ten_san_pham = "Mạch hạ áp LM2596"
            prompt = f"""
            Hãy đóng vai một thợ điện tử. Viết một bài đánh giá ngắn khoảng 300 chữ về sản phẩm: "{ten_san_pham}".
            Yêu cầu định dạng đầu ra chỉ chứa HTML:
            - Tiêu đề bọc trong <h2>
            - Các đoạn văn bọc trong <p>
            Không dùng markdown (```html).
            """

            # 4. Gọi Gemini viết bài với cơ chế chống lỗi 503
            bai_viet_html = ""
            for lan_thu in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    bai_viet_html = response.text
                    break
                except Exception as e:
                    if '503' in str(e) or 'UNAVAILABLE' in str(e):
                        time.sleep(5)
                        continue
                    else:
                        raise e
            
            if not bai_viet_html:
                raise Exception("Không thể lấy bài viết từ Gemini sau 3 lần thử.")

            # 5. Đẩy dữ liệu lên Firebase Realtime Database
            ref = db.reference('articles')
            new_article = {
                'title': ten_san_pham,
                'content': bai_viet_html,
                'timestamp': int(time.time() * 1000) # Lưu thời gian dạng milliseconds
            }
            # push() sẽ tự động tạo một ID ngẫu nhiên, độc nhất cho mỗi bài viết
            ref.push(new_article)

            # 6. Trả về kết quả thành công cho Vercel
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response_data = {
                "status": "success",
                "message": "Đã tạo và đẩy bài viết lên Firebase thành công!"
            }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as err:
            # Bắt và hiển thị lỗi nếu có vấn đề xảy ra
            self.send_response(500)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            error_data = {
                "status": "error",
                "message": str(err)
            }
            self.wfile.write(json.dumps(error_data).encode('utf-8'))
