# data_explorer_backend

FastAPI 기반의 MVC 구조 백엔드 서버. 비동기 작업 처리, DB 연결, MinIO 파일 스토리지를 지원하는 확장 가능한 API 서버 템플릿.

## 기술 스택

- **Framework**: FastAPI 0.115.11 + Uvicorn 0.34.0
- **ORM**: SQLAlchemy 2.0.24 (SQLite / PostgreSQL / MySQL)
- **Validation**: Pydantic 2.8.1
- **Storage**: MinIO 7.1.0
- **File Processing**: Pillow, pdf2image, pypdfium2, pandas
- **Testing**: pytest 8.4.2 + httpx 0.28.1
- **CLI**: rich 14.1.0

## 서버 실행

```bash
# 가상환경 설정
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 서버 시작 (포트 9000)
python operate.py

# 테스트 실행
pytest -v
```

- `APP_ENV=local` → uvicorn + hot reload
- `APP_ENV=prod` (Windows) → uvicorn 멀티 워커
- `APP_ENV=prod` (Linux) → gunicorn + UvicornWorker

## 환경 변수 (.env)

```env
HOST=0.0.0.0
PORT=9000
APP_ENV=local
DEBUG=True

# DB (기본값: SQLite)
DB_URL=sqlite:///./data/app.db
# DB_URL=postgresql+psycopg://user:password@localhost:5432/mydb
# DB_URL=mysql+pymysql://user:password@localhost:3306/mydb

# MinIO (선택)
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

## 디렉토리 구조

```
data_explorer_backend/
├── main.py                    # FastAPI 앱 생성, 미들웨어/예외 핸들러 등록
├── operate.py                 # 서버 진입점 (uvicorn/gunicorn 실행)
├── settings.py                # pydantic-settings 기반 환경 설정
├── requirements.txt
├── pytest.ini
├── app/
│   ├── utils.py               # FileManager, FileUtils, PrintUtils, 응답 빌더
│   ├── core/
│   │   ├── database.py        # SQLAlchemy 커넥터 (DatabaseConnector)
│   │   ├── storage.py         # MinIO 클라이언트 래퍼
│   │   └── logging_config.py  # 요청 로깅 설정 (로테이팅 파일 로그)
│   ├── middleware/
│   │   └── middleware.py      # connection_context (DB/MinIO 주입), ip_access (IP 필터링)
│   ├── routers/
│   │   └── items.py           # POST /items/~test, POST /items/~file
│   ├── models/
│   │   └── test_model.py      # _testRequest Pydantic 모델
│   ├── services/
│   │   └── _test_operation.py # _testProcessor (condition → generation → parsing)
│   ├── operate/
│   │   └── operate_service.py # operate_run() 비동기 오케스트레이터
│   └── test/
│       ├── conftest.py        # TestClient fixture
│       └── test_basic.py      # 파라미터화된 기본 테스트
└── logs/server.log
```

## 핵심 아키텍처 패턴

### 1. 비동기 처리 (202 Accepted 패턴)
요청 수신 즉시 `operation_id`를 반환하고, 실제 처리는 BackgroundTask로 실행.

### 2. 미들웨어 의존성 주입
`connection_context` 미들웨어가 DB/MinIO 클라이언트를 `request.state`에 주입 → 라우터에서 `request.state.db`로 접근.

### 3. 동적 서비스 로딩
`importlib`로 모델 타입에 따라 서비스 프로세서를 런타임에 로드.

### 4. IP 화이트리스트
`ALLOWED_IPS`: `127.0.0.1`, `localhost`, `testclient` — 운영 배포 전 설정 필요.

## 표준 API 응답 형식

```json
{
  "status_code": 200,
  "error_code": "A001",
  "message": "Success message",
  "data": {},
  "errors": "",
  "operation_id": "hex-uuid"
}
```

## 새 라우터/서비스 추가 방법

1. `app/models/` 에 Pydantic 요청 모델 추가
2. `app/services/` 에 `condition()`, `generation()`, `parsing()` 메서드를 가진 프로세서 클래스 추가
3. `app/routers/` 에 라우터 추가
4. `main.py` 에서 라우터 `include_router()` 등록

## 유틸리티

- `build_api_response()` / `make_json_response()` — 표준 응답 생성
- `raise_http()` — 표준 HTTP 예외 발생
- `FileManager` — 사용자별 업로드 디렉토리 관리
- `FileUtils` — 파일 확장자 검증, 이미지→PDF 변환, PDF 페이지 수 추출
- `PrintUtils` — rich 기반 터미널 스피너 컨텍스트 매니저
