import os
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # --- CHUYỂN KHỞI TẠO FIREBASE VÀO VÙNG AN TOÀN ---
            if not firebase_admin._apps:
                firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                if not firebase_cert_str:
                    raise Exception("Chưa cài đặt biến môi trường FIREBASE_SERVICE_ACCOUNT")
                firebase_cert = json.loads(firebase_cert_str)
                cred = credentials.Certificate(firebase_cert)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/' 
                })

            # 1. LẤY ID VÀ LOẠI BÀI VIẾT TỪ URL
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)
            article_id = query_params.get('id', [None])[0]
            post_type = query_params.get('type', ['article'])[0] # Mặc định là bài Blog nếu không có type

            if not article_id:
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return

            # 2. CHỌN NHÁNH DATABASE LINH HOẠT TÙY THEO LOẠI BÀI
            db_node = "news" if post_type == "news" else "articles"
            article_ref = db.reference(f'{db_node}/{article_id}')
            article = article_ref.get()

            if not article:
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return

            # 3. TẠO LINK CHUYỂN HƯỚNG VÀ XỬ LÝ HÌNH ẢNH/TIÊU ĐỀ
            if post_type == "news":
                # Xử lý riêng cho trang News
                real_article_url = f"/news.html?id={article_id}"
                title = article.get('title', 'Điểm Tin Nhanh - AI Tổng Hợp')
                desc = article.get('category', 'Tin tức') + " - Bản tin tổng hợp bằng AI."
                # Cố định ảnh ImgBB cho trang News
                finalImageUrl = "https://i.ibb.co/zhKJY3MP/default-banner.jpg" 
            else:
                # Xử lý cho trang Blog (Giữ nguyên logic cũ của bạn)
                real_article_url = f"/?id={article_id}"
                title = article.get('title', 'DIY Việt Nam - Review Sản Phẩm')
                desc = "Xem ngay đánh giá chi tiết và nhận mã giảm giá Freeship trên Shopee!"
                promptText = article.get('image_prompt') or title or 'technology product'
                aiImageUrl = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(promptText)}?width=1200&height=630&nologo=true"
                finalImageUrl = article.get('custom_img') if article.get('custom_img') else aiImageUrl

            # 4. TẠO GIAO DIỆN ẢO DÀNH RIÊNG CHO BOT FACEBOOK/ZALO
            html_content = f"""
            <!DOCTYPE html>
            <html lang="vi">
            <head>
                <meta charset="UTF-8">
                <title>{title}</title>
                <!-- Thẻ Meta cho Facebook và Zalo -->
                <meta property="og:title" content="{title}" />
                <meta property="og:description" content="{desc}" />
                <meta property="og:image" content="{finalImageUrl}" />
                <meta property="og:type" content="article" />
                <meta property="og:image:width" content="1200" />
                <meta property="og:image:height" content="630" />
                
                <!-- Chuyển hướng người dùng thật về trang bài viết -->
                <script>
                    window.location.href = "{real_article_url}";
                </script>
            </head>
            <body>
                <p>Đang chuyển hướng đến bài viết...</p>
                <a href="{real_article_url}">Bấm vào đây nếu trình duyệt không tự chuyển</a>
            </body>
            </html>
            """

            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))

        except Exception as err:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"Lỗi: {str(err)}".encode('utf-8'))
