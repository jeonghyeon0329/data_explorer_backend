# data_explorer_backend — 기획 문서

## 1. 서비스 개요

CSV / Excel / JSON 파일을 업로드하고, 데이터를 탐색·시각화·공유할 수 있는 웹 서비스의 백엔드 API 서버.

| 항목 | 내용 |
|------|------|
| 프레임워크 | FastAPI 0.115 |
| 인증 방식 | JWT Bearer Token |
| DB | SQLite (개발) / PostgreSQL (운영) |
| 파일 스토리지 | MinIO (로컬) / S3 호환 (운영) |
| 비동기 처리 | FastAPI BackgroundTask |

---

## 2. 사용자 역할 (Role)

| 역할 | 설명 | 권한 |
|------|------|------|
| `admin` | 관리자 | 모든 사용자·데이터셋 조회/수정/삭제 |
| `user` | 일반 사용자 | 자신의 데이터셋만 CRUD, 공개 데이터셋 읽기 |

- `User` 테이블에 `role` 컬럼 추가 (`'user'` 기본값)
- 최초 가입자는 `user` 역할, 관리자는 DB 직접 또는 `/admin/users/{id}` API로 역할 변경

---

## 3. 기능 목록

### 3-1. 인증 (구현 완료)
| 기능 | 엔드포인트 | 상태 |
|------|-----------|------|
| 회원가입 | POST /accounts/signup/ | 완료 |
| 로그인 | POST /accounts/login/ | 완료 |
| 비밀번호 재설정 요청 | POST /accounts/forgot-password/ | 완료 |
| 비밀번호 재설정 | POST /accounts/reset-password/ | 완료 |

### 3-2. 데이터셋 관리
| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 업로드 | POST /datasets/ | CSV·XLSX·JSON 파일 업로드 + 메타데이터 파싱 |
| 목록 조회 | GET /datasets/ | 내 데이터셋 + 공개 데이터셋 목록 (페이지네이션) |
| 상세 조회 | GET /datasets/{id} | 메타데이터 + 컬럼 정보 |
| 수정 | PATCH /datasets/{id} | 이름·설명·공개여부 수정 |
| 삭제 | DELETE /datasets/{id} | 파일 + DB 레코드 삭제 |
| 미리보기 | GET /datasets/{id}/preview | 행 데이터 (페이지네이션·정렬·필터) |
| 컬럼 통계 | GET /datasets/{id}/columns/{col} | 컬럼별 통계 (min/max/mean/null_count/unique_count) |

### 3-3. 차트
| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 차트 생성 | POST /datasets/{id}/charts/ | 차트 설정 저장 |
| 차트 목록 | GET /datasets/{id}/charts/ | 데이터셋의 차트 목록 |
| 차트 데이터 | GET /datasets/{id}/charts/{chart_id} | 차트 렌더링용 데이터 반환 |
| 차트 삭제 | DELETE /datasets/{id}/charts/{chart_id} | |

### 3-4. 관리자
| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 사용자 목록 | GET /admin/users/ | 전체 사용자 목록 (페이지네이션) |
| 사용자 수정 | PATCH /admin/users/{id} | 역할 변경·활성화/비활성화 |
| 사용자 삭제 | DELETE /admin/users/{id} | |
| 전체 데이터셋 | GET /admin/datasets/ | 전체 데이터셋 목록 |

---

## 4. DB 스키마

### 4-1. users (기존 + role 컬럼 추가)
```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(30)  UNIQUE NOT NULL,
    name            VARCHAR(255),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(10)  NOT NULL DEFAULT 'user',  -- 'user' | 'admin'
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL
);
```

### 4-2. password_resets (기존 유지)
```sql
CREATE TABLE password_resets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      VARCHAR(255) UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL
);
```

### 4-3. datasets (신규)
```sql
CREATE TABLE datasets (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL,
    description       TEXT,
    file_type         VARCHAR(10)  NOT NULL,   -- 'csv' | 'xlsx' | 'json'
    original_filename VARCHAR(255) NOT NULL,
    file_size         INTEGER      NOT NULL,   -- bytes
    row_count         INTEGER      NOT NULL DEFAULT 0,
    column_count      INTEGER      NOT NULL DEFAULT 0,
    storage_path      VARCHAR(500) NOT NULL,   -- MinIO 객체 키 또는 로컬 경로
    is_public         BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        DATETIME     NOT NULL,
    updated_at        DATETIME     NOT NULL
);
```

### 4-4. dataset_columns (신규)
```sql
CREATE TABLE dataset_columns (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id   INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    column_name  VARCHAR(255) NOT NULL,
    column_order INTEGER      NOT NULL,
    dtype        VARCHAR(50)  NOT NULL,   -- 'int' | 'float' | 'str' | 'datetime' | 'bool'
    null_count   INTEGER      NOT NULL DEFAULT 0,
    unique_count INTEGER      NOT NULL DEFAULT 0,
    min_value    VARCHAR(255),
    max_value    VARCHAR(255),
    sample_values TEXT        -- JSON 배열 (최대 5개 샘플)
);
```

### 4-5. charts (신규)
```sql
CREATE TABLE charts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id  INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    chart_type  VARCHAR(20)  NOT NULL,  -- 'bar' | 'line' | 'pie' | 'scatter' | 'histogram'
    x_column    VARCHAR(255),
    y_column    VARCHAR(255),
    config_json TEXT,                   -- 추가 설정 (JSON)
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);
```

---

## 5. API 상세 명세

### 공통 응답 형식
```json
{
  "status_code": 200,
  "error_code": "A001",
  "message": "Success",
  "data": {},
  "errors": "",
  "operation_id": ""
}
```

### 공통 에러 코드
| 코드 | HTTP | 설명 |
|------|------|------|
| A001 | - | 성공 |
| A401 | 401 | 인증 토큰 없음 또는 만료 |
| A403 | 403 | 권한 없음 |
| A404 | 404 | 리소스 없음 |
| D001 | 400 | 지원하지 않는 파일 형식 |
| D002 | 400 | 파일 파싱 실패 |
| D003 | 413 | 파일 크기 초과 (최대 50MB) |
| D101 | 404 | 데이터셋 없음 |
| D102 | 403 | 데이터셋 접근 권한 없음 |
| C001 | 403 | IP 접근 차단 |

### 인증 헤더
로그인 이후 모든 요청에 포함:
```
Authorization: Bearer <access_token>
```

---

### POST /datasets/
파일 업로드 및 메타데이터 저장.

**Request** `multipart/form-data`
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| file | File | Y | CSV / XLSX / JSON (최대 50MB) |
| name | string | N | 데이터셋 이름 (미입력 시 파일명 사용) |
| description | string | N | 설명 |
| is_public | boolean | N | 공개 여부 (기본: false) |

**Response 201**
```json
{
  "data": {
    "dataset_id": 1,
    "name": "sales_2024",
    "file_type": "csv",
    "row_count": 5000,
    "column_count": 12,
    "columns": [
      { "name": "date", "dtype": "datetime", "null_count": 0 },
      { "name": "revenue", "dtype": "float", "null_count": 3 }
    ]
  }
}
```

---

### GET /datasets/
내 데이터셋 + 공개 데이터셋 목록.

**Query Params**
| 파라미터 | 기본값 | 설명 |
|---------|-------|------|
| page | 1 | 페이지 번호 |
| size | 20 | 페이지 크기 (최대 100) |
| mine | true | true: 내 것만 / false: 공개 포함 |
| q | - | 이름 검색 |

**Response 200**
```json
{
  "data": {
    "total": 42,
    "page": 1,
    "size": 20,
    "items": [
      {
        "id": 1, "name": "sales_2024", "file_type": "csv",
        "row_count": 5000, "is_public": false,
        "created_at": "2026-06-14T10:00:00Z"
      }
    ]
  }
}
```

---

### GET /datasets/{id}/preview
행 데이터 미리보기.

