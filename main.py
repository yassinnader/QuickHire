import asyncio
import hashlib
import io
import json
import logging
import os
import re
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, EmailStr, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from celery import Celery
from prometheus_fastapi_instrumentator import Instrumentator
import aiohttp
from config import settings

# Logging Configuration with Correlation IDs
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - Correlation-ID: %(correlation_id)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": settings.log_level,
        "handlers": ["console"]
    }
})
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def get_correlation_id(request: Request = None):
    return request.headers.get('X-Correlation-ID', str(uuid.uuid4())) if request else str(uuid.uuid4())

# Celery Configuration
try:
    celery = Celery('quickhire', broker=settings.redis_url, backend=settings.redis_url)
except Exception as e:
    logger.error(f"Failed to initialize Celery: {str(e)}")
    raise

# Mock Services (Replace with real implementations in production)
class AIService:
    async def initialize(self): pass
    async def cleanup(self): pass
    async def health_check(self): return {"status": "healthy"}
    async def warmup(self): pass
    async def generate_resume(self, data): return "Generated Resume Content"
    async def generate_cover_letter(self, data): return "Generated Cover Letter Content"

class PDFGenerator:
    def initialize(self): pass
    def health_check(self): return {"status": "healthy"}
    async def generate_pdf_async(self, content, template_type, style): return b"%PDF-1.4\n%Generated PDF"

class DatabaseService:
    async def initialize(self): pass
    async def close(self): pass
    async def health_check(self): return {"status": "healthy"}
    async def count_active_requests(self, user_id): return 0
    async def get_user_preferences(self, user_id): return {}
    async def store_generation_request(self, **kwargs): pass
    async def update_request_status(self, request_id, status, error_message=None): pass
    async def store_generated_file(self, **kwargs): return f"http://fake-url.com/{kwargs['filename']}"
    async def get_generation_request(self, request_id): return {"user_id": "test", "status": "completed", "request_type": "resume", "created_at": "", "updated_at": "", "batch_id": None}
    async def get_generated_file(self, request_id): return b"%PDF-1.4\n%Generated PDF"
    async def increment_download_count(self, request_id): pass
    async def get_user_generation_history(self, **kwargs): return []
    async def count_user_generations(self, **kwargs): return 0
    async def update_user_preferences(self, user_id, prefs): return prefs
    async def count_user_api_keys(self, user_id): return 0
    async def create_api_key(self, **kwargs): pass
    async def get_user_api_keys(self, user_id): return []
    async def revoke_api_key(self, user_id, key_id): return True
    async def cleanup_old_files(self, user_id, cutoff_date): return 0
    async def get_batch_status(self, batch_id, user_id): return {"batch_id": batch_id, "status": "completed", "request_ids": []}
    async def get_user(self, user_id): return {"email": "test@example.com", "email_notifications": True, "webhook_url": None}
    async def get_user_analytics(self, user_id, days): return {"requests": 0, "success_rate": 1.0}
    async def get_available_templates(self): return [{"id": "modern", "name": "Modern Template", "preview": "Modern Preview"}]
    async def get_template_preview(self, template_id): return {"template_id": template_id, "preview": "Preview Content"}

class AuthService:
    async def verify_token(self, token): return {"user_id": "test", "email": "test@example.com"}

class CacheService:
    async def initialize(self): pass
    async def close(self): pass
    async def health_check(self): return {"status": "healthy"}
    async def get(self, key): return None
    async def set(self, key, value, ttl=300): pass
    async def delete(self, key): pass
    async def delete_pattern(self, pattern): pass

class NotificationService:
    async def send_completion_email(self, email, request_id, request_type): pass
    async def send_batch_completion_email(self, email, batch_id, total_requests): pass
    async def send_webhook_notification(self, webhook_url, data):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook_url, json=data, timeout=settings.default_webhook_timeout) as response:
                    if response.status >= 400:
                        logger.error(f"Webhook failed with status {response.status}")
            except Exception as e:
                logger.error(f"Webhook notification failed: {str(e)}")

# Service Container
class ServiceContainer:
    def __init__(self):
        self.ai_service = AIService()
        self.pdf_generator = PDFGenerator()
        self.db_service = DatabaseService()
        self.auth_service = AuthService()
        self.cache_service = CacheService()
        self.notification_service = NotificationService()

    async def initialize(self):
        try:
            await self.db_service.initialize()
            await self.ai_service.initialize()
            await self.cache_service.initialize()
            self.pdf_generator.initialize()
        except Exception as e:
            logger.error(f"Service initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Service initialization failed")

    async def cleanup(self):
        try:
            await self.db_service.close()
            await self.ai_service.cleanup()
            await self.cache_service.close()
        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")

# FastAPI Application Setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting QuickHire AI application...")
    services = ServiceContainer()
    app.state.services = services
    try:
        await services.initialize()
        await services.ai_service.warmup()
        logger.info("All services initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Lifespan error: {str(e)}")
        raise
    finally:
        await services.cleanup()
        logger.info("All services shut down successfully")

app = FastAPI(
    title="QuickHire AI",
    description="AI-powered resume and cover letter generator",
    version="2.2.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health checks and system status"},
        {"name": "generation", "description": "Document generation operations"},
        {"name": "auth", "description": "Authentication and authorization"},
        {"name": "user", "description": "User management and preferences"},
        {"name": "analytics", "description": "Usage analytics and reporting"},
        {"name": "templates", "description": "Template management"},
        {"name": "batch", "description": "Batch processing operations"}
    ]
)

# Middleware Configuration
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "WEBSOCKET"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    max_age=3600,
)

# Prometheus Metrics
try:
    Instrumentator().instrument(app).expose(app)
except Exception as e:
    logger.warning(f"Failed to initialize Prometheus: {str(e)}")

# Rate Limiter
limiter = Limiter(key_func=lambda request: request.headers.get("Authorization", "anonymous").split("Bearer ")[-1] or "anonymous")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

security = HTTPBearer()

def user_rate_limit(limit: str):
    async def get_user_id(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security), services: ServiceContainer = Depends(get_services)):
        try:
            user = await services.auth_service.verify_token(credentials.credentials)
            return user['user_id']
        except Exception:
            return "anonymous"

    def decorator(fn):
        return limiter.limit(limit, key_func=lambda request: get_user_id(request))(fn)
    return decorator

# Pydantic Models
class BasePersonalInfo(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    address: Optional[str] = Field(None, max_length=200)
    linkedin: Optional[str] = Field(None, pattern=r'^https://(?:www\.)?linkedin\.com/in/[\w\-]+/?$')
    github: Optional[str] = Field(None, pattern=r'^https://(?:www\.)?github\.com/[\w\-]+/?$')
    website: Optional[str] = Field(None, pattern=r'^https?://[\w\-\.]+\.[\w]{2,}/?.*$')

    @validator('full_name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return re.sub(r'[<>]', '', v.strip())

    @validator('phone')
    def validate_phone(cls, v):
        if v:
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 10 or len(digits_only) > 15:
                raise ValueError('Phone number must be between 10 and 15 digits')
        return v

class Experience(BaseModel):
    company: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}$')
    end_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}$|^present$')
    description: str = Field(..., min_length=10, max_length=2000)
    achievements: Optional[List[str]] = Field(default_factory=list, max_items=10)

    @validator('description')
    def sanitize_description(cls, v):
        return re.sub(r'[<>]', '', v.strip())

class Education(BaseModel):
    institution: str = Field(..., min_length=1, max_length=100)
    degree: str = Field(..., min_length=1, max_length=100)
    field_of_study: Optional[str] = Field(None, max_length=100)
    graduation_year: int = Field(..., ge=1950, le=2030)
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)

class ResumeRequest(BasePersonalInfo):
    experiences: List[Experience] = Field(default_factory=list, max_items=20)
    education: List[Education] = Field(default_factory=list, max_items=10)
    skills: List[str] = Field(..., min_items=1, max_items=50)
    summary: Optional[str] = Field(None, max_length=1000)
    job_target: Optional[str] = Field(None, max_length=200)
    template_style: str = Field(default="modern", pattern=r'^(modern|classic|creative|minimal)$')

    @validator('skills')
    def validate_skills(cls, v):
        cleaned_skills = []
        seen = set()
        for skill in v:
            clean_skill = re.sub(r'[<>]', '', skill.strip())
            if clean_skill and clean_skill.lower() not in seen:
                cleaned_skills.append(clean_skill)
                seen.add(clean_skill.lower())
        if not cleaned_skills:
            raise ValueError('At least one skill is required')
        return cleaned_skills[:50]

class CoverLetterRequest(BasePersonalInfo):
    company_name: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    job_description: Optional[str] = Field(None, max_length=5000)
    hiring_manager: Optional[str] = Field(None, max_length=100)
    key_experiences: List[str] = Field(..., min_items=1, max_items=10)
    tone: str = Field(default="professional", pattern=r'^(professional|friendly|enthusiastic|formal)$')

    @validator('company_name', 'position', 'hiring_manager')
    def sanitize_strings(cls, v):
        return re.sub(r'[<>]', '', v.strip()) if v else v

class GenerationResponse(BaseModel):
    request_id: str
    status: str
    message: str
    download_url: Optional[str] = None
    estimated_completion: Optional[str] = None

class APIKeyResponse(BaseModel):
    api_key: str
    key_id: str
    created_at: str
    expires_at: Optional[str] = None
    usage_limit: Optional[int] = None

class UserPreferences(BaseModel):
    default_template_style: str = Field(default="modern", pattern=r'^(modern|classic|creative|minimal)$')
    default_tone: str = Field(default="professional", pattern=r'^(professional|friendly|enthusiastic|formal)$')
    auto_save_drafts: bool = True
    email_notifications: bool = True
    webhook_url: Optional[str] = Field(None, pattern=r'^https?://[\w\-\.]+\.[\w]{2,}/?.*$')
    max_concurrent_requests: int = Field(default=3, ge=1, le=10)

class BatchRequest(BaseModel):
    requests: List[Union[ResumeRequest, CoverLetterRequest]] = Field(..., max_items=10)
    priority: str = Field(default="normal", pattern=r'^(low|normal|high)$')

class TemplateResponse(BaseModel):
    id: str
    name: str
    preview: str

