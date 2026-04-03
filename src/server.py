"""FastAPI HTTP 服务 — 包装 AI 日报 pipeline，供 OpenClaw 调用。"""

import argparse
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from src import config
from src.main import run_pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)

_run_lock = asyncio.Lock()


class RunRequest(BaseModel):
    """POST /api/run 请求体。"""

    hours: int = 48
    top_n: int | None = None
    github_pages_url: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时加载配置。"""
    config.load()
    logger.info("AI 日报 HTTP 服务就绪")
    yield


app = FastAPI(title="AI 日报 Bridge", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    """健康检查。"""
    return {"status": "ok"}


@app.post("/api/run")
async def run(body: RunRequest = RunRequest()) -> dict:
    """触发完整 pipeline，串行化执行防止并发。"""
    if _run_lock.locked():
        return {"success": False, "error": "Pipeline 正在运行中，请稍后重试"}

    async with _run_lock:
        result = await asyncio.to_thread(
            run_pipeline,
            hours=body.hours,
            top_n=body.top_n,
            github_pages_url=body.github_pages_url,
        )
    return result


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="AI 日报 HTTP Bridge")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=18791, help="监听端口（默认 18791）")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info", access_log=False)
