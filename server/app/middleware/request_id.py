
import uuid
import logging
from fastapi import Request, Response

# Filter để thêm field request_id vào log record
# log la ghi chep cac su kien xay ra trong qua trinh chay ung dung
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        #Neu khong co request_id thi them vao
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True

# Middleware nhu mot bo loc trung gian giua request va response
# Middleware chính
# Ham async de xu ly bat dong bo ( nhieu ham async trong ung dung)
async def request_id_middleware(request: Request, call_next):
    # Lấy từ header nếu có, không thì tạo mới
    # uuid la mot chuoi ky tu duy nhat
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    # gan request_id vao request.state de su dung sau nay
    request.state.request_id = rid

    
    try:
        # Goi ham call_next de tiep tuc xu ly request(xu li nhieu request cung luc)
        response: Response = await call_next(request)
    except Exception:
       
        raise
    finally:
        # Nếu đã có response object, thêm header (nếu chưa gửi)
        try:
            # Them request_id vao header cua response
            if "response" in locals():
                response.headers["X-Request-ID"] = rid
        except Exception:
            # Nếu không thể gắn (vd: header đã gửi), bỏ qua.
            pass
    return response

   