# Dependencies
async def get_services():
    return app.state.services

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        cache_key = f"user_token:{hashlib.sha256(credentials.credentials.encode()).hexdigest()}"
        cached_user = await services.cache_service.get(cache_key)
        if cached_user:
            logger.info(f"User retrieved from cache - Correlation-ID: {correlation_id}")
            return json.loads(cached_user)

        user = await services.auth_service.verify_token(credentials.credentials)
        await services.cache_service.set(cache_key, json.dumps(user), ttl=300)
        logger.info(f"User authenticated - User: {user.get('user_id')} - Correlation-ID: {correlation_id}")
        return user
    except Exception as e:
        logger.error(f"Authentication failed - Error: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Background Tasks
async def cleanup_old_files(user_id: str, services: ServiceContainer):
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        deleted_count = await services.db_service.cleanup_old_files(user_id, cutoff_date)
        logger.info(f"Cleaned up {deleted_count} old files for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to cleanup old files for user {user_id}: {str(e)}")

async def send_completion_notification(user: dict, request_id: str, request_type: str, services: ServiceContainer):
    try:
        user_data = await services.db_service.get_user(user['user_id'])
        if user_data.get('email_notifications', True):
            await services.notification_service.send_completion_email(
                user_data['email'], request_id, request_type
            )
        if user_data.get('webhook_url'):
            await services.notification_service.send_webhook_notification(
                user_data['webhook_url'],
                {"request_id": request_id, "request_type": request_type, "status": "completed"}
            )
        logger.info(f"Sent notifications for {request_type} {request_id}")
    except Exception as e:
        logger.error(f"Failed to send notification for {request_type} {request_id}: {str(e)}")

# Routes
@app.get("/health", tags=["health"])
async def health_check(services: ServiceContainer = Depends(get_services)):
    try:
        start_time = datetime.utcnow()
        health_checks = await asyncio.gather(
            services.ai_service.health_check(),
            services.db_service.health_check(),
            services.cache_service.health_check(),
            return_exceptions=True
        )
        ai_health, db_health, cache_health = health_checks
        pdf_health = services.pdf_generator.health_check()
        response_time = (datetime.utcnow() - start_time).total_seconds()

        status = "healthy" if all([
            isinstance(ai_health, dict) and ai_health.get('status') == 'healthy',
            isinstance(db_health, dict) and db_health.get('status') == 'healthy',
            isinstance(cache_health, dict) and cache_health.get('status') == 'healthy',
            pdf_health.get('status') == 'healthy'
        ]) else "degraded"

        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_seconds": response_time,
            "services": {
                "ai_service": ai_health if not isinstance(ai_health, Exception) else {"status": "error", "error": str(ai_health)},
                "pdf_generator": pdf_health,
                "database": db_health if not isinstance(db_health, Exception) else {"status": "error", "error": str(db_health)},
                "cache": cache_health if not isinstance(cache_health, Exception) else {"status": "error", "error": str(cache_health)}
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

async def generate_document(
    request_data: dict,
    request_type: str,
    template_style: str,
    services: ServiceContainer,
    user_id: str,
    request_id: str,
    ip_address: str,
    user_agent: str
):
    try:
        await services.db_service.store_generation_request(
            user_id=user_id,
            request_id=request_id,
            request_type=request_type,
            request_data={**request_data, "user_id": user_id, "ip_address": ip_address, "user_agent": user_agent},
            status="processing"
        )

        content = await asyncio.wait_for(
            services.ai_service.generate_resume(request_data) if request_type == "resume"
            else services.ai_service.generate_cover_letter(request_data),
            timeout=120.0
        )
        if not content:
            raise HTTPException(status_code=500, detail=f"Failed to generate {request_type} content")

        pdf_content = await services.pdf_generator.generate_pdf_async(
            content=content,
            template_type=request_type,
            style=template_style
        )

        file_url = await services.db_service.store_generated_file(
            request_id=request_id,
            file_type="pdf",
            file_content=pdf_content,
            filename=f"{request_type}_{request_id}.pdf"
        )

        await services.db_service.update_request_status(request_id, "completed")
        await services.cache_service.set(f"generated_file:{request_id}", file_url, ttl=3600)
        return file_url
    except asyncio.TimeoutError:
        await services.db_service.update_request_status(request_id, "failed", "AI service timeout")
        raise HTTPException(status_code=408, detail="AI service timeout")
    except Exception as e:
        await services.db_service.update_request_status(request_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"{request_type.capitalize()} generation failed")

@app.post("/api/v1/generate-resume", response_model=GenerationResponse, tags=["generation"])
@user_rate_limit("10/minute")
async def generate_resume(
    request: Request,
    resume_request: ResumeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services)
):
    correlation_id = get_correlation_id(request)
    request_id = str(uuid.uuid4())
    logger.info(f"Resume generation started - User: {current_user['user_id']} - Request: {request_id} - Correlation-ID: {correlation_id}")

    active_requests = await services.db_service.count_active_requests(current_user['user_id'])
    user_prefs = await services.db_service.get_user_preferences(current_user['user_id'])
    max_concurrent = user_prefs.get('max_concurrent_requests', settings.max_concurrent_requests)

    if active_requests >= max_concurrent:
        raise HTTPException(status_code=429, detail=f"Maximum concurrent requests ({max_concurrent}) exceeded")

    file_url = await generate_document(
        resume_request.dict(),
        "resume",
        resume_request.template_style,
        services,
        current_user['user_id'],
        request_id,
        request.client.host,
        request.headers.get('user-agent', '')
    )

    background_tasks.add_task(cleanup_old_files, current_user['user_id'], services)
    background_tasks.add_task(send_completion_notification, current_user, request_id, "resume", services)

    return GenerationResponse(
        request_id=request_id,
        status="completed",
        message="Resume generated successfully",
        download_url=file_url
    )

@app.post("/api/v1/generate-cover-letter", response_model=GenerationResponse, tags=["generation"])
@user_rate_limit("10/minute")
async def generate_cover_letter(
    request: Request,
    cover_letter_request: CoverLetterRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services)
):
    correlation_id = get_correlation_id(request)
    request_id = str(uuid.uuid4())
    logger.info(f"Cover letter generation started - User: {current_user['user_id']} - Request: {request_id} - Correlation-ID: {correlation_id}")

    active_requests = await services.db_service.count_active_requests(current_user['user_id'])
    user_prefs = await services.db_service.get_user_preferences(current_user['user_id'])
    max_concurrent = user_prefs.get('max_concurrent_requests', settings.max_concurrent_requests)

    if active_requests >= max_concurrent:
        raise HTTPException(status_code=429, detail=f"Maximum concurrent requests ({max_concurrent}) exceeded")

    file_url = await generate_document(
        cover_letter_request.dict(),
        "cover_letter",
        cover_letter_request.tone,
        services,
        current_user['user_id'],
        request_id,
        request.client.host,
        request.headers.get('user-agent', '')
    )

    background_tasks.add_task(cleanup_old_files, current_user['user_id'], services)
    background_tasks.add_task(send_completion_notification, current_user, request_id, "cover_letter", services)

    return GenerationResponse(
        request_id=request_id,
        status="completed",
        message="Cover letter generated successfully",
        download_url=file_url
    )

