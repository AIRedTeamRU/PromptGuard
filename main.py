# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.guard import detect_jailbreak
import uvicorn

app = FastAPI(
    title="PromptGuard API",
    description="🛡️ Простой фаервол для защиты LLM от вредоносных промптов",
    version="0.1.0"
)

class PromptRequest(BaseModel):
    prompt: str

class GuardResponse(BaseModel):
    is_safe: bool
    risk_score: float
    flags: list[str]
    suggested_rewrite: str

@app.post("/v1/guard-prompt", response_model=GuardResponse)
async def guard_prompt(request: PromptRequest):
    """
    Анализирует промпт на наличие jailbreak, вредоносных инструкций или запрещённых тем.
    Возвращает флаг безопасности и рекомендацию.
    """
    result = detect_jailbreak(request.prompt)
    
    return GuardResponse(
        is_safe=not result["flagged"],
        risk_score=result["risk_score"],
        flags=[result["reason"]] if result["flagged"] else [],
        suggested_rewrite=result["suggested_rewrite"]
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to PromptGuard API — your LLM firewall 🔐"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)