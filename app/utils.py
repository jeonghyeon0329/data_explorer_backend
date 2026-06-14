from fastapi import HTTPException, UploadFile
from rich.console import Console
from pathlib import Path
from typing import List, Tuple, Union, Optional, Iterable
from PIL import Image
import pandas as pd
import tempfile
import itertools
import threading
import pypdfium2 as pdfium
import io, os, glob, time


# =========================================================
# 🎯 공통 헬퍼
# =========================================================
def raise_http(status: int, code: str, message: str, errors: Optional[Union[str, dict]] = None):
    """HTTPException 포맷 통일"""
    raise HTTPException(
        status_code=status,
        detail=build_api_response(status, code, message, errors=errors),
    )


def build_api_response(
    status: int,
    code: str,
    message: str,
    data: Optional[dict] = None,
    errors: Optional[Union[str, dict]] = None,
    operation_id: Optional[str] = None,
) -> dict:
    """공통 API 응답 구조를 통일합니다."""
    return {
        "status_code": status,
        "error_code": code,
        "message": message,
        "errors": errors if errors is not None else "",
        "data": data or {},
        "operation_id": operation_id or "",
    }


def make_json_response(status: int, code: str, message: str, errors: Optional[Union[str, dict]] = None) -> dict:
    """공통 JSON 응답 포맷"""
    return build_api_response(status, code, message, data={}, errors=errors)


def _safe_filename(name: str) -> str:
    """경로 주입 방지용 파일명 정규화"""
    return Path(name).name


def _normalize_extensions(exts: Union[str, Iterable[str]]) -> List[str]:
    """확장자 문자열을 표준화 ('.' 포함, lower 변환)"""
    if isinstance(exts, str):
        exts = [exts]
    out = []
    for e in exts:
        e = (e or "").strip().lower()
        if not e:
            continue
        out.append(e if e.startswith(".") else f".{e}")
    return out


# =========================================================
# 📁 FileManager
# =========================================================
class FileManager:
    UPLOAD_ROOT = Path("uploads")

    def __init__(self, user_id: str, affiliation: str):
        self.user_id = user_id
        self.affiliation = affiliation
        self.base_dir = f"{self.affiliation}_{self.user_id}" if user_id and affiliation else None
        self.subdirs = ["dataset", "dataset_tmp", "result"]
        self.filename = None
        self.full_path = None
        self.file_info = None

        self.base_path = None
        self.dataset_dir = None
        self.dataset_tmp = None
        self.result_dir = None

    def _init_user_folder(self) -> Path:
        """유저별 디렉토리 생성"""
        base_path = self.UPLOAD_ROOT / self.base_dir
        base_path.mkdir(parents=True, exist_ok=True)
        for sub in self.subdirs:
            (base_path / sub).mkdir(exist_ok=True)
        return base_path

    async def save_file_to_dataset(self, file, chunk_size: int = 1024 * 1024) -> None:
        """파일 시스템 없이 파일 메타데이터를 유지합니다."""
        if not file:
            raise_http(422, "C001", "File required")

        if isinstance(file, UploadFile):
            safe_name = _safe_filename(file.filename)
            self.filename = Path(safe_name).stem
            self.full_path = None
            self.file_info = {
                "filename": safe_name,
                "content_type": getattr(file, "content_type", None),
                "source": "uploadfile",
            }
            self.raw_file = file
            return None

        if isinstance(file, dict):
            self.filename = _safe_filename(str(file.get("filename", ""))) if file.get("filename") else None
            self.full_path = None
            self.file_info = {**file, "source": "json"}
            self.raw_file = file
            return None

        raise_http(422, "C001", "Unsupported file payload")

    # ------------------------------------------------------------------
    # 정적 메서드 (파일 유효성 검사)
    # ------------------------------------------------------------------
    @staticmethod
    def require_file_count(files: List[UploadFile], expected_count: int) -> Union[UploadFile, Tuple[UploadFile, ...]]:
        """파일 개수 및 이름 유효성 검사"""
        if not isinstance(files, list):
            raise_http(422, "C002", "Files format error")

        if len(files) != expected_count:
            raise_http(422, "C003", "Files count error")

        names = [getattr(f, "filename", "") for f in files]
        if any(not n for n in names):
            raise_http(422, "C004", "Files name error")

        if len(names) != len(set(names)):
            raise_http(422, "C005", "Files duplicate error")

        return files[0] if expected_count == 1 else tuple(files)

    @staticmethod
    def validate_extensions(files: Union[UploadFile, List[UploadFile]], allowed_extensions: Union[str, List[str]]) -> None:
        """허용된 확장자 검사"""
        exts = _normalize_extensions(allowed_extensions)
        file_list = files if isinstance(files, list) else [files]

        for f in file_list:
            name = getattr(f, "filename", "") or ""
            if not name:
                raise_http(422, "C006", "File name error")
            lower = name.lower()
            if not any(lower.endswith(e) for e in exts):
                raise_http(422, "C007", f"Invalid file extension: {name}")


