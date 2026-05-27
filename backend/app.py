import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_file
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.realpath(os.path.join(current_dir, '..', 'frontend', 'dist'))

print(f"Current directory: {current_dir}")
print(f"Frontend directory: {frontend_dir}")
print(f"Frontend exists: {os.path.exists(frontend_dir)}")
print(f"Index exists: {os.path.exists(os.path.join(frontend_dir, 'index.html'))}")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    index_path = os.path.join(frontend_dir, 'index.html')
    print(f"Index path: {index_path}")
    return send_file(index_path)

@app.route('/<path:filename>')
def serve_static(filename):
    file_path = os.path.join(frontend_dir, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "File not found", 404

# 注册蓝图
from app.routes.excel_process_routes import excel_process_bp
from app.routes.file_parse_routes import file_parse_bp
from app.routes.place_routes import place_bp
from app.routes.bid_assistant_routes import bid_assistant_bp

app.register_blueprint(excel_process_bp)
app.register_blueprint(file_parse_bp)
app.register_blueprint(place_bp)
app.register_blueprint(bid_assistant_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)