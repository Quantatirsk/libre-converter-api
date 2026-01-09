"""Multi-format document conversion service using LibreOffice."""
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


class Config:
    """Application configuration from environment variables."""

    AUTH_ENABLED: bool = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
    AUTH_TOKEN: str = os.getenv("API_AUTH_TOKEN", "")
    PORT: int = int(os.getenv("API_PORT", "28001"))
    TIMEOUT: int = int(os.getenv("API_TIMEOUT", "300"))
    MAX_FILE_SIZE: int = int(os.getenv("API_MAX_FILE_SIZE", "524288000"))  # 500MB
    MAX_CONCURRENT: int = int(os.getenv("API_MAX_CONCURRENT", "10"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json").lower()


config = Config()

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    """Configure application logging."""
    logger = logging.getLogger("libre-convert")
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if config.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(handler)
    return logger


logger = setup_logging()


def log_event(event: str, **kwargs):
    """Log structured event."""
    record = logging.LogRecord(
        name="libre-convert",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=event,
        args=(),
        exc_info=None,
    )
    record.extra = {"event": event, **kwargs}
    logger.handle(record)


# -----------------------------------------------------------------------------
# Concurrency Control
# -----------------------------------------------------------------------------

conversion_semaphore: Optional[asyncio.Semaphore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global conversion_semaphore
    conversion_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT)
    log_event(
        "startup",
        auth_enabled=config.AUTH_ENABLED,
        max_concurrent=config.MAX_CONCURRENT,
        max_file_size=config.MAX_FILE_SIZE,
        timeout=config.TIMEOUT,
    )
    yield
    log_event("shutdown")


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Document Converter",
    description="Convert documents using LibreOffice",
    lifespan=lifespan,
)

# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


async def verify_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> None:
    """Verify Bearer token if authentication is enabled."""
    if not config.AUTH_ENABLED:
        return

    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if credentials.credentials != config.AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


# -----------------------------------------------------------------------------
# Format Definitions
# -----------------------------------------------------------------------------

CONVERSIONS = {
    # Document formats
    "doc": {
        "docx": ("MS Word 2007 XML", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "pdf": ("writer_pdf_Export", "application/pdf"),
        "odt": ("writer8", "application/vnd.oasis.opendocument.text"),
        "txt": ("Text", "text/plain"),
        "rtf": ("Rich Text Format", "application/rtf"),
        "html": ("HTML (StarWriter)", "text/html"),
    },
    "docx": {
        "doc": ("MS Word 97", "application/msword"),
        "pdf": ("writer_pdf_Export", "application/pdf"),
        "odt": ("writer8", "application/vnd.oasis.opendocument.text"),
        "txt": ("Text", "text/plain"),
        "rtf": ("Rich Text Format", "application/rtf"),
        "html": ("HTML (StarWriter)", "text/html"),
    },
    "odt": {
        "doc": ("MS Word 97", "application/msword"),
        "docx": ("MS Word 2007 XML", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "pdf": ("writer_pdf_Export", "application/pdf"),
        "txt": ("Text", "text/plain"),
        "rtf": ("Rich Text Format", "application/rtf"),
        "html": ("HTML (StarWriter)", "text/html"),
    },
    "rtf": {
        "doc": ("MS Word 97", "application/msword"),
        "docx": ("MS Word 2007 XML", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "pdf": ("writer_pdf_Export", "application/pdf"),
        "odt": ("writer8", "application/vnd.oasis.opendocument.text"),
    },
    # Spreadsheet formats
    "xls": {
        "xlsx": ("Calc MS Excel 2007 XML", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "pdf": ("calc_pdf_Export", "application/pdf"),
        "ods": ("calc8", "application/vnd.oasis.opendocument.spreadsheet"),
        "csv": ("Text - txt - csv (StarCalc):44,34,76", "text/csv"),
    },
    "xlsx": {
        "xls": ("MS Excel 97", "application/vnd.ms-excel"),
        "pdf": ("calc_pdf_Export", "application/pdf"),
        "ods": ("calc8", "application/vnd.oasis.opendocument.spreadsheet"),
        "csv": ("Text - txt - csv (StarCalc):44,34,76", "text/csv"),
    },
    "ods": {
        "xls": ("MS Excel 97", "application/vnd.ms-excel"),
        "xlsx": ("Calc MS Excel 2007 XML", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "pdf": ("calc_pdf_Export", "application/pdf"),
        "csv": ("Text - txt - csv (StarCalc):44,34,76", "text/csv"),
    },
    "csv": {
        "xls": ("MS Excel 97", "application/vnd.ms-excel"),
        "xlsx": ("Calc MS Excel 2007 XML", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "ods": ("calc8", "application/vnd.oasis.opendocument.spreadsheet"),
    },
    # Presentation formats
    "ppt": {
        "pptx": ("Impress MS PowerPoint 2007 XML", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "pdf": ("impress_pdf_Export", "application/pdf"),
        "odp": ("impress8", "application/vnd.oasis.opendocument.presentation"),
    },
    "pptx": {
        "ppt": ("MS PowerPoint 97", "application/vnd.ms-powerpoint"),
        "pdf": ("impress_pdf_Export", "application/pdf"),
        "odp": ("impress8", "application/vnd.oasis.opendocument.presentation"),
    },
    "odp": {
        "ppt": ("MS PowerPoint 97", "application/vnd.ms-powerpoint"),
        "pptx": ("Impress MS PowerPoint 2007 XML", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "pdf": ("impress_pdf_Export", "application/pdf"),
    },
}


def get_input_ext(filename: str) -> str:
    """Extract and validate input extension."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in CONVERSIONS:
        supported = ", ".join(sorted(CONVERSIONS.keys()))
        raise HTTPException(400, f"Unsupported input format: .{ext}. Supported: {supported}")
    return ext


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@app.post("/convert")
async def convert(
    request: Request,
    file: UploadFile,
    to: str = Query(..., description="Target format (e.g., pdf, docx, xlsx)"),
    _: None = Depends(verify_auth),
):
    """Convert document to specified format."""
    start_time = time.time()
    client_ip = get_client_ip(request)

    if not file.filename:
        raise HTTPException(400, "Filename required")

    input_ext = get_input_ext(file.filename)
    output_ext = to.lower().lstrip(".")

    if output_ext not in CONVERSIONS.get(input_ext, {}):
        available = ", ".join(sorted(CONVERSIONS[input_ext].keys()))
        raise HTTPException(400, f"Cannot convert .{input_ext} to .{output_ext}. Available: {available}")

    # Read file content and check size
    file_content = await file.read()
    input_size = len(file_content)

    if input_size > config.MAX_FILE_SIZE:
        raise HTTPException(
            413,
            f"File too large: {input_size} bytes. Max: {config.MAX_FILE_SIZE} bytes",
        )

    filter_name, mime_type = CONVERSIONS[input_ext][output_ext]

    # Acquire semaphore for concurrency control
    if not conversion_semaphore.locked() or conversion_semaphore._value > 0:
        pass  # Can proceed
    else:
        raise HTTPException(429, "Too many concurrent requests. Please retry later.")

    async with conversion_semaphore:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / file.filename
            with open(input_path, "wb") as f:
                f.write(file_content)

            # Build convert command
            convert_to_arg = f"{output_ext}:{filter_name}" if filter_name else output_ext

            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ["libreoffice", "--headless", "--convert-to", convert_to_arg, "--outdir", tmpdir, str(input_path)],
                        capture_output=True,
                        timeout=config.TIMEOUT,
                    ),
                )
            except subprocess.TimeoutExpired:
                log_event(
                    "conversion_timeout",
                    input_format=input_ext,
                    output_format=output_ext,
                    input_size_bytes=input_size,
                    client_ip=client_ip,
                )
                raise HTTPException(504, "Conversion timed out")

            if result.returncode != 0:
                log_event(
                    "conversion_error",
                    input_format=input_ext,
                    output_format=output_ext,
                    error=result.stderr.decode()[:500],
                    client_ip=client_ip,
                )
                raise HTTPException(500, f"Conversion failed: {result.stderr.decode()}")

            # Find output file
            output_files = list(Path(tmpdir).glob(f"*.{output_ext}"))
            if not output_files:
                raise HTTPException(500, "Conversion produced no output")

            with open(output_files[0], "rb") as f:
                content = f.read()

    output_size = len(content)
    duration_ms = int((time.time() - start_time) * 1000)

    log_event(
        "conversion_complete",
        input_format=input_ext,
        output_format=output_ext,
        input_size_bytes=input_size,
        output_size_bytes=output_size,
        duration_ms=duration_ms,
        client_ip=client_ip,
    )

    output_filename = Path(file.filename).stem + f".{output_ext}"
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
    )


@app.get("/formats")
async def list_formats(_: None = Depends(verify_auth)):
    """List all supported format conversions."""
    return {input_fmt: list(outputs.keys()) for input_fmt, outputs in CONVERSIONS.items()}


@app.get("/health")
async def health():
    """Health check endpoint (no auth required)."""
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
