
## 🚀 Cài đặt và Chạy Dự Án

### 1. Cài đặt Poetry

**Windows:**
```bash
# Tải và cài đặt Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Hoặc sử dụng pip
pip install poetry
```

**macOS/Linux:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Cài đặt Dependencies

```bash
# Clone repository
git clone <repository-url>
cd BE-HTTM

# Cài đặt dependencies
poetry install

# Nếu gặp lỗi, chạy:
poetry lock
poetry install
```

### 3. Cấu hình Database

#### Tạo Database MySQL:
```sql
CREATE DATABASE httm;
use httm;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    log_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE violations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id INT NOT NULL,
    plate_number VARCHAR(20) NOT NULL,
    timestamp_frame DATETIME NOT NULL,
    snapshot_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

#### Tạo file `.env`:
```bash
# Copy từ file mẫu
cp env.example .env
```

#### Chỉnh sửa file `.env`:

**Lưu ý:** Thay đổi `DATABASE_URL` theo cấu hình MySQL:
- `root`: username MySQL
- `123456`: password MySQL
- `localhost`: host MySQL
- `httm`: tên database

### 4. Chạy Dự Án

```bash
# Kích hoạt virtual environment
.venv\Scripts\activate

# Chạy server
poetry run uvicorn app.main:app --reload
```

### 5. Truy cập API

- **API Documentation:** http://localhost:8000/docs
- **API Base URL:** http://localhost:8000

