import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi import Request
from app.core.security import require_api_key
from app.schemas.completion import CompleteRequest, CompleteResponse, DEFAULT_STOPS_PY
from app.services.ollama import build_prompt, call_generate, new_request_id
from app.core.config import settings
router = APIRouter(prefix="", tags=["completion"])
logger = logging.getLogger("completion")
@router.post("/complete", response_model=CompleteResponse, dependencies=[Depends(require_api_key)])
def complete(req: CompleteRequest):
    req_id = new_request_id()
    prompt = build_prompt(req)
    stops = (req.stop or []) + DEFAULT_STOPS_PY
    try:
        r = call_generate(prompt, req.max_tokens, req.temperature, stops, stream=False)
        data = r.json()
        return {"request_id": req_id, "completion": data.get("response", "")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}")

@router.post("/complete_stream", dependencies=[Depends(require_api_key)])
def complete_stream(req: CompleteRequest, request: Request):
    req_id = new_request_id()
    prompt = build_prompt(req.prefix, req.suffix, req.language)
    stops = (req.stop or []) + DEFAULT_STOPS
    upstream = call_generate(prompt, req.max_tokens, req.temperature, stops, stream=True)

    def gen():
        yield f"event: meta\ndata: {json.dumps({'request_id': req_id})}\n\n"
        for line in upstream.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
                chunk = obj.get("response", "")
            except Exception:
                chunk = line
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
        yield "event: done\ndata: {}\n\n"
    rid = getattr(request.state, settings.REQUEST_ID, "-")
    logger.info("Received /complete", extra={ settings.REQUEST_ID: rid})
    return StreamingResponse(gen(), media_type="text/event-stream")
