import os
import json
import time
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
        'databaseURL': '[https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/](https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/)' 
    })

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 1. Lấy 1 chủ đề đầu tiên từ hàng đợi (queue) trong Firebase
            queue_ref = db.reference('queue')
            queue_data = queue_ref.get()
            
            if not queue_data:
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "empty", "message": "Hàng đợi trống, không còn chủ đề nào để viết!"}, ensure_ascii=False).encode('utf-8'))
                return

            # Lấy key và object đầu tiên
            first_key = list(queue_data.keys())[0]
            item = queue_data[first_key]
            keyword = item.get('keyword', 'Mẹo công nghệ')

            # 2. Khởi tạo Gemini Client
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            if not gemini_api_key:
                raise ValueError("Chưa thiết lập biến môi trường GEMINI_API_KEY")
            
            client = genai.Client(api_key=gemini_api_key)

            # 3. Yêu cầu Gemini phân tích và trả về cấu trúc JSON chặt chẽ
            prompt = f"""
            Đóng vai một chuyên gia review sản phẩm và viết bài hướng dẫn kỹ thuật chuyên sâu về chủ đề: "{keyword}".
            Yêu cầu đầu ra bắt buộc phải là một đối tượng JSON thuần túy (không chứa markdown như ```json hoặc ```), có đúng các trường sau:
            - "title": Tiêu đề bài viết hấp dẫn (string)
            - "category": Chọn 1 trong các danh mục sau cho phù hợp: "Linh kiện điện tử", "Năng lượng mặt trời", "Mẹo DIY" (string)
            - "hashtags": Danh sách 4-5 thẻ hashtag liên quan (mảng string, ví dụ: ["#machhaap", "#dientu"])
            - "content": Nội dung bài viết chi tiết định dạng HTML, dùng các thẻ <h2>, <p>, <ul>, <li>. Đặc biệt ở phần cuối bài, hãy chèn một nút bấm HTML mua hàng Shopee có class là "buy-button" với link mẫu "[https://shopee.vn](https://shopee.vn)" (string)
            """

            # Gọi Gemini với cơ chế thử lại chống lỗi 503
            response_text = ""
            for _ in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    response_text = response.text.strip()
                    # Làm sạch nếu AI lỡ bọc markdown
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

            # 4. Đẩy bài viết hoàn chỉnh lên nhánh 'articles'
            articles_ref = db.reference('articles')
            new_article = {
                'title': article_json.get('title'),
                'category': article_json.get('category'),
                'hashtags': article_json.get('hashtags'),
                'content': article_json.get('content'),
                'timestamp': int(time.time() * 1000)
            }
            articles_ref.push(new_article)

            # 5. Xóa chủ đề vừa viết xong khỏi hàng đợi (queue)
            db.reference(f'queue/{first_key}').delete()

            # Trả về kết quả thành công
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response_data = {
                "status": "success",
                "processed_keyword": keyword,
                "article_title": article_json.get('title')
            }
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            error_data = {
                "status": "error",
                "message": str(err)
            }
            self.wfile.write(json.dumps(error_data, ensure_ascii=False).encode('utf-8'))
