"""
FastAPI Application

HTTP API server for application upload and interview scheduling.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import asyncio
import random
import json

from livekit import api as livekit_api

from app.config import Config, get_config
from app.services.resume_service import ResumeService
from app.services.booking_service import BookingService
from app.services.email_service import EmailService
from app.utils.logger import get_logger

logger = get_logger(__name__)
config = get_config()

# Create FastAPI app
app = FastAPI(
    title="Interview Scheduling API",
    description="API for application upload and interview scheduling",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
resume_service = ResumeService(config)
booking_service = BookingService(config)
email_service = EmailService(config)


# Request/Response Models
class ScheduleInterviewRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    datetime: str  # ISO datetime string
    resumeUrl: Optional[str] = None
    resumeText: Optional[str] = None


class UploadApplicationResponse(BaseModel):
    resumeUrl: str
    resumeText: Optional[str] = None
    extractionError: Optional[str] = None


class ScheduleInterviewResponse(BaseModel):
    ok: bool
    interviewUrl: str
    emailSent: bool = False
    emailError: Optional[str] = None


class BookingResponse(BaseModel):
    token: str
    name: str
    email: str
    phone: str
    scheduled_at: str
    created_at: str
    resume_text: Optional[str] = None
    resume_url: Optional[str] = None


class ConnectionDetailsRequest(BaseModel):
    room_config: Optional[dict] = None
    token: Optional[str] = None


class ConnectionDetailsResponse(BaseModel):
    serverUrl: str
    roomName: str
    participantName: str
    participantToken: str


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "interview-scheduling-api"}


@app.post("/api/upload-application", response_model=UploadApplicationResponse)
async def upload_application(file: UploadFile = File(...)):
    """
    Upload and process application file.
    
    Extracts text from PDF or DOC/DOCX files and uploads to Supabase Storage.
    """
    try:
        logger.info(f"[API] Received application upload: {file.filename} ({file.content_type})")
        
        # Read file content
        file_content = await file.read()
        
        # Validate file
        is_valid, error_msg = resume_service.validate_file(
            file_content, file.filename, file.content_type
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Upload to Supabase Storage
        try:
            resume_url = booking_service.upload_resume_to_storage(file_content, file.filename)
        except Exception as e:
            logger.error(f"[API] Failed to upload to storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload application: {str(e)}"
            )
        
        # Extract text
        resume_text, extraction_error = resume_service.extract_text(
            file_content, file.filename, file.content_type
        )
        
        if resume_text:
            logger.info(f"[API] ✅ Application processed: {len(resume_text)} characters extracted")
        else:
            logger.warning(f"[API] ⚠️ Application uploaded but text extraction failed: {extraction_error}")
        
        return UploadApplicationResponse(
            resumeUrl=resume_url,
            resumeText=resume_text if resume_text else None,
            extractionError=extraction_error,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to process application: {str(e)}"
        logger.error(f"[API] {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post("/api/schedule-interview", response_model=ScheduleInterviewResponse)
async def schedule_interview(request: ScheduleInterviewRequest):
    """
    Schedule an interview.
    
    Creates a booking in the database and sends confirmation email.
    """
    try:
        logger.info(f"[API] Received schedule request: {request.email} at {request.datetime}")
        
        # Validate required fields
        if not request.name or not request.email or not request.phone or not request.datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: name, email, phone, datetime"
            )
        
        # Parse datetime
        try:
            # Try parsing with timezone info first
            if 'Z' in request.datetime or '+' in request.datetime or request.datetime.count('-') > 2:
                # Has timezone info
                scheduled_at = datetime.fromisoformat(request.datetime.replace('Z', '+00:00'))
            else:
                # No timezone info - treat as local time and convert to UTC
                naive_dt = datetime.fromisoformat(request.datetime)
                # Assume it's in IST (UTC+5:30) if no timezone specified
                # Convert to UTC for storage
                ist_offset = timezone(timedelta(hours=5, minutes=30))
                scheduled_at = naive_dt.replace(tzinfo=ist_offset).astimezone(timezone.utc)
        except ValueError:
            try:
                # Fallback: try parsing as-is
                scheduled_at = datetime.fromisoformat(request.datetime)
                # If still naive, assume IST and convert to UTC
                if scheduled_at.tzinfo is None:
                    ist_offset = timezone(timedelta(hours=5, minutes=30))
                    scheduled_at = scheduled_at.replace(tzinfo=ist_offset).astimezone(timezone.utc)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid datetime format. Expected ISO format."
                )
        
        # Create booking
        try:
            token = booking_service.create_booking(
                name=request.name,
                email=request.email,
                phone=request.phone,
                scheduled_at=scheduled_at,
                resume_text=request.resumeText,
                resume_url=request.resumeUrl,
            )
        except Exception as e:
            logger.error(f"[API] Failed to create booking: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create booking: {str(e)}"
            )
        
        # Generate interview URL
        base_url = config.server.frontend_url.rstrip('/')
        interview_url = f"{base_url}/interview/{token}"
        
        # Send email (non-blocking)
        email_sent = False
        email_error = None
        
        try:
            email_sent, email_error = await email_service.send_interview_email(
                to_email=request.email,
                name=request.name,
                interview_url=interview_url,
                scheduled_at=scheduled_at,
            )
        except Exception as e:
            email_error = str(e)
            logger.warning(f"[API] Email sending failed: {email_error}")
        
        logger.info(f"[API] ✅ Interview scheduled: {interview_url}")
        
        return ScheduleInterviewResponse(
            ok=True,
            interviewUrl=interview_url,
            emailSent=email_sent,
            emailError=email_error,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to schedule interview: {str(e)}"
        logger.error(f"[API] {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get("/api/booking/{token}", response_model=BookingResponse)
async def get_booking(token: str):
    """
    Get booking details by token.
    """
    try:
        booking = booking_service.get_booking(token)
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        return BookingResponse(**booking)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to fetch booking: {str(e)}"
        logger.error(f"[API] {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post("/api/connection-details", response_model=ConnectionDetailsResponse)
async def connection_details(request: ConnectionDetailsRequest):
    """
    Generate LiveKit connection details for interview.
    
    Creates a participant token and room configuration with agent.
    """
    try:
        # Validate LiveKit config
        if not config.livekit.url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LIVEKIT_URL is not configured"
            )
        if not config.livekit.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LIVEKIT_API_KEY is not configured"
            )
        if not config.livekit.api_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LIVEKIT_API_SECRET is not configured"
            )
        
        # Extract agent name from request
        logger.info(f"[API] 📥 Received connection-details request:")
        logger.info(f"   room_config: {request.room_config}")
        logger.info(f"   token: {request.token if request.token else 'None'}")
        
        agent_name = None
        if request.room_config and isinstance(request.room_config, dict):
            agents = request.room_config.get("agents", [])
            logger.info(f"   Found agents array: {agents}")
            if agents and len(agents) > 0:
                agent_name = agents[0].get("agent_name")
                logger.info(f"   Extracted agent_name from request: '{agent_name}'")
        
        # Use default agent name from config if not provided
        if not agent_name:
            agent_name = config.livekit.agent_name
            logger.info(f"   Using default agent_name from config: '{agent_name}'")
        else:
            logger.info(f"   ✅ Using agent_name: '{agent_name}'")
        
        # If token is provided, fetch booking to get resume text
        resume_text = None
        if request.token:
            try:
                booking = booking_service.get_booking(request.token)
                if booking and booking.get("resume_text"):
                    resume_text = booking["resume_text"]
                    logger.info(f"[API] Found resume text for token {request.token} ({len(resume_text)} chars)")
            except Exception as e:
                logger.warning(f"[API] Failed to fetch booking for resume: {e}")
        
        # Generate room details
        participant_name = "user"
        participant_identity = f"voice_assistant_user_{random.randint(1, 99999)}"
        room_name = f"voice_assistant_room_{random.randint(1, 99999)}"
        
        # Create room metadata with resume text (if available)
        room_metadata = None
        if resume_text:
            room_metadata = json.dumps({"resume_text": resume_text})
        
        # Create LiveKit AccessToken
        token = livekit_api.AccessToken(
            config.livekit.api_key,
            config.livekit.api_secret
        )
        token.with_identity(participant_identity)
        token.with_name(participant_name)
        token.with_ttl(timedelta(minutes=15))
        
        # Add video grant (permissions)
        grant = livekit_api.VideoGrants(
            room=room_name,
            room_join=True,
            can_publish=True,
            can_publish_data=True,
            can_subscribe=True,
        )
        token.with_grants(grant)
        
        # Set room configuration with agent
        if agent_name:
            logger.info(f"[API] 🔧 Creating RoomConfiguration with agent dispatch:")
            logger.info(f"   Agent Name: '{agent_name}'")
            room_config = livekit_api.RoomConfiguration()
            room_agent_dispatch = room_config.agents.add()
            room_agent_dispatch.agent_name = agent_name
            if room_metadata:
                room_config.metadata = room_metadata
                logger.info(f"   Room metadata: {room_metadata[:100]}...")
            token.with_room_config(room_config)
            logger.info(f"[API] ✅ RoomConfiguration set with agent dispatch")
        else:
            logger.warning(f"[API] ⚠️  No agent_name provided - agent will NOT be dispatched!")
        
        # Generate JWT token
        participant_token = token.to_jwt()
        
        logger.info(f"[API] ✅ Generated connection details:")
        logger.info(f"   Server URL: {config.livekit.url}")
        logger.info(f"   Room Name: {room_name}")
        logger.info(f"   Participant Name: {participant_name}")
        logger.info(f"   Agent Name: {agent_name}")
        logger.info(f"   Token Length: {len(participant_token)} chars")
        
        return ConnectionDetailsResponse(
            serverUrl=config.livekit.url,
            roomName=room_name,
            participantName=participant_name,
            participantToken=participant_token,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to generate connection details: {str(e)}"
        logger.error(f"[API] {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )

