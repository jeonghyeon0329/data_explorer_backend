""" FastAPI 앱 실행 (operating the application) """
from main import create_app
from settings import settings

""" library 선언부 """
import multiprocessing
import subprocess
import sys
import os


def run_uvicorn(host: str, port: int, reload: bool = False, log_level: str = "info", workers: int = 1):
    """Uvicorn 실행 명령어 래퍼"""
    cmd = [
        sys.executable, "-m", "uvicorn", "operate:app",
        "--host", host, "--port", str(port),
        "--log-level", log_level
    ]
    if reload:
        cmd.append("--reload")
    elif workers > 1:
        cmd.extend(["--workers", str(workers)])
    subprocess.run(cmd)


def run_gunicorn(host: str, port: int, workers: int, log_level: str = "warning"):
    """Gunicorn + UvicornWorker 실행 명령어 래퍼"""
    cmd = [
        "gunicorn", "operate:app",
        "-k", "uvicorn.workers.UvicornWorker",
        "-w", str(workers),
        "-b", f"{host}:{port}",
        "--log-level", log_level,
        "--access-logfile", "-"  # 표준출력
    ]
    subprocess.run(cmd)


def print_banner(env: str, host: str, port: int, mode: str, workers: int | None = None):
    """환경 정보 출력용 배너"""
    worker_info = f"\n Workers     : {workers}" if workers and workers > 1 else ""
    print(
        f"\n{'='*60}\n"
        f" Environment : {env}\n"
        f" Mode        : {mode}{worker_info}\n"
        f" Address     : http://{host}:{port}\n"
        f"{'='*60}\n"
    )


app = create_app()

if __name__ == "__main__":
    host = settings.host
    port = settings.port
    env = getattr(settings, "app_env", "local")

    if env == "local":
        print_banner(env, host, port, "Uvicorn (reload)")
        run_uvicorn(host, port, reload=True, log_level="debug")
    else:
        workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
        log_level = "warning"

        if os.name == "nt":
            print_banner(env, host, port, "Uvicorn (Windows)", workers)
            run_uvicorn(host, port, workers=workers, log_level=log_level)
        else:
            print_banner(env, host, port, "Gunicorn + UvicornWorker (Linux)", workers)
            run_gunicorn(host, port, workers, log_level)
