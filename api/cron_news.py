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
            if not firebase_admin._apps:
                firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                firebase_cert = json.loads(firebase_cert_str)
                cred = credentials.Certificate(firebase_cert)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })

            gemini_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=gemini_key)

            # --- MÓC LINK AFFILIATE ---
            articles_ref = db.reference('articles').get()
            promo_html = ""
            if articles_ref:
                valid_products = []
                for key, val in articles_ref.items():
                    if isinstance(val, dict) and val.get('shopee_link') and val.get('product_name'):
                        valid_products.append({'name': val['product_name'], 'link': val['shopee_link']})
                
                if valid_products:
                    promo = random.choice(valid_products)
                    # FIX MOBILE: Chuyển sang dùng Flexbox thay vì float để tự động co giãn trên điện thoại
                    promo_html = f"""\n\n<div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; border-radius: 6px; font-size: 0.95em; margin-top: 15px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; width: 100%; box-sizing: border-box;"><span style="color: #856404; font-weight: bold;">🛒 Gợi ý tiện ích:</span> <a href="{promo['link']}" target="_blank" style="background: #ee4d2d; color: white; padding: 6px 14px; border-radius: 4px; text-decoration: none; font-weight: bold; white-space: nowrap; text-align: center;">{promo['name']} &rarr;</a></div>"""

            # --- GỌI AI VIẾT BÀI CÓ HASHTAG ---
            topics = ["Công nghệ & Trí tuệ nhân tạo", "Thị trường tài chính & Crypto", "Khởi nghiệp & Xu hướng kinh doanh", "Khoa học vũ trụ", "Đời sống số"]
            random_topic = random.choice(topics)

            prompt = f"""
            Viết 1 bản tin NGẮN GỌN (khoảng 150 chữ) về sự kiện hoặc xu hướng mới nhất thuộc lĩnh vực: {random_topic}.
            - Tiêu đề phải "giật tít".
            - Trình bày bằng các gạch đầu dòng (-), sử dụng \\n để xuống dòng.
            - Tạo ra 3 đến 5 hashtags (VD: #CongNghe, #AI) phù hợp với bài viết.
            
            Trả về định dạng JSON chuẩn xác như sau:
            {{
                "category": "{random_topic}",
                "title": "[Tiêu đề]",
                "content": "[Nội dung]",
                "hashtags": ["#tag1", "#tag2", "#tag3"],
                "source": "AI Tổng hợp tự động"
            }}
            """

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.8, response_mime_type="application/json")
                    )
                    break 
                except Exception as api_err:
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        raise Exception(f"Lỗi AI: {str(api_err)}")

            news_data = json.loads(response.text)
            news_data['content'] = news_data.get('content', '') + promo_html
            news_data['timestamp'] = int(time.time() * 1000)
            
            db.reference('news').push(news_data)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"✅ Đã viết tin + Hashtag + Link Mobile thành công: {news_data['title']}".encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"❌ Lỗi: {str(err)}".encode('utf-8'))
