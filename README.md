# ⚡ FastMVC

> **FastAPI 기반 MVC 스타일 백엔드 프레임워크**
> _모듈화된 구조로 유지보수성과 확장성을 높인 경량 서버 아키텍처_

---

## ✨ 개요
FastMVC는 FastAPI를 기반으로 한 구조화된 백엔드 프로젝트입니다.
`routers`, `models`, `services`, `middleware`, `core`를 분리해 요청 처리, 비즈니스 로직,
DB/스토리지 연결을 명확하게 분리합니다.

---

## 📁 프로젝트 구조
```
app/
 ┣ routers/       → API 엔드포인트
 ┣ models/        → 요청/응답 스키마
 ┣ services/      → 비즈니스 로직
 ┣ middleware/    → 요청 필터링 및 연결 주입
 ┣ core/          → 로깅, DB 및 스토리지 연결
 ┣ utils.py       → 공통 응답 및 파일 유틸리티
 ┗ main.py        → FastAPI 앱 생성
operate.py        → 앱 실행 진입점
```

---

## 🧠 아키텍처 요약

### 엔트리 포인트
- `operate.py`가 실제 서버 실행 진입점입니다.
- `main.py`는 FastAPI 앱 생성과 예외 핸들러 구성만 담당합니다.

### 미들웨어
- `app/middleware/middleware.py`에는 다음 기능이 있습니다:
  - `connection_context` : 요청 시 `request.state`에 DB/MinIO 연결을 주입
  - `ip_access` : 허용된 IP 및 API 경로 필터링

### DB/MinIO 연결
- `app/core/database.py` : DB 연결 및 세션 관리 유틸
- `app/core/storage.py` : MinIO 클라이언트 래퍼

---

## 🔧 설치 방법

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

### MinIO 사용 시
```bash
pip install minio
```

---

## 🚀 실행 방법

```bash
python operate.py
```

---

## 🌐 설정(Environment)
다음 환경 변수를 `.env`에 추가하면 DB/MinIO 연결을 활성화할 수 있습니다.

```env
HOST=127.0.0.1
PORT=8000
APP_ENV=local
DEBUG=true
DB_URL=sqlite:///./data/app.db
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

- `DB_URL`: 다음 DB URL 형식을 지원합니다.
  - SQLite: `sqlite:///./data/app.db`
  - PostgreSQL: `postgresql+psycopg://user:pass@host:port/dbname`
  - MariaDB/MySQL: `mysql+pymysql://user:pass@host:port/dbname`
- `MINIO_*`: MinIO 클라이언트 설정입니다.

> `DB_URL`가 제공되었지만 DB 연결에 실패하는 경우, API는 `500 DB_CONNECTION_ERROR` 응답을 반환합니다.

---

## 🧪 테스트

```bash
pytest -v
```

또는 로컬 테스트 스크립트:

```bash
python run_async_test.py
```

---

## 📌 참고
- API 응답 포맷은 `app.utils.build_api_response()`로 통일되어 있습니다.
- 서버 실행은 `operate.py`를 기준으로 합니다.
- DB/MinIO 연결은 미들웨어에서 요청 상태로 주입되어 사용됩니다.