@app.get("/api/v1/download/{request_id}", tags=["generation"])
@user_rate_limit("30/minute")
async def download_file(
    request: Request,
    request_id: str,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services)
):
    correlation_id = get_correlation_id(request)
    try:
        try:
            uuid.UUID(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request ID format")

        request_data = await services.db_service.get_generation_request(request_id)
        if not request_data or request_data['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=404, detail="File not found or access denied")

        if request_data['status'] != 'completed':
            raise HTTPException(status_code=202, detail=f"File is still being processed (status: {request_data['status']})")

        file_content = await services.db_service.get_generated_file(request_id)
        if not file_content:
            raise HTTPException(status_code=404, detail="File content not found")

        await services.db_service.increment_download_count(request_id)
        file_type = request_data['request_type']
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{file_type}_{timestamp}.pdf"

        logger.info(f"File downloaded - Request: {request_id} - User: {current_user['user_id']} - Correlation-ID: {correlation_id}")

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "private, max-age=3600",
                "X-Content-Type-Options": "nosniff"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed - Request: {request_id} - Error: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="File download failed")

@app.get("/api/v1/history", tags=["user"])
@user_rate_limit("20/minute")
async def get_generation_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    limit: int = Field(20, ge=1, le=100),
    offset: int = Field(0, ge=0),
    request_type: Optional[str] = Field(None, pattern=r'^(resume|cover_letter)$'),
    status: Optional[str] = Field(None, pattern=r'^(processing|completed|failed)$')
):
    correlation_id = get_correlation_id(request)
    try:
        cache_key = f"history:{current_user['user_id']}:{limit}:{offset}:{request_type}:{status}"
        cached_history = await services.cache_service.get(cache_key)
        if cached_history:
            logger.info(f"History retrieved from cache - User: {current_user['user_id']} - Correlation-ID: {correlation_id}")
            return json.loads(cached_history)

        history = await services.db_service.get_user_generation_history(
            user_id=current_user['user_id'],
            limit=limit,
            offset=offset,
            request_type=request_type,
            status=status
        )
        total_count = await services.db_service.count_user_generations(
            user_id=current_user['user_id'],
            request_type=request_type,
            status=status
        )

        result = {
            "history": history,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(history) < total_count
        }

        await services.cache_service.set(cache_key, json.dumps(result, default=str), ttl=300)
        logger.info(f"History retrieved - User: {current_user['user_id']} - Correlation-ID: {correlation_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to fetch history for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")

