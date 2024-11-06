import http.server
import cgi
import os
import random
import string
import threading
import time
from socketserver import TCPServer
from datetime import datetime, timedelta
import urllib.parse

UPLOAD_DIR = "/tmp/uploads"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB in Bytes

os.makedirs(UPLOAD_DIR, exist_ok=True)

def cleanup_old_files():
    while True:
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path) and datetime.now() - datetime.fromtimestamp(os.path.getctime(file_path)) > timedelta(days=1):
                os.remove(file_path)
        time.sleep(3600)

threading.Thread(target=cleanup_old_files, daemon=True).start()

def generate_random_filename():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1" />
                    <title>ReviveMii Image Transfer</title>
                    <style>
                        body { font-family: Arial, sans-serif; background-color: #f4f4f4; text-align: center; }
                        .container { width: 90%; max-width: 400px; margin: 0 auto; padding: 20px; background: #ffffff; border: 2px solid #ddd; }
                        h1 { font-size: 20px; color: #333; }
                        .button { font-size: 16px; padding: 12px 20px; margin-top: 15px; color: #fff; background-color: #f0b420; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
                        .button:disabled { background-color: #ccc; }
                        .form-group { margin-top: 15px; }
                        .form-group label { font-size: 12px; color: #555; display: block; text-align: left; margin-bottom: 5px; }
                        .form-group input[type="file"] { display: block; width: 100%; }
                        .form-group input[type="text"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px; font-size: 12px; }
                        .footer { margin-top: 20px; font-size: 12px; color: #666; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>ReviveMii Image Transfer</h1>
                        <form action="/upload" method="post" enctype="multipart/form-data">
                            <div class="form-group">
                                <label for="file">Select image to transfer from your 3DS or Wii U. You can download it from your PC:</label>
                                <input type="file" name="file" id="file" required>
                            </div>
                            <div class="form-group">
                                <!-- <label for="comment">Add comment (up to 80 characters):</label> -->
                                <!-- <input type="text" name="comment" id="comment" maxlength="80"> -->
                            </div>
                            <input type="submit" value="Transfer" class="button">
                        </form>
                        <div class="footer">
                            <p><a href="https://revivemii.fr.to/" target="_blank" style="text-decoration: none; color: #0073e6;">Visit ReviveMii</a></p>
                        </div>
                    </div>
                </body>
                </html>
            """.encode('utf-8'))
        elif self.path.startswith('/download/'):
            file_id = self.path.split('/')[-1]
            file_path = os.path.join(UPLOAD_DIR, file_id)
            if os.path.isfile(file_path):
                self.send_response(200)
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename={file_id}.jpg")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found.")
        else:
            self.send_error(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/upload':
            content_type, pdict = cgi.parse_header(self.headers.get('Content-Type'))
            if content_type == 'multipart/form-data':
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
                file_item = form['file']

                if file_item.filename:
                    file_item.file.seek(0, os.SEEK_END)
                    file_size = file_item.file.tell()
                    file_item.file.seek(0)
                    if file_size > MAX_FILE_SIZE:
                        self.send_error(413, "File too large. Maximum size is 500MB.")
                        return

                    file_id = generate_random_filename()
                    file_path = os.path.join(UPLOAD_DIR, file_id)

                    with open(file_path, "wb") as f:
                        f.write(file_item.file.read())

                    download_url = f"http://{self.headers['Host']}/download/{file_id}"
                    qr_code_url = f"http://api.qrserver.com/v1/create-qr-code/?data={urllib.parse.quote(download_url)}&size=150x150"

                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1" />
                            <title>Upload Successful</title>
                            <style>
                                body {{ font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f4; }}
                                .container {{ width: 90%; max-width: 400px; margin: 0 auto; padding: 20px; background: #ffffff; border: 2px solid #ddd; }}
                                h1 {{ font-size: 20px; color: #333; }}
                                p {{ color: #666; font-size: 14px; }}
                                .qr-code {{ margin-top: 15px; }}
                                .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>Upload Successful</h1>
                                <p>Your image has been uploaded successfully.</p>
                                <p>Scan the QR code to download the image:</p>
                                <div class="qr-code">
                                    <img src="{qr_code_url}" alt="QR Code">
                                </div>
                                <p><a href="{download_url}" style="text-decoration: none; color: #0073e6;">Direct Download Link</a></p>
                                <p><em>Note: The file will expire in 24 hours.</em></p>
                                <div class="footer">
                                    <p><a href="https://revivemii.fr.to/" target="_blank" style="text-decoration: none; color: #0073e6;">Visit ReviveMii</a></p>
                                </div>
                            </div>
                        </body>
                        </html>
                    """.encode('utf-8'))
                else:
                    self.send_error(400, "No file uploaded.")
            else:
                self.send_error(400, "Invalid request.")

with TCPServer(('0.0.0.0', 25581), SimpleHTTPRequestHandler) as httpd:
    print("Serving on http://0.0.0.0:25581")
    httpd.serve_forever()
