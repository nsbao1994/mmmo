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

            # Lấy ID bài viết từ URL
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)
            article_id = query_params.get('id', [None])[0]

            if not article_id:
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return

            # Gọi dữ liệu bài viết từ Firebase
            article_ref = db.reference(f'articles/{article_id}')
            article = article_ref.get()

            if not article:
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return

            # Xử lý hình ảnh (Ưu tiên ảnh tự nhập, nếu không lấy ảnh AI)
            title = article.get('title', 'DIY Việt Nam - Review Sản Phẩm')
            promptText = article.get('image_prompt') or title or 'technology product'
            aiImageUrl = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(promptText)}?width=1200&height=630&nologo=true"
            finalImageUrl = article.get('custom_img') if article.get('custom_img') else aiImageUrl

            # Link bài viết thực tế để chuyển hướng người dùng
            real_article_url = f"/?id={article_id}"

            # TẠO GIAO DIỆN ẢO DÀNH RIÊNG CHO BOT FACEBOOK/ZALO
            html_content = f"""
            <!DOCTYPE html>
            <html lang="vi">
            <head>
                <meta charset="UTF-8">
                <title>{title}</title>
                <!-- Thẻ Meta cho Facebook và Zalo -->
                <meta property="og:title" content="{title}" />
                <meta property="og:description" content="Xem ngay đánh giá chi tiết và nhận mã giảm giá Freeship trên Shopee!" />
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
