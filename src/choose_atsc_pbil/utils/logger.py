import logging
import os
import multiprocessing as mp
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

CONSOLE_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"  # tối giản
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(processName)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: str = "logs"):
    """
    Logging đơn giản cho CLI single-process.
    Gắn trực tiếp console/file handlers vào root logger.
    """
    os.makedirs(log_dir, exist_ok=True)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT, DATE_FORMAT))

    app_file = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    app_file.setLevel(logging.DEBUG)
    app_file.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    err_file = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    err_file.setLevel(logging.WARNING)
    err_file.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(app_file)
    root.addHandler(err_file)


def setup_multiprocess_logging(log_dir: str = "logs"):
    """
    Logging dùng cho multiprocessing.
    - Tạo Queue để nhận log từ các tiến trình con
    - Tạo QueueListener gắn các handler (console/file)
    - Gắn QueueHandler vào root logger để cả main cũng đẩy log qua Queue
    """
    os.makedirs(log_dir, exist_ok=True)

    log_queue = mp.Queue(-1)

    # Handlers thực sự (chỉ gắn vào Listener)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT, DATE_FORMAT))

    app_file = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    app_file.setLevel(logging.DEBUG)
    app_file.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    err_file = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    err_file.setLevel(logging.WARNING)
    err_file.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    listener = QueueListener(
        log_queue, console, app_file, err_file, respect_handler_level=True
    )
    listener.start()

    # Root logger đẩy log vào Queue
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(QueueHandler(log_queue))

    return log_queue, listener


def worker_configurer(log_queue):
    """
    Gọi bên trong mỗi tiến trình con (hoặc ngay đầu hàm target).
    Gắn QueueHandler để đẩy log về Listener của tiến trình chính.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(QueueHandler(log_queue))
