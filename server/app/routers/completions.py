import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional

from app.core.config import settings
from app.core.postprocess import postprocess
from app.core.formatter import format_code, should_format, normalize_python_code, normalize_cpp_code
from app.core.security import require_api_key
from app.middleware.telemetry import get_telemetry_collector
from app.schemas.completion import DEFAULT_STOPS_PY, DEFAULT_STOPS_CPP, CompleteRequest, CompleteResponse
from app.services.groq import build_prompt, call_groq_completion, new_request_id
from app.services.user_profiling import get_profiler

router = APIRouter(prefix="", tags=["completion"])
logger = logging.getLogger("completion")


@router.post("/complete", response_model=CompleteResponse, dependencies=[Depends(require_api_key)])
def complete(
    req: CompleteRequest,
    x_user_id: Optional[str] = Header(None, description="User identifier for personalization")
):
    req_id = new_request_id()
    start_time = time.time()
    
    # Get personalized style hints if user_id provided
    user_style_hints = ""
    if x_user_id:
        try:
            profiler = get_profiler()
            user_style_hints = profiler.get_style_hints(x_user_id)
        except Exception as e:
            logger.warning(f"Failed to get style hints: {e}")
    
    prompt = build_prompt(req, user_style_hints)
    
    # Choose appropriate stop sequences based on language
    default_stops = DEFAULT_STOPS_CPP if req.language in ["cpp", "c++", "c"] else DEFAULT_STOPS_PY
    stops = (req.stop or []) + default_stops
    
    try:
        raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
        completion = (
            postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
        )
        
        # Auto-format if enabled and applicable
        if settings.AUTO_FORMAT and should_format(completion, req.language):
            formatted, error = format_code(completion, req.language)
            if error:
                logger.warning(f"Format failed: {error}, using normalization fallback")
                if req.language == "python":
                    completion = normalize_python_code(completion)
                elif req.language in ["cpp", "c++", "c"]:
                    completion = normalize_cpp_code(completion)
            else:
                completion = formatted
        else:
            # If auto-format is disabled, still apply lightweight normalization
            if req.language == "python":
                completion = normalize_python_code(completion)
            elif req.language in ["cpp", "c++", "c"]:
                completion = normalize_cpp_code(completion)
        
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
                model=settings.GROQ_MODEL,
                user_id=x_user_id  # Include user_id in telemetry
            )
        except Exception as e:
            logger.error(f"Telemetry recording failed: {e}")
        
        return {"request_id": req_id, "completion": completion}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}") from e


@router.post("/complete_stream", dependencies=[Depends(require_api_key)])
def complete_stream(
    req: CompleteRequest,
    request: Request,
    x_user_id: Optional[str] = Header(None, description="User identifier for personalization")
):
    """
    Streaming endpoint - NOTE: Groq API returns full response, we simulate streaming.
    For true streaming, consider using Groq's streaming API in future.
    """
    req_id = new_request_id()
    
    # Get personalized style hints if user_id provided
    user_style_hints = ""
    if x_user_id:
        try:
            profiler = get_profiler()
            user_style_hints = profiler.get_style_hints(x_user_id)
        except Exception as e:
            logger.warning(f"Failed to get style hints: {e}")
    
    prompt = build_prompt(req, user_style_hints)
    
    # Choose appropriate stop sequences based on language
    default_stops = DEFAULT_STOPS_CPP if req.language in ["cpp", "c++", "c"] else DEFAULT_STOPS_PY
    stops = (req.stop or []) + default_stops
    
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

            # Apply same formatting/normalization logic as non-streaming endpoint
            if settings.AUTO_FORMAT and should_format(final, req.language):
                formatted, error = format_code(final, req.language)
                if error:
                    logger.warning(f"Format failed in stream: {error}, using normalization fallback")
                    if req.language == "python":
                        final = normalize_python_code(final)
                    elif req.language in ["cpp", "c++", "c"]:
                        final = normalize_cpp_code(final)
                else:
                    final = formatted
            else:
                if req.language == "python":
                    final = normalize_python_code(final)
                elif req.language in ["cpp", "c++", "c"]:
                    final = normalize_cpp_code(final)

            yield f"event: final\ndata: {json.dumps({'completion': final})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.exception("Error in streaming completion")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    rid = getattr(request.state, settings.REQUEST_ID, "-")
    logger.info("Received /complete_stream", extra={settings.REQUEST_ID: rid})
    return StreamingResponse(gen(), media_type="text/event-stream")
