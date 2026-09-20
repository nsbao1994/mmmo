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
            # Khởi tạo Firebase
            if not firebase_admin._apps:
                firebase_cert_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                if not firebase_cert_str:
                    raise Exception("Chưa cài đặt biến môi trường FIREBASE_SERVICE_ACCOUNT")
                firebase_cert = json.loads(firebase_cert_str)
                cred = credentials.Certificate(firebase_cert)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://mmo-1-a7a47-default-rtdb.asia-southeast1.firebasedatabase.app/' 
                })

            # Lấy ID công việc từ URL
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)
            job_id = query_params.get('id', [None])[0]

            if not job_id:
                self.send_response(302)
                self.send_header('Location', '/jobs.html')
                self.end_headers()
                return

            # Rút dữ liệu công việc từ nhánh 'jobs'
            job_ref = db.reference(f'jobs/{job_id}')
            job = job_ref.get()

            if not job:
                self.send_response(302)
                self.send_header('Location', '/jobs.html')
                self.end_headers()
                return

            # Xử lý thông tin hiển thị lên thẻ Facebook
            title = f"Tuyển dụng: {job.get('title', 'Việc làm Kỹ thuật')} - {job.get('company', '')}"
            desc = f"Lương: {job.get('salary', 'Thỏa thuận')} | Khu vực: {job.get('location', 'Toàn quốc')}. Bấm để xem chi tiết và ứng tuyển!"
            finalImageUrl = job.get('image') if job.get('image') else "https://cdn-icons-png.flaticon.com/512/3281/3281289.png"

            real_url = f"/jobs.html?id={job_id}"

            # TẠO GIAO DIỆN ẢO DÀNH RIÊNG CHO BOT FACEBOOK/ZALO
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
                
                <script>
                    window.location.href = "{real_url}";
                </script>
            </head>
            <body>
                <p>Đang chuyển hướng đến bài tuyển dụng...</p>
                <a href="{real_url}">Bấm vào đây nếu trình duyệt không tự chuyển</a>
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
