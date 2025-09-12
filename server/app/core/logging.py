# server/core/logging.py
import logging
from app.middleware.request_id import RequestIdFilter

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        #Quan trong: them request_id vao format de hien thi trong log
        format="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
        level=level,
    )
    # Thêm filter để gắn request_id vào mỗi log record
    # getlogger tra ve mot doi tuong logger
    logging.getLogger().addFilter(RequestIdFilter())
