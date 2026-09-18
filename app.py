"""FastAPI 后端入口：学历校验优先 → 拼接课程 → AI 生成 → 导出 Excel。"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import EXCEL_FILENAME, REJECT_MESSAGE
from excel_writer import write_plan
from generator import generate_plan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(EXPORTS_DIR, exist_ok=True)

app = FastAPI(title="AI 全栈开发学习计划生成器")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/generate")
async def api_generate(request: Request):
    try:
        form = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "请求体格式错误"}, status_code=400)

    if not isinstance(form, dict):
        return JSONResponse({"status": "error", "message": "请求体格式错误"}, status_code=400)

    education = (form.get("education") or "").strip()

    # 第一优先级：学历校验，不调用大模型，直接返回固定文案并终止后续流程
    if education == "其他":
        return JSONResponse({"status": "rejected", "message": REJECT_MESSAGE})

    # 正常流程：拼接固定课程 + 调用大模型生成个性化计划
    plan, source = generate_plan(form)

    # 导出固定文件名 Excel
    path = os.path.join(EXPORTS_DIR, EXCEL_FILENAME)
    write_plan(form, plan, path)

    return JSONResponse(
        {
            "status": "success",
            "source": source,
            "plan": plan,
            "download_url": "/api/download",
            "filename": EXCEL_FILENAME,
        }
    )


@app.get("/api/download")
def api_download():
    path = os.path.join(EXPORTS_DIR, EXCEL_FILENAME)
    if not os.path.exists(path):
        return JSONResponse({"status": "error", "message": "文件不存在"}, status_code=404)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=EXCEL_FILENAME,
    )
