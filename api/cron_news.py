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

            # ==============================================================
            # TÍNH NĂNG MỚI: TỰ ĐỘNG MÓC LINK AFFILIATE TỪ KHO BÀI VIẾT CŨ
            # ==============================================================
            articles_ref = db.reference('articles').get()
            promo_html = ""
            
            if articles_ref:
                valid_products = []
                # Lọc ra các bài viết có gắn Tên sản phẩm và Link Shopee
                for key, val in articles_ref.items():
                    if isinstance(val, dict) and val.get('shopee_link') and val.get('product_name'):
                        valid_products.append({
                            'name': val['product_name'],
                            'link': val['shopee_link']
                        })
                
                # Bốc ngẫu nhiên 1 sản phẩm để quảng cáo
                if valid_products:
                    promo = random.choice(valid_products)
                    # Thiết kế giao diện HTML khung quảng cáo sẽ dính vào cuối bản tin
                    promo_html = f"""\n\n<div style="background: #fff3cd; padding: 12px; border-left: 4px solid #ffc107; border-radius: 6px; font-size: 0.95em; margin-top: 15px; display: inline-block; width: 100%; box-sizing: border-box;">🛒 <b>Gợi ý tiện ích:</b> <a href="{promo['link']}" target="_blank" style="color: #ee4d2d; text-decoration: none; font-weight: bold; float: right;">{promo['name']} &rarr;</a></div>"""
            # ==============================================================

            # 3. Lựa chọn Chủ đề
            topics = [
                "Công nghệ & Trí tuệ nhân tạo (AI)", 
                "Thị trường tài chính & Crypto", 
                "Khởi nghiệp & Xu hướng kinh doanh", 
                "Khoa học vũ trụ & Chế tạo kỹ thuật",
                "Đời sống số & Tiện ích gia đình"
            ]
            random_topic = random.choice(topics)

            # 4. Lệnh AI
            prompt = f"""
            Viết 1 bản tin NGẮN GỌN (khoảng 150 chữ) về sự kiện, tin tức hoặc xu hướng mới nhất thuộc lĩnh vực: {random_topic}.
            - Tiêu đề phải thật "giật tít".
            - Nội dung trình bày bằng các gạch đầu dòng (-), sử dụng \\n để xuống dòng.
            Trả về BẮT BUỘC bằng định dạng JSON chuẩn xác như sau:
            {{
                "category": "{random_topic}",
                "title": "[Tiêu đề giật tít]",
                "content": "[Nội dung tóm tắt]",
                "source": "AI Tổng hợp tự động"
            }}
            """

            # 5. Gọi AI
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.8,
                            response_mime_type="application/json",
                        )
                    )
                    break 
                except Exception as api_err:
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        raise Exception(f"Lỗi AI: {str(api_err)}")

            # 6. Gắn quảng cáo vào nội dung & Đẩy lên Firebase
            news_data = json.loads(response.text)
            
            # Nối khung quảng cáo HTML vào dưới cùng nội dung AI viết
            news_data['content'] = news_data.get('content', '') + promo_html
            news_data['timestamp'] = int(time.time() * 1000)
            
            db.reference('news').push(news_data)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"✅ Đã viết tin & Gắn link Affiliate thành công: {news_data['title']}".encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"❌ Lỗi: {str(err)}".encode('utf-8'))
