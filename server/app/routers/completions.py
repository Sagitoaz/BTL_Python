import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.postprocess import postprocess
from app.core.security import require_api_key
from app.schemas.completion import DEFAULT_STOPS_PY, CompleteRequest, CompleteResponse
from app.services.groq import build_prompt, call_groq_completion, new_request_id

router = APIRouter(prefix="", tags=["completion"])
logger = logging.getLogger("completion")


@router.post("/complete", response_model=CompleteResponse, dependencies=[Depends(require_api_key)])
def complete(req: CompleteRequest):
    req_id = new_request_id()
    prompt = build_prompt(req)
    stops = (req.stop or []) + DEFAULT_STOPS_PY
    try:
        raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
        completion = (
            postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
        )
        return {"request_id": req_id, "completion": completion}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}") from e


@router.post("/complete_stream", dependencies=[Depends(require_api_key)])
def complete_stream(req: CompleteRequest, request: Request):
    """
    Streaming endpoint - NOTE: Groq API returns full response, we simulate streaming.
    For true streaming, consider using Groq's streaming API in future.
    """
    req_id = new_request_id()
    prompt = build_prompt(req)
    stops = (req.stop or []) + DEFAULT_STOPS_PY
    
    def gen():
        yield f"event: meta\ndata: {json.dumps({'request_id': req_id})}\n\n"
        try:
            # Groq returns full completion (not streaming yet)
            raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
            
            # Simulate streaming by chunking
            chunk_size = 10
            for i in range(0, len(raw), chunk_size):
                chunk = raw[i:i+chunk_size]
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
            
            final = (
                postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
            )
            yield f"event: final\ndata: {json.dumps({'completion': final})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.exception("Error in streaming completion")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    rid = getattr(request.state, settings.REQUEST_ID, "-")
    logger.info("Received /complete_stream", extra={settings.REQUEST_ID: rid})
    return StreamingResponse(gen(), media_type="text/event-stream")
