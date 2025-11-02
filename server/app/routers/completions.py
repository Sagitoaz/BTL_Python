import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.postprocess import postprocess
from app.core.formatter import format_code, should_format
from app.core.security import require_api_key
from app.middleware.telemetry import get_telemetry_collector
from app.schemas.completion import DEFAULT_STOPS_PY, CompleteRequest, CompleteResponse
from app.services.groq import build_prompt, call_groq_completion, new_request_id

router = APIRouter(prefix="", tags=["completion"])
logger = logging.getLogger("completion")


@router.post("/complete", response_model=CompleteResponse, dependencies=[Depends(require_api_key)])
def complete(req: CompleteRequest):
    req_id = new_request_id()
    start_time = time.time()
    
    prompt = build_prompt(req)
    stops = (req.stop or []) + DEFAULT_STOPS_PY
    try:
        raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
        completion = (
            postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
        )
        
        # Auto-format if enabled and applicable
        if settings.AUTO_FORMAT and should_format(completion, req.language):
            formatted, error = format_code(completion, req.language)
            if error:
                logger.warning(f"Format failed: {error}, using unformatted")
            else:
                completion = formatted
        
        # Record telemetry
        latency_ms = (time.time() - start_time) * 1000
        try:
            telemetry = get_telemetry_collector()
            telemetry.record_completion(
                request_id=req_id,
                prefix=req.prefix,
                suffix=req.suffix,
                language=req.language,
                completion=completion,
                latency_ms=latency_ms,
                model=settings.GROQ_MODEL
            )
        except Exception as e:
            logger.error(f"Telemetry recording failed: {e}")
        
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