@app.get("/api/v1/status/{request_id}", tags=["generation"])
@user_rate_limit("30/minute")
async def get_request_status(
    request_id: str,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        try:
            uuid.UUID(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request ID format")

        cache_key = f"request_status:{request_id}"
        cached_status = await services.cache_service.get(cache_key)
        if cached_status:
            status_data = json.loads(cached_status)
            if status_data['user_id'] == current_user['user_id']:
                logger.info(f"Status retrieved from cache - Request: {request_id} - Correlation-ID: {correlation_id}")
                return status_data

        request_data = await services.db_service.get_generation_request(request_id)
        if not request_data or request_data['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=404, detail="Request not found or access denied")

        status_response = {
            "request_id": request_id,
            "status": request_data['status'],
            "request_type": request_data['request_type'],
            "created_at": request_data['created_at'],
            "updated_at": request_data['updated_at'],
            "progress": request_data.get('progress', 0),
            "error_message": request_data.get('error_message'),
            "user_id": request_data['user_id']
        }
        if request_data['status'] == 'completed':
            status_response['download_url'] = f"/api/v1/download/{request_id}"

        await services.cache_service.set(cache_key, json.dumps(status_response, default=str), ttl=60)
        logger.info(f"Status retrieved - Request: {request_id} - Correlation-ID: {correlation_id}")
        return status_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for request {request_id}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve request status")

@app.websocket("/api/v1/ws/status/{request_id}")
async def websocket_status(
    websocket: WebSocket,
    request_id: str,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services)
):
    await websocket.accept()
    try:
        try:
            uuid.UUID(request_id)
        except ValueError:
            await websocket.send_json({"error": "Invalid request ID format"})
            await websocket.close()
            return

        request_data = await services.db_service.get_generation_request(request_id)
        if not request_data or request_data['user_id'] != current_user['user_id']:
            await websocket.send_json({"error": "Request not found or access denied"})
            await websocket.close()
            return

        while True:
            request_data = await services.db_service.get_generation_request(request_id)
            await websocket.send_json({
                "request_id": request_id,
                "status": request_data['status'],
                "progress": request_data.get('progress', 0),
                "download_url": f"/api/v1/download/{request_id}" if request_data['status'] == 'completed' else None
            })
            if request_data['status'] in ['completed', 'failed']:
                break
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"WebSocket error for request {request_id}: {str(e)}")
        await websocket.send_json({"error": "WebSocket error"})
    finally:
        await websocket.close()

@app.get("/api/v1/user/preferences", response_model=UserPreferences, tags=["user"])
@user_rate_limit("10/minute")
async def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        preferences = await services.db_service.get_user_preferences(current_user['user_id'])
        return UserPreferences(**preferences) if preferences else UserPreferences()
    except Exception as e:
        logger.error(f"Failed to get preferences for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user preferences")

@app.put("/api/v1/user/preferences", response_model=UserPreferences, tags=["user"])
@user_rate_limit("5/minute")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        updated_preferences = await services.db_service.update_user_preferences(
            current_user['user_id'],
            preferences.dict()
        )
        await services.cache_service.delete(f"user_preferences:{current_user['user_id']}")
        logger.info(f"Updated preferences for user {current_user['user_id']} - Correlation-ID: {correlation_id}")
        return UserPreferences(**updated_preferences)
    except Exception as e:
        logger.error(f"Failed to update preferences for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to update user preferences")

@app.post("/api/v1/auth/api-keys", response_model=APIKeyResponse, tags=["auth"])
@user_rate_limit("3/hour")
async def create_api_key(
    name: str = Field(..., min_length=1, max_length=50),
    expires_in_days: Optional[int] = Field(None, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        existing_keys = await services.db_service.count_user_api_keys(current_user['user_id'])
        if existing_keys >= settings.max_api_keys:
            raise HTTPException(status_code=400, detail=f"Maximum number of API keys reached ({settings.max_api_keys})")

        api_key = f"qh_{secrets.token_urlsafe(32)}"
        key_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None

        await services.db_service.create_api_key(
            user_id=current_user['user_id'],
            key_id=key_id,
            api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
            name=name,
            expires_at=expires_at
        )
        logger.info(f"Created API key {key_id} for user {current_user['user_id']} - Correlation-ID: {correlation_id}")

        return APIKeyResponse(
            api_key=api_key,
            key_id=key_id,
            created_at=datetime.utcnow().isoformat(),
            expires_at=expires_at.isoformat() if expires_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

@app.get("/api/v1/auth/api-keys", tags=["auth"])
@user_rate_limit("10/minute")
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        api_keys = await services.db_service.get_user_api_keys(current_user['user_id'])
        return {
            "api_keys": [
                {
                    "key_id": key['key_id'],
                    "name": key['name'],
                    "created_at": key['created_at'],
                    "expires_at": key['expires_at'],
                    "last_used": key.get('last_used'),
                    "usage_count": key.get('usage_count', 0),
                    "is_active": key['is_active']
                } for key in api_keys
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list API keys for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API keys")

@app.delete("/api/v1/auth/api-keys/{key_id}", tags=["auth"])
@user_rate_limit("10/minute")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        try:
            uuid.UUID(key_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid key ID format")

        success = await services.db_service.revoke_api_key(current_user['user_id'], key_id)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        await services.cache_service.delete_pattern(f"api_key:{key_id}:*")
        logger.info(f"Revoked API key {key_id} for user {current_user['user_id']} - Correlation-ID: {correlation_id}")
        return {"message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id} for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to revoke API key")

@app.post("/api/v1/batch/generate", tags=["batch"])
@user_rate_limit("2/hour")
async def batch_generate(
    batch_request: BatchRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        if len(batch_request.requests) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 requests per batch")

        batch_id = str(uuid.uuid4())
        request_ids = []

        for req in batch_request.requests:
            request_id = str(uuid.uuid4())
            request_ids.append(request_id)
            request_type = "resume" if isinstance(req, ResumeRequest) else "cover_letter"
            await services.db_service.store_generation_request(
                user_id=current_user['user_id'],
                request_id=request_id,
                request_type=request_type,
                request_data=req.dict(),
                status="queued",
                batch_id=batch_id,
                priority=batch_request.priority
            )

        background_tasks.add_task(process_batch_requests, batch_id, request_ids, current_user, services)
        logger.info(f"Created batch {batch_id} with {len(request_ids)} requests for user {current_user['user_id']} - Correlation-ID: {correlation_id}")

        return {
            "batch_id": batch_id,
            "request_ids": request_ids,
            "status": "queued",
            "total_requests": len(request_ids),
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=len(request_ids) * 2)).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to create batch request")

@celery.task
async def process_batch_requests(batch_id: str, request_ids: List[str], user: dict, services: ServiceContainer):
    try:
        logger.info(f"Starting batch processing for batch {batch_id}")
        for request_id in request_ids:
            try:
                request_data = await services.db_service.get_generation_request(request_id)
                if not request_data:
                    continue

                await services.db_service.update_request_status(request_id, "processing")
                request_type = request_data['request_type']
                style = request_data['request_data'].get('template_style' if request_type == "resume" else 'tone', 'modern')

                content = await asyncio.wait_for(
                    services.ai_service.generate_resume(request_data['request_data']) if request_type == "resume"
                    else services.ai_service.generate_cover_letter(request_data['request_data']),
                    timeout=120.0
                )

                pdf_content = await services.pdf_generator.generate_pdf_async(
                    content=content,
                    template_type=request_type,
                    style=style
                )

                await services.db_service.store_generated_file(
                    request_id=request_id,
                    file_type="pdf",
                    file_content=pdf_content,
                    filename=f"{request_type}_{request_id}.pdf"
                )

                await services.db_service.update_request_status(request_id, "completed")
                logger.info(f"Completed batch request {request_id}")
            except Exception as e:
                logger.error(f"Failed to process batch request {request_id}: {str(e)}")
                await services.db_service.update_request_status(request_id, "failed", str(e))

        user_data = await services.db_service.get_user(user['user_id'])
        if user_data.get('email_notifications', True):
            await services.notification_service.send_batch_completion_email(
                user_data['email'], batch_id, len(request_ids)
            )
        if user_data.get('webhook_url'):
            await services.notification_service.send_webhook_notification(
                user_data['webhook_url'],
                {"batch_id": batch_id, "status": "completed", "total_requests": len(request_ids)}
            )
        logger.info(f"Completed batch processing for batch {batch_id}")
    except Exception as e:
        logger.error(f"Batch processing failed for batch {batch_id}: {str(e)}")

@app.get("/api/v1/batch/{batch_id}/status", tags=["batch"])
@user_rate_limit("20/minute")
async def get_batch_status(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        try:
            uuid.UUID(batch_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid batch ID format")

        batch_status = await services.db_service.get_batch_status(batch_id, current_user['user_id'])
        if not batch_status:
            raise HTTPException(status_code=404, detail="Batch not found or access denied")

        logger.info(f"Batch status retrieved - Batch: {batch_id} - User: {current_user['user_id']} - Correlation-ID: {correlation_id}")
        return batch_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status {batch_id}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve batch status")

@app.get("/api/v1/analytics/usage", tags=["analytics"])
@user_rate_limit("5/minute")
async def get_usage_analytics(
    request: Request,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    days: int = 30
):
    correlation_id = get_correlation_id(request)
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

        cache_key = f"analytics:{current_user['user_id']}:{days}"
        cached_analytics = await services.cache_service.get(cache_key)
        if cached_analytics:
            logger.info(f"Analytics retrieved from cache - User: {current_user['user_id']} - Correlation-ID: {correlation_id}")
            return json.loads(cached_analytics)

        analytics = await services.db_service.get_user_analytics(current_user['user_id'], days)
        await services.cache_service.set(cache_key, json.dumps(analytics, default=str), ttl=3600)
        logger.info(f"Analytics retrieved - User: {current_user['user_id']} - Correlation-ID: {correlation_id}")
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics for user {current_user['user_id']}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage analytics")

@app.get("/api/v1/templates", response_model=List[TemplateResponse], tags=["templates"])
@user_rate_limit("20/minute")
async def get_available_templates(
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        cache_key = "templates:all"
        cached_templates = await services.cache_service.get(cache_key)
        if cached_templates:
            logger.info(f"Templates retrieved from cache - Correlation-ID: {correlation_id}")
            return json.loads(cached_templates)

        templates = await services.db_service.get_available_templates()
        await services.cache_service.set(cache_key, json.dumps(templates, default=str), ttl=86400)
        logger.info(f"Templates retrieved - Correlation-ID: {correlation_id}")
        return templates
    except Exception as e:
        logger.error(f"Failed to retrieve templates: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")

@app.get("/api/v1/templates/{template_id}/preview", response_model=TemplateResponse, tags=["templates"])
@user_rate_limit("20/minute")
async def get_template_preview(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    services: ServiceContainer = Depends(get_services),
    request: Request = None
):
    correlation_id = get_correlation_id(request)
    try:
        cache_key = f"template_preview:{template_id}"
        cached_preview = await services.cache_service.get(cache_key)
        if cached_preview:
            logger.info(f"Template preview retrieved from cache - Template: {template_id} - Correlation-ID: {correlation_id}")
            return json.loads(cached_preview)

        preview = await services.db_service.get_template_preview(template_id)
        if not preview:
            raise HTTPException(status_code=404, detail="Template not found")

        await services.cache_service.set(cache_key, json.dumps(preview, default=str), ttl=86400)
        logger.info(f"Template preview retrieved - Template: {template_id} - Correlation-ID: {correlation_id}")
        return preview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve template preview {template_id}: {str(e)} - Correlation-ID: {correlation_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve template preview")

# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = get_correlation_id(request)
    logger.warning(f"Validation error from {request.client.host}: {exc} - Correlation-ID: {correlation_id}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "The request data is invalid",
            "details": exc.errors()
        }
    )

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    correlation_id = get_correlation_id(request)
    logger.warning(f"Rate limit exceeded from {request.client.host}: {exc} - Correlation-ID: {correlation_id}")
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate Limit Exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.retry_after
        }
    )

@app.exception_handler(Exception)
async def internal_server_error_handler(request: Request, exc):
    correlation_id = get_correlation_id(request)
    error_id = str(uuid.uuid4())
    logger.error(f"Internal server error {error_id}: {exc} - Correlation-ID: {correlation_id}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "error_id": error_id
        }
    )

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(
            "main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.environment == "development",
            workers=4,
            http="httptools",
            log_config=None
        )
    except Exception as e:
        logger.error(f"Failed to start Uvicorn server: {str(e)}")
        raise
