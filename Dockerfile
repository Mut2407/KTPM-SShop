# Sử dụng Python 3.10 (khớp với workflow CI của bạn)
FROM python:3.10-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Các biến môi trường để tối ưu Python trong Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cài đặt các thư viện phụ thuộc hệ thống (nếu cần cho Pillow/Postgres)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements và cài đặt
COPY requirements.txt /app/
# Lưu ý: File requirements.txt của bạn chưa có gunicorn.
# Bạn cần thêm gunicorn vào requirements.txt hoặc cài trực tiếp tại đây:
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn

# Copy toàn bộ source code vào container
COPY . /app/

# Mở port 8000
EXPOSE 8000

# Lệnh chạy server (khớp với Procfile của bạn)
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
