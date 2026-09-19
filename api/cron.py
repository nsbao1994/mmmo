import os
import json
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler
from google import genai
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Khởi tạo Firebase
if not firebase_admin._apps:
    firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    firebase_cert = json.loads(firebase_cert_str)
    cred = credentials.Certificate(firebase_cert)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/' 
    })

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            queue_ref = db.reference('queue')
            queue_data = queue_ref.get()
            
            if not queue_data:
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "empty", "message": "Hàng đợi trống!"}, ensure_ascii=False).encode('utf-8'))
                return

            first_key = list(queue_data.keys())[0]
            item = queue_data[first_key]
            
            # --- 1. LẤY DỮ LIỆU TỪ HÀNG ĐỢI (Đã sửa lỗi thiếu biến) ---
            keyword = item.get('keyword', 'Mẹo công nghệ')
            shopee_link_raw = item.get('shopee_link', '')
            custom_img = item.get('custom_img', '')     
            custom_price = item.get('custom_price', '') 

            # --- 2. XỬ LÝ LINK SHOPEE / ACCESSTRADE THÔNG MINH ---
            # Nếu Admin nhập link tay thì dùng link tay. Nếu Admin bỏ trống thì tự tạo link tìm kiếm có mã AT.
            if shopee_link_raw == "https://shopee.vn" or shopee_link_raw == "":
                encoded_keyword = urllib.parse.quote(keyword)
                shopee_search_url = f"https://shopee.vn/search?keyword={encoded_keyword}"
                safe_shopee_url = urllib.parse.quote(shopee_search_url, safe='')
                
                # Bọc mã Accesstrade của bạn vào đây (Sửa MÃ_CỦA_BẠN bằng số thật nếu có)
                at_base = "https://go.isclix.com/deep_link/MÃ_CỦA_BẠN?url=" 
                shopee_link = f"{at_base}{safe_shopee_url}"
            else:
                shopee_link = shopee_link_raw

            # --- 3. GỌI GEMINI AI VIẾT BÀI ---
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=gemini_api_key)

           prompt = f"""
            Đóng vai một chuyên gia kỹ thuật và mẹo vặt đời sống (Tech & DIY Hacker) nhiều kinh nghiệm. Hãy viết một bài chia sẻ mẹo vặt, hướng dẫn xử lý nhanh hoặc cảnh báo hữu ích về chủ đề: "{keyword}".
            
            Văn phong: Gây tò mò, đi thẳng vào vấn đề, đánh trúng tâm lý người đọc (tiết kiệm tiền, an toàn, nhanh chóng), dễ hiểu và mang tính ứng dụng thực tế cao.
            Cấu trúc bài viết (bắt buộc): 
            1. Nêu vấn đề/Nỗi đau thường gặp.
            2. Cách giải quyết bằng mẹo vặt (Step-by-step rõ ràng).
            3. Lời khuyên chọn mua thiết bị/dụng cụ để xử lý triệt để (Đây là bước đệm hoàn hảo để hiển thị sản phẩm mua hàng).
            
            Yêu cầu đầu ra bắt buộc phải là một đối tượng JSON thuần túy (không chứa markdown như ```json hoặc ```), có đúng các trường sau:
            - "title": Tiêu đề bài viết cực kỳ thu hút, giật tít một chút, khơi gợi sự tò mò (string). Ví dụ: "Đừng vội vứt đồ đi nếu biết mẹo này...", "3 Sai lầm chết người khi dùng..."
            - "category": Chọn 1 trong các danh mục sau cho phù hợp nhất: "Mẹo DIY", "Linh kiện điện tử", "Đồ điện tử", "Đồ gia dụng", "Năng lượng mặt trời" (string)
            - "hashtags": Danh sách 4-5 thẻ hashtag liên quan (mảng string, ví dụ: ["#meohay", "#diyvietnam", "#suachua"])
            - "image_prompt": Một đoạn mô tả ngắn bằng tiếng Anh để tạo hình ảnh AI minh họa chân thực cho mẹo vặt này (string)
            - "content": Nội dung bài viết chi tiết định dạng HTML, ưu tiên dùng các thẻ <h2>, <p>, <ul>, <li>, <strong> để trình bày thật bắt mắt, dễ đọc. (Tuyệt đối không tự chèn thẻ <a> hay link vào trong nội dung). (string)
            """

            response_text = ""
            for _ in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    response_text = response.text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                    response_text = response_text.strip()
                    break
                except Exception as e:
                    if '503' in str(e) or 'UNAVAILABLE' in str(e):
                        time.sleep(5)
                        continue
                    else:
                        raise e

            article_json = json.loads(response_text)

            # --- 4. LƯU BÀI VIẾT LÊN FIREBASE ---
            articles_ref = db.reference('articles')
            new_article = {
                'title': article_json.get('title'),
                'category': article_json.get('category'),
                'hashtags': article_json.get('hashtags'),
                'image_prompt': article_json.get('image_prompt'),
                'content': article_json.get('content'),
                'shopee_link': shopee_link,          
                'custom_img': custom_img,            # Lấy ảnh Admin nhập
                'custom_price': custom_price,        # Lấy giá Admin nhập
                'timestamp': int(time.time() * 1000)
            }
            articles_ref.push(new_article)

            # Xóa chủ đề đã xử lý khỏi hàng đợi
            db.reference(f'queue/{first_key}').delete()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "keyword": keyword}, ensure_ascii=False).encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(err)}, ensure_ascii=False).encode('utf-8'))