# =========================================================
# 📦 FileUtils
# =========================================================
class FileUtils:
    """파일 처리 관련 유틸 클래스"""

    @staticmethod
    def resultfile_delete(delete_patterns: List[Tuple[str, str]]) -> None:
        """패턴 기반 파일 삭제"""
        for dir_path, pattern in delete_patterns:
            for file_path in glob.glob(os.path.join(dir_path, pattern)):
                if os.path.exists(file_path):
                    os.remove(file_path)

    @staticmethod
    def convert_images_to_pdf(files):
        """이미지(jpg, png)를 PDF로 변환"""
        try:
            is_single = not isinstance(files, list)
            files = [files] if is_single else files

            converted = []
            for f in files:
                name = f.filename.lower()
                if name.endswith((".jpg", ".jpeg", ".png")):
                    image = Image.open(f.file).convert("RGB")
                    pdf_stream = io.BytesIO()
                    image.save(pdf_stream, format="PDF")
                    pdf_stream.seek(0)

                    temp = tempfile.SpooledTemporaryFile()
                    temp.write(pdf_stream.read())
                    temp.seek(0)

                    pdf_file = UploadFile(filename=name.rsplit(".", 1)[0] + ".pdf", file=temp)
                    converted.append(pdf_file)
                else:
                    converted.append(f)

            return converted[0] if is_single else converted
        except Exception as e:
            raise_http(500, "F004", "Failed to convert images to PDF", str(e))

    @staticmethod
    def pdf_info(pdf_path: str):
        """PDF 파일을 읽고 페이지 수/이미지 목록을 반환
        - 실패 시 error 상태와 메시지를 return"""
        import pypdfium2 as pdfium
        try:
            pdf = pdfium.PdfDocument(pdf_path)
            images = [page.render(scale=100 / 72).to_pil() for page in pdf]
            return {
                "status": "success",
                "page_count": len(images),
                "images": images
            }
        except Exception as e:
            error_message = str(e)
            # PDFium 암호화 에러인 경우 좀 더 친절히 안내
            if "Incorrect password" in error_message:
                error_message = "PDF is password-protected (cannot be opened)."
            elif "file not found" in error_message.lower():
                error_message = "File not found or inaccessible."
            elif "unsupported" in error_message.lower():
                error_message = "Unsupported PDF format."
            
            return {
                "status": "error",
                "page_count": 0,
                "images": [],
                "error_message": error_message
            }


# =========================================================
# 💬 PrintUtils
# =========================================================
class PrintUtils:
    """터미널 스피너 & 출력 도우미"""
    def __init__(self):
        self.console = Console()

    def show_spinner(self, message: str = "작업중", interval: float = 0.1):
        console = self.console

        class SpinnerCtx:
            def __enter__(self):
                self._spinner = itertools.cycle(["-", "\\", "|", "/"])
                self._running = True
                self._thread = threading.Thread(target=self._spin_loop, daemon=True)
                self._thread.start()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self._running = False
                self._thread.join()
                if exc_type is None:
                    console.log(f"{message} [bold green]완료 ✅[/]")
                else:
                    console.log(f"{message} [bold red]실패 ❌[/]")

            def _spin_loop(self):
                while self._running:
                    console.print(f"{message} {next(self._spinner)}", end="\r", style="cyan")
                    time.sleep(interval)

        return SpinnerCtx()
