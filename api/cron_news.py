import os
import json
import random
import time
import urllib.parse
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

            client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

            # 2. LẤY SẢN PHẨM TỪ BLOG VÀ TẠO KHUNG SHOPEE TO ĐẸP
            articles_ref = db.reference('articles').get()
            promo_html = ""
            
            if articles_ref:
                valid_products = []
                for key, val in articles_ref.items():
                    if isinstance(val, dict) and val.get('shopee_link') and val.get('product_name'):
                        # Tìm ảnh (Nếu có ảnh custom thì lấy, không thì dùng ảnh AI tạo từ prompt/title)
                        img_prompt = val.get('image_prompt') or val.get('title') or 'technology gadget'
                        final_img = val.get('custom_img') or f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_prompt)}?width=300&height=300&nologo=true"
                        final_price = val.get('custom_price') or "Đang có mã giảm giá"
                        
                        valid_products.append({
                            'name': val['product_name'],
                            'link': val['shopee_link'],
                            'image': final_img,
                            'price': final_price
                        })
                
                if valid_products:
                    promo = random.choice(valid_products)
                    # Tạo cấu trúc HTML giống hệt trang Blog
                    promo_html = f"""
                    <a href="{promo['link']}" target="_blank" style="text-decoration: none; color: inherit; display: block; margin-top: 20px;">
                        <div class="shopee-box" style="display: flex; align-items: center; background: #fff; border: 2px dashed #ee4d2d; border-radius: 8px; padding: 15px; gap: 20px; box-shadow: 0 4px 10px rgba(238,77,45,0.08);">
                            <div class="shopee-box-img" style="width: 120px; height: 120px; flex-shrink: 0; border-radius: 6px; overflow: hidden; border: 1px solid #eee;">
                                <img src="{promo['image']}" alt="Sản phẩm" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='https://picsum.photos/300/300'">
                            </div>
                            <div class="shopee-box-info" style="flex-grow: 1;">
                                <div class="shopee-box-title" style="font-weight: bold; font-size: 1.1em; color: #333; margin-bottom: 8px; line-height: 1.4;">🛒 {promo['name']}</div>
                                <div class="shopee-box-price" style="color: #555; font-size: 0.95em; margin-bottom: 5px;">Giá ưu đãi: <span style="color: #ee4d2d; font-weight: bold; font-size: 1.2em;">{promo['price']}</span></div>
                                <div class="shopee-box-desc" style="color: #26aa99; font-size: 0.85em; font-weight: bold; margin-bottom: 15px;">🔥 Đang có Mã Giảm Giá & Freeship Extra</div>
                                <span class="shopee-box-btn" style="display: inline-block; background: #ee4d2d; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold;">Đến Nơi Bán &rarr;</span>
                            </div>
                        </div>
                    </a>
                    """

            # 3. Lệnh AI viết báo
            topics = ["Công nghệ", "Tài chính", "Khởi nghiệp", "Vũ trụ & Khoa học", "Mẹo vặt gia đình"]
            random_topic = random.choice(topics)
            prompt = f"""
            Viết 1 bản tin NGẮN GỌN (khoảng 150 chữ) về sự kiện/xu hướng mới nhất lĩnh vực: {random_topic}.
            Tiêu đề giật tít. Nội dung gạch đầu dòng (-), dùng \\n xuống dòng.
            Trả về BẮT BUỘC bằng JSON: {{"category": "{random_topic}", "title": "Tiêu đề", "content": "Nội dung", "source": "AI Tổng hợp", "hashtags": ["#Tag1", "#Tag2"]}}
            """

            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash', contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.8, response_mime_type="application/json")
                    )
                    break 
                except Exception as api_err:
                    if attempt < 2: time.sleep(5)
                    else: raise Exception(str(api_err))

            # 4. Ép khung Quảng cáo vào đuôi bài viết & Lưu Firebase
            news_data = json.loads(response.text)
            news_data['content'] = news_data.get('content', '') + promo_html
            news_data['timestamp'] = int(time.time() * 1000)
            
            db.reference('news').push(news_data)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"✅ Đã viết tin & Gắn Shopee thành công: {news_data['title']}".encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"❌ Lỗi: {str(err)}".encode('utf-8'))
