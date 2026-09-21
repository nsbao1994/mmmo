import os
import json
import random
import time
from http.server import BaseHTTPRequestHandler
import firebase_admin
from firebase_admin import credentials, db
from google import genai
from google.genai import types

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 1. Khởi tạo Firebase (Sử dụng biến môi trường đã có sẵn trên Vercel)
            if not firebase_admin._apps:
                firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                if not firebase_cert_str:
                    raise Exception("Chưa cài đặt FIREBASE_SERVICE_ACCOUNT")
                firebase_cert = json.loads(firebase_cert_str)
                cred = credentials.Certificate(firebase_cert)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })

            # 2. Khởi tạo Gemini AI (Sử dụng GEMINI_API_KEY)
            gemini_key = os.environ.get('GEMINI_API_KEY')
            if not gemini_key:
                raise Exception("Chưa cài đặt GEMINI_API_KEY")
            client = genai.Client(api_key=gemini_key)

            # 3. Lựa chọn chủ đề NGẪU NHIÊN để làm phong phú trang web
            topics = [
                "Công nghệ & Trí tuệ nhân tạo", 
                "Kinh tế & Thị trường tài chính", 
                "Khởi nghiệp & Xu hướng kinh doanh", 
                "Khoa học vũ trụ & Khám phá",
                "Môi trường & Năng lượng xanh"
            ]
            random_topic = random.choice(topics)

            # 4. Ra lệnh cho Gemini viết báo (Ép buộc trả về JSON)
            prompt = f"""
            Đóng vai một nhà báo chuyên nghiệp. Hãy viết 1 bản tin điểm tin nhanh (khoảng 150 - 200 chữ) về một sự kiện/thông tin thực tế, nổi bật và thú vị nhất liên quan đến lĩnh vực: {random_topic}.
            Bạn phải trả về kết quả dưới dạng JSON với cấu trúc chính xác như sau:
            {{
                "category": "{random_topic}",
                "title": "Tiêu đề bản tin giật tít, hấp dẫn",
                "content": "Nội dung tóm tắt chi tiết. Trình bày bằng các gạch đầu dòng (-), sử dụng ký tự \\n để xuống dòng cho dễ nhìn.",
                "source": "AI Tổng hợp tự động"
            }}
            """

            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json", # Ép Gemini trả về JSON chuẩn
                )
            )

            # 5. Phân tích kết quả và đẩy lên Firebase nhánh 'news'
            news_data = json.loads(response.text)
            news_data['timestamp'] = int(time.time() * 1000)
            
            db.reference('news').push(news_data)

            # 6. Báo cáo thành công cho cron-job.org
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"✅ Đã tự động viết và đăng tin thành công: {news_data['title']}".encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"❌ Lỗi: {str(err)}".encode('utf-8'))
