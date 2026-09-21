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
            # 1. Khởi tạo Firebase
            if not firebase_admin._apps:
                firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                firebase_cert = json.loads(firebase_cert_str)
                cred = credentials.Certificate(firebase_cert)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })

            # 2. Khởi tạo Gemini AI
            gemini_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=gemini_key)

            # 3. NGÂN HÀNG CHỦ ĐỀ SIÊU ĐA DẠNG (AI sẽ bốc ngẫu nhiên mỗi lần chạy)
            topics = [
                "Công nghệ lõi & Trí tuệ nhân tạo (AI)", 
                "Thị trường tài chính & Tiền điện tử (Crypto)", 
                "Xu hướng kinh doanh & Khởi nghiệp", 
                "Khoa học vũ trụ & Công nghệ tương lai",
                "Xe cộ & Phương tiện giao thông điện",
                "Môi trường & Năng lượng xanh",
                "Đời sống số & An toàn không gian mạng",
                "Đột phá Vật lý & Chế tạo kỹ thuật"
            ]
            random_topic = random.choice(topics)

            # 4. PROMPT TRAO TOÀN QUYỀN CHO AI TỰ BIÊN TẬP
            prompt = f"""
            Bạn là một Tổng biên tập tin tức mẫn cán. Không có ai cung cấp thông tin cho bạn cả, bạn phải TỰ SUY NGHĨ, tự tìm kiếm trong kho dữ liệu khổng lồ của mình để viết ra 1 bản tin NGẮN GỌN, HẤP DẪN về chủ đề: {random_topic}.
            
            Quy tắc:
            - Chọn một sự kiện nổi bật, thực tế hoặc một xu hướng công nghệ mới nhất.
            - Tiêu đề phải thật "giật tít", khơi gợi trí tò mò.
            - Nội dung khoảng 150 chữ, trình bày bằng các gạch đầu dòng (-) rõ ràng, sử dụng \\n để xuống dòng.
            
            Trả về BẮT BUỘC bằng định dạng JSON chuẩn xác như sau:
            {{
                "category": "{random_topic}",
                "title": "[Tiêu đề giật tít]",
                "content": "[Nội dung tóm tắt]",
                "source": "AI Tổng hợp tự động"
            }}
            """

            # 5. Gọi AI với cơ chế Tự động thử lại (Chống lỗi 503 Quá tải)
            max_retries = 3
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.8, # Tăng nhẹ độ sáng tạo
                            response_mime_type="application/json",
                        )
                    )
                    break 
                except Exception as api_err:
                    if attempt < max_retries - 1:
                        time.sleep(5) # Đợi 5 giây nếu Google bị nghẽn mạng
                    else:
                        raise Exception(f"AI đang nghỉ ngơi, thử lại sau: {str(api_err)}")

            # 6. Đẩy thẳng lên Firebase, không qua Admin duyệt
            news_data = json.loads(response.text)
            news_data['timestamp'] = int(time.time() * 1000)
            
            db.reference('news').push(news_data)

            # Báo cáo kết quả
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"✅ AI đã tự nghĩ và viết thành công bài: {news_data['title']}".encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"❌ Lỗi: {str(err)}".encode('utf-8'))