**Query Params**
| 파라미터 | 기본값 | 설명 |
|---------|-------|------|
| page | 1 | 페이지 번호 |
| size | 50 | 행 수 (최대 500) |
| sort_by | - | 정렬 컬럼명 |
| sort_dir | asc | asc / desc |
| filter | - | 필터 JSON (예: `{"col":"revenue","op":"gt","val":1000}`) |

**Response 200**
```json
{
  "data": {
    "total_rows": 5000,
    "page": 1,
    "columns": ["date", "revenue", "category"],
    "rows": [
      ["2024-01-01", 1500.5, "A"],
      ["2024-01-02", 980.0, "B"]
    ]
  }
}
```

---

### POST /datasets/{id}/charts/
차트 설정 저장.

**Request JSON**
```json
{
  "title": "월별 매출 추이",
  "chart_type": "line",
  "x_column": "date",
  "y_column": "revenue",
  "config": {
    "color": "#4f83cc",
    "show_legend": true,
    "aggregation": "sum"
  }
}
```

---

### GET /datasets/{id}/charts/{chart_id}
차트 렌더링 데이터 반환.

**Response 200**
```json
{
  "data": {
    "chart_type": "line",
    "title": "월별 매출 추이",
    "labels": ["2024-01", "2024-02", "2024-03"],
    "series": [{ "name": "revenue", "data": [45000, 52000, 48000] }],
    "config": { "color": "#4f83cc" }
  }
}
```

---

## 6. 인증 미들웨어 설계

현재 `ip_access` / `connection_context` 미들웨어 외에 **JWT 검증 의존성** 추가:

```
app/core/auth.py          → create_access_token, decode_access_token (기존)
app/dependencies/auth.py  → get_current_user(token) → User 반환 (신규)
app/dependencies/admin.py → require_admin(user) → role 검증 (신규)
```

- 공개 엔드포인트: `/accounts/*`
- 인증 필요: `/datasets/*`, `/charts/*`
- 관리자 전용: `/admin/*`

---

## 7. 파일 처리 흐름

```
클라이언트 업로드
    ↓
POST /datasets/ (multipart)
    ↓
파일 형식 검증 (csv / xlsx / json)
    ↓
pandas로 파싱 → row_count, column_count, 컬럼 통계 추출
    ↓
파일 저장 (MinIO 또는 로컬 uploads/)
    ↓
datasets + dataset_columns 테이블 저장
    ↓
201 응답 반환
```

미리보기 요청 시:
```
GET /datasets/{id}/preview
    ↓
storage_path에서 파일 읽기 (pandas)
    ↓
필터 / 정렬 / 페이지네이션 적용
    ↓
JSON 직렬화 후 응답
```

---

## 8. 디렉토리 구조 (추가 예정)

```
app/
├── dependencies/
│   ├── auth.py           # get_current_user
│   └── admin.py          # require_admin
├── models/
│   ├── user_model.py     # User(role 추가), PasswordReset
│   ├── dataset_model.py  # Dataset, DatasetColumn  (신규)
│   ├── chart_model.py    # Chart  (신규)
│   └── ...
├── routers/
│   ├── accounts.py       # 기존
│   ├── datasets.py       # 신규
│   └── admin.py          # 신규
├── services/
│   ├── dataset_service.py  # 파싱, 저장, 조회 로직
│   └── chart_service.py    # 차트 데이터 생성
└── core/
    ├── database.py       # 기존
    ├── storage.py        # 기존
    └── auth.py           # 기존
```

---

## 9. 구현 우선순위

| 단계 | 기능 | 비고 |
|------|------|------|
| 1 | User 모델에 `role` 컬럼 추가 + JWT 인증 미들웨어 | 이후 모든 기능의 기반 |
| 2 | 데이터셋 업로드 (CSV 우선) | 핵심 기능 |
| 3 | 데이터셋 목록 / 미리보기 | 탐색 기능 |
| 4 | 컬럼 통계 | 데이터 품질 파악 |
| 5 | 차트 저장 / 데이터 반환 | 시각화 기반 |
| 6 | 관리자 API | 사용자·데이터셋 관리 |
| 7 | XLSX / JSON 업로드 지원 확장 | CSV 이후 추가 |
