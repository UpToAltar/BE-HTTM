# Phân Tích Thiết Kế Hệ Thống - Chức Năng Download Log

## 📋 Mục Lục
1. [Tổng Quan](#1-tổng-quan)
2. [Kiến Trúc Hệ Thống](#2-kiến-trúc-hệ-thống)
3. [Phân Tích Các Thành Phần](#3-phân-tích-các-thành-phần)
4. [Luồng Hoạt Động Chi Tiết](#4-luồng-hoạt-động-chi-tiết)
5. [Sequence Diagram](#5-sequence-diagram)
6. [Class Diagram](#6-class-diagram)
7. [Phân Tích Bảo Mật](#7-phân-tích-bảo-mật)
8. [Xử Lý Lỗi](#8-xử-lý-lỗi)

---

## 1. Tổng Quan

### 1.1. Mục Đích
Chức năng **Download Log** cho phép người dùng tải xuống file log (định dạng ZIP) chứa kết quả nhận diện biển số xe từ video đã được xử lý.

### 1.2. Yêu Cầu Chức Năng
- Người dùng chỉ được tải log của video mình upload
- Chỉ tải được log của video đã xử lý xong (status = "completed")
- File log phải tồn tại trên hệ thống
- Yêu cầu xác thực JWT token

### 1.3. Công Nghệ Sử Dụng
- **Backend:** FastAPI (Python), SQLAlchemy ORM
- **Frontend:** Vanilla JavaScript, Fetch API
- **Database:** MySQL
- **Authentication:** JWT (JSON Web Token)
- **File Format:** ZIP (chứa CSV + images)

---

## 2. Kiến Trúc Hệ Thống

### 2.1. Mô Hình Tổng Quan

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │  home.html   │─────▶│   home.js    │                    │
│  │  (View)      │      │ (Controller)  │                    │
│  └──────────────┘      └──────┬───────┘                    │
│                                │                             │
└────────────────────────────────┼─────────────────────────────┘
                                 │ HTTP Request
                                 │ GET /api/v1/logs/download/{id}
                                 │ Authorization: Bearer {token}
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                             │
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   main.py    │─────▶│ log_router.py│                    │
│  │  (FastAPI)   │      │  (Router)     │                    │
│  └──────────────┘      └──────┬───────┘                    │
│                                │                             │
│                                ▼                             │
│                       ┌────────────────┐                    │
│                       │auth_middleware │                    │
│                       │   (Security)   │                    │
│                       └────────┬───────┘                    │
│                                │                             │
│                                ▼                             │
│                       ┌────────────────┐                    │
│                       │ log_service.py │                    │
│                       │   (Business    │                    │
│                       │     Logic)     │                    │
│                       └────────┬───────┘                    │
│                                │                             │
│                                ▼                             │
│                       ┌────────────────┐                    │
│                       │  database.py   │                    │
│                       │   (ORM Layer)  │                    │
│                       └────────┬───────┘                    │
│                                │                             │
└────────────────────────────────┼─────────────────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   MySQL DB      │
                        │  (Data Layer)   │
                        └─────────────────┘
```

### 2.2. Kiến Trúc 3 Lớp (Three-Tier Architecture)

```
┌─────────────────────────────────────────────────────┐
│             PRESENTATION LAYER (Frontend)            │
│  - HTML (View)                                       │
│  - JavaScript (Controller)                           │
│  - CSS (Styling)                                     │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼──────────────────────────────┐
│             APPLICATION LAYER (Backend)              │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐│
│  │  Routers   │─▶│  Services   │─▶│  Middleware  ││
│  │ (Endpoint) │  │ (Business)  │  │  (Security)  ││
│  └────────────┘  └─────────────┘  └──────────────┘│
└──────────────────────┬──────────────────────────────┘
                       │ ORM (SQLAlchemy)
┌──────────────────────▼──────────────────────────────┐
│               DATA LAYER (Database)                  │
│  - MySQL Database                                    │
│  - Tables: users, videos, violations                 │
└─────────────────────────────────────────────────────┘
```

---

## 3. Phân Tích Các Thành Phần

### 3.1. Backend Components

#### 3.1.1. **Class: LogService** (`app/services/log_service.py`)

**Mục đích:** Xử lý business logic liên quan đến log file

**Thuộc tính:**
| Tên | Kiểu | Mô tả |
|-----|------|-------|
| `logs_dir` | str | Đường dẫn thư mục chứa log files |

**Phương thức:**

##### `get_log_file_path(db: Session, video_id: int, user_id: int) -> str`
- **Mục đích:** Lấy đường dẫn file log và validate
- **Tham số:**
  - `db`: Database session
  - `video_id`: ID của video
  - `user_id`: ID của user yêu cầu
- **Trả về:** Đường dẫn file log (string)
- **Exception:** 
  - `HTTPException(404)`: Video không tồn tại hoặc không có quyền
  - `HTTPException(400)`: Video chưa xử lý xong
  - `HTTPException(404)`: File log không tồn tại

**Logic Flow:**
```python
1. Query video từ DB với điều kiện:
   - video.id == video_id
   - video.user_id == user_id
   
2. IF video NOT found:
   ├─▶ RAISE HTTPException(404, "Video không tồn tại...")
   
3. IF video.status != "completed":
   ├─▶ RAISE HTTPException(400, "Video đang xử lý...")
   
4. IF video.log_path is None:
   ├─▶ RAISE HTTPException(404, "File log chưa được tạo...")
   
5. IF NOT os.path.exists(video.log_path):
   ├─▶ RAISE HTTPException(404, "File log không tồn tại...")
   
6. RETURN video.log_path
```

##### `get_video_info(db: Session, video_id: int, user_id: int) -> Video`
- **Mục đích:** Lấy thông tin video
- **Tham số:** Tương tự trên
- **Trả về:** Object Video (ORM model)

---

#### 3.1.2. **Router: log_router** (`app/routers/log_router.py`)

**Mục đích:** Định nghĩa API endpoints cho log operations

**Dependencies:**
- `log_service`: Instance của LogService
- `get_current_user`: Middleware xác thực JWT
- `get_db`: Dependency để lấy database session

**Endpoints:**

##### `GET /api/v1/logs/download/{video_id}`

**Signature:**
```python
async def download_log(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileResponse
```

**Flow:**
```
1. Nhận request với video_id từ URL path
2. Extract user_id từ JWT token (via get_current_user)
3. Gọi log_service.get_log_file_path(db, video_id, user_id)
4. Lấy tên file từ log_file_path
5. Trả về FileResponse với:
   - path: log_file_path
   - filename: tên file
   - media_type: 'application/zip'
   - headers: Content-Disposition attachment
```

**Response:**
- **Success (200):** File ZIP được download
- **Error (400):** Video chưa xử lý xong
- **Error (401):** Token không hợp lệ
- **Error (404):** Video/File không tồn tại

##### `GET /api/v1/logs/info/{video_id}`

**Signature:**
```python
async def get_log_info(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict
```

**Response JSON:**
```json
{
  "video_id": 1,
  "filename": "video.mp4",
  "status": "completed",
  "log_path": "app/upload/logs/log_1_abc123.zip",
  "has_log": true
}
```

---

#### 3.1.3. **Middleware: auth_middleware** (`app/middleware/auth_middleware.py`)

**Mục đích:** Xác thực JWT token và extract user info

**Class: HTTPBearer**
- FastAPI security scheme cho Bearer token

**Function: get_current_user**

**Signature:**
```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict
```

**Flow:**
```
1. Nhận token từ header: Authorization: Bearer {token}
2. Gọi auth_service.verify_token(token)
3. IF token invalid:
   ├─▶ RAISE HTTPException(401, "Could not validate credentials")
4. Extract payload từ token:
   - sub: user_id
   - username: username
   - exp: expiration time
5. RETURN payload (dict)
```

**Payload Structure:**
```python
{
    "sub": "1",           # user_id
    "username": "admin",  # username
    "exp": 1234567890     # expiration timestamp
}
```

---

#### 3.1.4. **Database Models** (`app/models/models.py`)

##### **Class: Video**

**Thuộc tính:**
| Column | Type | Description | Constraint |
|--------|------|-------------|------------|
| `id` | Integer | Primary key | PK, Auto Increment |
| `user_id` | Integer | Foreign key to users | FK, NOT NULL |
| `filename` | String(255) | Tên file gốc | NOT NULL |
| `filepath` | String(255) | Đường dẫn file video | NOT NULL |
| `status` | String(50) | Trạng thái xử lý | Default: "processing" |
| `log_path` | String(255) | Đường dẫn file log | Nullable |
| `created_at` | DateTime | Thời gian tạo | Default: now() |

**Relationships:**
```python
user = relationship("User", back_populates="videos")
violations = relationship("Violation", back_populates="video")
```

**Status Values:**
- `"processing"`: Đang xử lý
- `"completed"`: Hoàn thành
- `"failed"`: Thất bại
- `"pending"`: Chờ xử lý

---

### 3.2. Frontend Components

#### 3.2.1. **View: home.html**

**Cấu trúc Table:**
```html
<table class="video-table">
  <thead>
    <tr>
      <th>ID</th>
      <th>USER ID</th>
      <th>FILENAME</th>
      <th>FILEPATH</th>
      <th>STATUS</th>
      <th>CREATED AT</th>
      <th>ACTIONS</th>  <!-- Chứa nút download -->
    </tr>
  </thead>
  <tbody id="videoTableBody">
    <!-- Dynamic content rendered by JavaScript -->
  </tbody>
</table>
```

---

#### 3.2.2. **Controller: home.js**

##### **Function: renderVideoList(videos: Array)**

**Mục đích:** Render danh sách video và nút download

**Tham số:**
- `videos`: Array of video objects

**Logic:**
```javascript
FOR EACH video IN videos:
  1. canDownloadLog = (video.status === 'completed' && video.log_path)
  
  2. IF canDownloadLog:
     ├─▶ downloadBtnText = 'Tải Log'
     ├─▶ downloadBtnDisabled = ''
  ELSE:
     ├─▶ downloadBtnText = 'Đang xử lý...'
     ├─▶ downloadBtnDisabled = 'disabled'
  
  3. Render HTML với:
     - onclick="downloadLog(video.id, video.filename)"
     - disabled attribute nếu cần
```

**Output HTML:**
```html
<button class="btn btn-download" 
        onclick="downloadLog(1, 'video.mp4')" 
        disabled>
    Đang xử lý...
</button>
```

hoặc

```html
<button class="btn btn-download" 
        onclick="downloadLog(1, 'video.mp4')">
    Tải Log
</button>
```

---

##### **Function: downloadLog(videoId: number, originalFilename: string)**

**Mục đích:** Tải xuống file log từ server

**Tham số:**
- `videoId`: ID của video
- `originalFilename`: Tên file gốc (không sử dụng trong phiên bản hiện tại)

**Flow Chi Tiết:**

```javascript
1. Hiển thị thông báo: "Đang chuẩn bị tải xuống..."

2. Lấy JWT token từ localStorage
   token = getFromStorage(StorageKeys.ACCESS_TOKEN)

3. Gửi HTTP GET request:
   ├─▶ URL: `${API_BASE_URL}/logs/download/${videoId}`
   ├─▶ Method: GET
   ├─▶ Headers: {
   │     'Authorization': `Bearer ${token}`
   │   }

4. Chờ response

5. IF response.ok == false:
   ├─▶ Parse error JSON
   ├─▶ Hiển thị thông báo lỗi
   └─▶ RETURN

6. Extract filename từ Content-Disposition header:
   ├─▶ Parse: filename=log_1_abc123.zip
   ├─▶ Fallback: `log_${videoId}.zip`

7. Chuyển response thành Blob:
   blob = await response.blob()

8. Tạo Object URL từ Blob:
   url = window.URL.createObjectURL(blob)

9. Tạo thẻ <a> ảo để trigger download:
   ├─▶ link.href = url
   ├─▶ link.download = filename
   ├─▶ link.click()

10. Clean up:
    ├─▶ Remove <a> element
    ├─▶ Revoke Object URL
    └─▶ Hiển thị thông báo: "Tải xuống thành công!"

11. CATCH error:
    └─▶ Hiển thị thông báo lỗi
```

**HTTP Request Example:**
```http
GET /api/v1/logs/download/1 HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**HTTP Response Example:**
```http
HTTP/1.1 200 OK
Content-Type: application/zip
Content-Disposition: attachment; filename=log_1_abc123.zip
Content-Length: 1048576

[Binary ZIP data]
```

---

## 4. Luồng Hoạt Động Chi Tiết

### 4.1. Use Case: User Download Log

**Actor:** Người dùng đã đăng nhập

**Preconditions:**
1. User đã login và có JWT token
2. User đã upload video
3. Video đã được xử lý xong (status = "completed")
4. File log đã được tạo trên server

**Main Flow:**

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. User truy cập trang Home     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Frontend gọi API              │
│    GET /api/v1/videos/           │
│    để lấy danh sách video        │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Backend trả về list videos    │
│    với thông tin:                │
│    - id, filename, status,       │
│    - log_path, created_at        │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Frontend render table         │
│    - Video completed → Nút enabled│
│    - Video processing → Disabled  │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. User click nút "Tải Log"      │
│    onclick="downloadLog(1, ...)" │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 6. JavaScript gọi API:           │
│    GET /api/v1/logs/download/1   │
│    Header: Authorization Bearer  │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 7. Request đến FastAPI Router    │
│    → log_router.download_log()   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 8. Middleware verify JWT token   │
│    → get_current_user()          │
│    Extract: user_id, username    │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 9. Router gọi Service:           │
│    log_service.get_log_file_path()│
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 10. Service query Database:      │
│     SELECT * FROM videos         │
│     WHERE id=1 AND user_id=X     │
└──────┬──────────────────────────┘
       │
       ▼
    ┌──┴──┐
    │video│
    │exist?│
    └──┬──┘
       │
   ┌───┴────┐
   │   NO   │
   │  YES   │
   └───┬────┘
       │
       ▼ YES
┌─────────────────────────────────┐
│ 11. Service validate:            │
│     - status == "completed"?     │
│     - log_path != null?          │
│     - file exists on disk?       │
└──────┬──────────────────────────┘
       │
       ▼
    ┌──┴──┐
    │valid?│
    └──┬──┘
       │
   ┌───┴────┐
   │   NO   │ → Raise HTTPException
   │  YES   │
   └───┬────┘
       │
       ▼ YES
┌─────────────────────────────────┐
│ 12. Service return log_path      │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 13. Router tạo FileResponse:     │
│     - Read file from disk        │
│     - Set Content-Type: zip      │
│     - Set Content-Disposition    │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 14. FastAPI stream file to client│
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 15. Frontend nhận binary data    │
│     → Convert to Blob            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 16. Create Object URL from Blob  │
│     blob:http://localhost/...    │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 17. Trigger download:            │
│     - Create <a> element         │
│     - Set href = blob URL        │
│     - Set download = filename    │
│     - Click programmatically     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 18. Browser download file        │
│     → User nhận file ZIP         │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 19. Cleanup:                     │
│     - Remove <a> element         │
│     - Revoke Object URL          │
│     - Show success message       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────┐
│     END     │
└─────────────┘
```

---

### 4.2. Alternative Flows

#### **Alternative Flow 1: Token Invalid**

```
Step 8: Middleware verify JWT token
    ↓
Token invalid or expired
    ↓
Raise HTTPException(401)
    ↓
Frontend catch error
    ↓
Show message: "Phiên đăng nhập hết hạn"
    ↓
Redirect to login page
```

#### **Alternative Flow 2: Video Not Found**

```
Step 10: Service query Database
    ↓
Video not found or user_id mismatch
    ↓
Raise HTTPException(404)
    ↓
Frontend catch error
    ↓
Show message: "Video không tồn tại"
```

#### **Alternative Flow 3: Video Not Completed**

```
Step 11: Service validate status
    ↓
video.status = "processing"
    ↓
Raise HTTPException(400)
    ↓
Frontend catch error
    ↓
Show message: "Video đang xử lý..."
```

#### **Alternative Flow 4: Log File Not Found**

```
Step 11: Service validate file exists
    ↓
os.path.exists(log_path) = False
    ↓
Raise HTTPException(404)
    ↓
Frontend catch error
    ↓
Show message: "File log không tồn tại"
```

---

## 5. Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant HomeJS as home.js
    participant API as FastAPI
    participant Router as log_router
    participant Middleware as auth_middleware
    participant Service as log_service
    participant DB as Database
    participant FileSystem as File System

    User->>Browser: Click "Tải Log" button
    Browser->>HomeJS: downloadLog(videoId)
    
    Note over HomeJS: Show message: "Đang chuẩn bị..."
    
    HomeJS->>HomeJS: Get JWT token from localStorage
    
    HomeJS->>API: GET /api/v1/logs/download/{video_id}<br/>Authorization: Bearer {token}
    
    API->>Router: download_log(video_id, current_user, db)
    
    Router->>Middleware: get_current_user(credentials)
    
    Note over Middleware: Verify JWT token
    
    alt Token Invalid
        Middleware-->>Router: HTTPException(401)
        Router-->>API: 401 Unauthorized
        API-->>HomeJS: Error Response
        HomeJS-->>Browser: Show error message
        Browser-->>User: "Phiên đăng nhập hết hạn"
    else Token Valid
        Middleware-->>Router: user_payload {sub, username}
        
        Router->>Service: get_log_file_path(db, video_id, user_id)
        
        Service->>DB: SELECT * FROM videos<br/>WHERE id={video_id}<br/>AND user_id={user_id}
        
        alt Video Not Found
            DB-->>Service: None
            Service-->>Router: HTTPException(404)
            Router-->>API: 404 Not Found
            API-->>HomeJS: Error Response
            HomeJS-->>Browser: Show error message
            Browser-->>User: "Video không tồn tại"
        else Video Found
            DB-->>Service: video_record
            
            Note over Service: Validate:<br/>1. status == "completed"<br/>2. log_path exists<br/>3. file exists on disk
            
            alt Validation Failed
                Service-->>Router: HTTPException(400/404)
                Router-->>API: Error Response
                API-->>HomeJS: Error Response
                HomeJS-->>Browser: Show error message
                Browser-->>User: Error detail
            else Validation Success
                Service-->>Router: log_file_path
                
                Router->>FileSystem: Read file: {log_file_path}
                FileSystem-->>Router: File binary data
                
                Router-->>API: FileResponse(path, filename, media_type)
                
                Note over API: Stream file with headers:<br/>Content-Type: application/zip<br/>Content-Disposition: attachment
                
                API-->>HomeJS: Binary file data (ZIP)
                
                Note over HomeJS: Process download:<br/>1. Convert to Blob<br/>2. Create Object URL<br/>3. Trigger download
                
                HomeJS->>Browser: Create <a> element and click
                Browser->>Browser: Download file
                
                HomeJS-->>Browser: Show success message
                Browser-->>User: "Tải xuống thành công!"<br/>File saved to Downloads
            end
        end
    end
```

---

## 6. Class Diagram

```mermaid
classDiagram
    class LogService {
        -logs_dir: str
        +get_log_file_path(db: Session, video_id: int, user_id: int) str
        +get_video_info(db: Session, video_id: int, user_id: int) Video
    }

    class LogRouter {
        -log_service: LogService
        +download_log(video_id: int, current_user: dict, db: Session) FileResponse
        +get_log_info(video_id: int, current_user: dict, db: Session) dict
    }

    class AuthMiddleware {
        -security: HTTPBearer
        -auth_service: AuthService
        +get_current_user(credentials: HTTPAuthorizationCredentials) dict
    }

    class AuthService {
        -secret_key: str
        -algorithm: str
        +verify_token(token: str) dict
        +create_access_token(data: dict) str
    }

    class Video {
        +id: int
        +user_id: int
        +filename: str
        +filepath: str
        +status: str
        +log_path: str
        +created_at: datetime
    }

    class User {
        +id: int
        +username: str
        +password_hash: str
        +created_at: datetime
    }

    class Database {
        +engine: Engine
        +SessionLocal: sessionmaker
        +get_db() Session
    }

    class FileResponse {
        +path: str
        +filename: str
        +media_type: str
        +headers: dict
    }

    LogRouter --> LogService : uses
    LogRouter --> AuthMiddleware : depends on
    LogRouter --> Database : depends on
    LogRouter --> FileResponse : returns
    
    LogService --> Database : uses
    LogService --> Video : queries
    
    AuthMiddleware --> AuthService : uses
    
    Video --> User : belongs to
    
    LogService ..> HTTPException : raises
    AuthMiddleware ..> HTTPException : raises
```

---

## 7. Phân Tích Bảo Mật

### 7.1. Authentication (Xác Thực)

**Phương thức:** JWT (JSON Web Token)

**Flow:**
```
1. User login → Backend tạo JWT token
2. Frontend lưu token vào localStorage
3. Mỗi request → Gửi token trong header
4. Backend verify token → Extract user info
```

**Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "1",
    "username": "admin",
    "exp": 1234567890
  },
  "signature": "..."
}
```

**Security Measures:**
- Token signed với SECRET_KEY
- Token có thời gian hết hạn (30 phút)
- Token verify mỗi request

---

### 7.2. Authorization (Phân Quyền)

**Access Control:**

```python
# Kiểm tra ownership
video = db.query(Video).filter(
    Video.id == video_id,
    Video.user_id == user_id  # ← User chỉ access video của mình
).first()
```

**Prevent:**
- User A không thể tải log của User B
- Unauthorized access bị chặn ở middleware
- SQL Injection prevented by ORM

---

### 7.3. File Access Control

**Validation Layers:**

```
Layer 1: Authentication
    ↓ Token valid?
Layer 2: Authorization  
    ↓ User owns video?
Layer 3: Status Check
    ↓ Video completed?
Layer 4: Path Validation
    ↓ Log path exists?
Layer 5: File System Check
    ↓ File exists on disk?
Access Granted
```

---

### 7.4. Security Best Practices

✅ **Implemented:**
1. JWT token authentication
2. User ownership validation
3. Path traversal prevention (no user input in path)
4. Status validation (only completed videos)
5. File existence check
6. HTTPS recommended in production
7. CORS configured

❌ **Not Implemented (Recommendations):**
1. Rate limiting (prevent abuse)
2. File encryption at rest
3. Audit logging (who downloaded what)
4. Token refresh mechanism
5. IP whitelist (optional)

---

## 8. Xử Lý Lỗi

### 8.1. Error Hierarchy

```
HTTPException (Base)
    ├── 400 Bad Request
    │   └── Video chưa xử lý xong
    ├── 401 Unauthorized
    │   ├── Token invalid
    │   ├── Token expired
    │   └── Missing token
    └── 404 Not Found
        ├── Video không tồn tại
        ├── Không có quyền truy cập
        ├── Log path null
        └── File không tồn tại
```

### 8.2. Error Handling Flow

```python
# Backend
try:
    log_path = log_service.get_log_file_path(db, video_id, user_id)
    return FileResponse(...)
except HTTPException as e:
    # FastAPI tự động convert thành HTTP response
    raise e
```

```javascript
// Frontend
try {
    const response = await fetch(...);
    if (!response.ok) {
        const error = await response.json();
        showMessage(error.detail);  // ← Hiển thị lỗi cho user
        return;
    }
    // Process success
} catch (error) {
    showMessage('Có lỗi xảy ra: ' + error.message);
}
```

### 8.3. Error Response Format

**Backend Response:**
```json
{
  "detail": "Video không tồn tại hoặc bạn không có quyền truy cập"
}
```

**Frontend Display:**
```
Toast Message: "Video không tồn tại hoặc bạn không có quyền truy cập"
```

---

## 9. Performance Considerations

### 9.1. Database Query Optimization

**Index Recommendations:**
```sql
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_user_status ON videos(user_id, status);
```

**Query Analysis:**
```sql
-- Optimized query với composite index
SELECT * FROM videos 
WHERE id = ? AND user_id = ?
-- Uses index: (id, user_id) hoặc PRIMARY KEY + user_id index
```

### 9.2. File Streaming

**FastAPI FileResponse Benefits:**
- Streaming (không load toàn bộ file vào RAM)
- Chunked transfer encoding
- Efficient for large files

**Memory Usage:**
```
Traditional approach: Load entire file → RAM usage = File size
Streaming approach: Load chunks → RAM usage = Chunk size (small)
```

### 9.3. Frontend Optimization

**Blob Handling:**
```javascript
// Efficient: Stream blob directly
const blob = await response.blob();
const url = URL.createObjectURL(blob);

// Clean up memory
URL.revokeObjectURL(url);  // ← Important!
```

---

## 10. Testing Scenarios

### 10.1. Unit Tests

**Test LogService:**
```python
def test_get_log_file_path_success():
    # Arrange
    db = mock_db_session()
    video = create_mock_video(status="completed", log_path="/path/to/log.zip")
    
    # Act
    result = log_service.get_log_file_path(db, 1, 1)
    
    # Assert
    assert result == "/path/to/log.zip"

def test_get_log_file_path_video_not_found():
    # Arrange
    db = mock_db_session()
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        log_service.get_log_file_path(db, 999, 1)
    assert exc.status_code == 404

def test_get_log_file_path_not_completed():
    # Arrange
    db = mock_db_session()
    video = create_mock_video(status="processing")
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        log_service.get_log_file_path(db, 1, 1)
    assert exc.status_code == 400
```

### 10.2. Integration Tests

```python
def test_download_log_endpoint(client, auth_headers):
    # Arrange
    video_id = create_test_video(status="completed")
    
    # Act
    response = client.get(
        f"/api/v1/logs/download/{video_id}",
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
```

### 10.3. E2E Tests (Frontend)

```javascript
describe('Download Log Feature', () => {
  it('should download log when button clicked', async () => {
    // Arrange
    const videoId = 1;
    mockApiResponse('/logs/download/1', createMockZipBlob());
    
    // Act
    await downloadLog(videoId, 'test.mp4');
    
    // Assert
    expect(createObjectURL).toHaveBeenCalled();
    expect(document.querySelector('a[download]')).toBeTruthy();
  });
  
  it('should show error when video not completed', async () => {
    // Arrange
    mockApiError('/logs/download/1', 400, 'Video chưa xử lý xong');
    
    // Act
    await downloadLog(1, 'test.mp4');
    
    // Assert
    expect(showMessage).toHaveBeenCalledWith(
      expect.stringContaining('Video chưa xử lý xong')
    );
  });
});
```

---

## 11. Deployment Considerations

### 11.1. Environment Variables

```bash
# Production
DATABASE_URL=mysql+pymysql://user:pass@prod-db:3306/httm
SECRET_KEY=super-secret-production-key-change-me
API_HOST=0.0.0.0
API_PORT=8000
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Staging
DATABASE_URL=mysql+pymysql://user:pass@staging-db:3306/httm
SECRET_KEY=staging-secret-key
```

### 11.2. File Storage

**Local Development:**
```
app/upload/logs/
```

**Production Options:**
1. **Local Storage:** Same as dev
2. **NFS/Shared Storage:** For multi-server deployment
3. **S3/Cloud Storage:** For scalability

**Recommendations:**
- Use cloud storage (S3, GCS) for production
- Implement signed URLs for secure download
- Set up lifecycle policies (auto-delete old logs)

### 11.3. Monitoring

**Metrics to Track:**
- Download success rate
- Average download time
- Error rate by type (401, 404, 400)
- File size distribution
- Concurrent downloads

**Logging:**
```python
import logging

logger.info(f"User {user_id} downloading log for video {video_id}")
logger.error(f"File not found: {log_path}")
```

---

## 12. Tổng Kết

### 12.1. Design Patterns Used

1. **Three-Tier Architecture:** Presentation - Application - Data
2. **Dependency Injection:** FastAPI Depends
3. **Service Layer Pattern:** LogService encapsulates business logic
4. **Repository Pattern:** SQLAlchemy ORM
5. **Middleware Pattern:** Authentication middleware
6. **Error Handling Pattern:** HTTPException propagation

### 12.2. SOLID Principles

- **S - Single Responsibility:** 
  - LogService: Business logic only
  - LogRouter: HTTP handling only
  - AuthMiddleware: Authentication only

- **O - Open/Closed:** 
  - Easy to extend with new log formats
  - Can add new validation rules without changing core logic

- **L - Liskov Substitution:**
  - LogService có thể swap với mock trong tests

- **I - Interface Segregation:**
  - LogService có 2 methods độc lập: get_log_file_path, get_video_info

- **D - Dependency Inversion:**
  - LogRouter depends on LogService abstraction
  - Database injected via dependency

### 12.3. Key Takeaways

✅ **Strengths:**
1. Clear separation of concerns
2. Comprehensive error handling
3. Security-first approach
4. Efficient file streaming
5. Clean architecture

⚠️ **Areas for Improvement:**
1. Add rate limiting
2. Implement caching
3. Add comprehensive logging
4. Implement retry mechanism
5. Add download progress tracking

### 12.4. Learning Outcomes

Từ bài phân tích này, sinh viên có thể học được:

1. **System Design:** Cách thiết kế REST API
2. **Security:** JWT authentication & authorization
3. **File Handling:** Streaming large files efficiently
4. **Error Handling:** Comprehensive error management
5. **Frontend-Backend Integration:** Full-stack communication
6. **Best Practices:** Clean code, SOLID principles
7. **Testing:** Unit, integration, E2E testing strategies

---

## Tài Liệu Tham Khảo

1. **FastAPI Documentation:** https://fastapi.tiangolo.com/
2. **SQLAlchemy ORM:** https://docs.sqlalchemy.org/
3. **JWT Specification:** https://jwt.io/
4. **REST API Design:** https://restfulapi.net/
5. **Clean Architecture:** Robert C. Martin
6. **SOLID Principles:** https://en.wikipedia.org/wiki/SOLID

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-27  
**Author:** System Analysis Team  
**Course:** Phân Tích Thiết Kế Hệ Thống

