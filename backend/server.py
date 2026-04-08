from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import jwt
from passlib.context import CryptContext
import json
import asyncio
import httpx
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from fastapi import Form

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase connection
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'default_secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Create the main app
app = FastAPI(title="MedicAI API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for frontend requests
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class AdminLogin(BaseModel):
    email: str
    password: str

class AdminCreate(BaseModel):
    email: str
    password: str
    name: str
    clinic_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    admin: dict

# Clinic Models (Multi-tenant)
class ClinicResponse(BaseModel):
    id: str
    code: str
    name: str
    clinic_name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    welcome_message: Optional[str] = None
    consultation_price: Optional[float] = None
    consultation_currency: Optional[str] = "MXN"
    is_active: bool
    subscription_status: str
    subscription_start: Optional[str] = None
    subscription_end: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    whatsapp_link: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_display_name: Optional[str] = None

class ClinicCreate(BaseModel):
    code: str
    name: str
    clinic_name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    welcome_message: Optional[str] = None
    consultation_price: Optional[float] = None
    consultation_currency: Optional[str] = "MXN"
    notes: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_display_name: Optional[str] = None

class ClinicUpdate(BaseModel):
    name: Optional[str] = None
    clinic_name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    welcome_message: Optional[str] = None
    consultation_price: Optional[float] = None
    consultation_currency: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_status: Optional[str] = None
    subscription_end: Optional[str] = None
    notes: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_display_name: Optional[str] = None

class SuperAdminStats(BaseModel):
    total_clinics: int
    active_clinics: int
    total_patients: int
    total_appointments: int
    appointments_today: int
    pending_alerts: int

class PatientResponse(BaseModel):
    id: str
    phone: str
    name: Optional[str] = None
    created_at: str
    last_interaction: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    date: str
    time: str
    reason: str
    status: str
    priority: Optional[str] = "normal"
    created_at: str

class AppointmentCreate(BaseModel):
    patient_id: str
    date: str
    time: str
    reason: str
    status: str = "confirmed"
    priority: str = "normal"

class AppointmentUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class AvailabilitySlot(BaseModel):
    id: Optional[str] = None
    day_of_week: int  # 0=Sunday, 1=Monday, etc.
    start_time: str
    end_time: str
    is_available: bool = True

class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    sender: str  # 'patient' or 'ai'
    content: str
    timestamp: str
    intent: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    started_at: str
    last_message_at: Optional[str] = None
    status: str
    messages: Optional[List[ConversationMessage]] = None

class AlertResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    message: str
    priority: str
    status: str
    created_at: str

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    allergies: Optional[str] = None
    pathologies: Optional[str] = None
    blood_type: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class MedicalRecordUpdate(BaseModel):
    allergies: Optional[str] = None
    pathologies: Optional[str] = None
    blood_type: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None

class ConsultationNoteResponse(BaseModel):
    id: str
    patient_id: str
    appointment_id: Optional[str] = None
    date: str
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    observations: Optional[str] = None
    created_at: str

class ConsultationNoteCreate(BaseModel):
    patient_id: str
    appointment_id: Optional[str] = None
    date: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    observations: Optional[str] = None

class ConsultationNoteUpdate(BaseModel):
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    observations: Optional[str] = None


class AlertUpdate(BaseModel):
    status: str

class WebhookMessage(BaseModel):
    phone: str
    message: str
    timestamp: Optional[str] = None
    to: Optional[str] = None  # Destination number - identifies which clinic's WhatsApp received the message

class DashboardStats(BaseModel):
    total_patients: int
    total_appointments_today: int
    total_appointments_week: int
    pending_alerts: int
    confirmed_appointments: int
    cancelled_appointments: int

# ============ AUTH HELPERS ============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        admin_id = payload.get("sub")
        if admin_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get full admin info including clinic_id and is_super_admin
        result = supabase.table("admins").select("id, email, name, clinic_id, is_super_admin").eq("id", admin_id).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="Admin not found")
        
        admin = result.data[0]
        return {
            "id": admin["id"], 
            "email": admin["email"],
            "name": admin.get("name"),
            "clinic_id": admin.get("clinic_id"),
            "is_super_admin": admin.get("is_super_admin", False)
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_super_admin(admin: dict = Depends(get_current_admin)):
    """Require super admin access"""
    if not admin.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return admin

# ============ AUTH ENDPOINTS ============

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: AdminLogin):
    """Admin login endpoint"""
    try:
        logger.info(f"Login attempt for: {credentials.email}")
        
        # Check if supabase client is properly initialized
        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials are not set in environment variables!")
            raise HTTPException(status_code=500, detail="Database configuration error")
            
        result = supabase.table("admins").select("*").eq("email", credentials.email).execute()
        
        if not result.data:
            logger.warning(f"Login failed: User {credentials.email} not found in database")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        admin = result.data[0]
        logger.info(f"User found, verifying password...")
        
        if not verify_password(credentials.password, admin["password_hash"]):
            logger.warning(f"Login failed: Incorrect password for {credentials.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        access_token = create_access_token(
            data={"sub": admin["id"], "email": admin["email"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            admin={
                "id": admin["id"], 
                "email": admin["email"], 
                "name": admin["name"],
                "clinic_id": admin.get("clinic_id"),
                "is_super_admin": admin.get("is_super_admin", False)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_admin(admin_data: AdminCreate):
    """Register a new admin (for initial setup)"""
    try:
        # Check if admin exists
        existing = supabase.table("admins").select("id").eq("email", admin_data.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        admin_id = str(uuid.uuid4())
        password_hash = get_password_hash(admin_data.password)
        
        new_admin = {
            "id": admin_id,
            "email": admin_data.email,
            "password_hash": password_hash,
            "name": admin_data.name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("admins").insert(new_admin).execute()
        
        access_token = create_access_token(
            data={"sub": admin_id, "email": admin_data.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            admin={"id": admin_id, "email": admin_data.email, "name": admin_data.name}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.get("/auth/me")
async def get_current_user(admin: dict = Depends(get_current_admin)):
    """Get current admin info"""
    try:
        result = supabase.table("admins").select("id, email, name, clinic_id, is_super_admin, created_at").eq("id", admin["id"]).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Admin not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin info")

# ============ SUPER ADMIN - CLINICS ENDPOINTS ============

WHATSAPP_NUMBER_LEGACY = os.environ.get('WHATSAPP_NUMBER', '521XXXXXXXXXX')  # Fallback for clinics without own number
WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'medicai_2026')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')  # System User permanent token

def generate_whatsapp_link(clinic):
    """Generate WhatsApp link using clinic's own number when available, fallback to shared number"""
    from urllib.parse import quote
    
    number = clinic.get('whatsapp_number')
    doctor_name = clinic.get('name', '')
    code = clinic.get('code', '')
    
    if number:
        # Clinic has its own number - clean link without code
        message = f"Hola, quiero agendar una cita con {doctor_name}" if doctor_name else "Hola, quiero agendar una cita"
    else:
        # Fallback: shared number with code for identification
        number = WHATSAPP_NUMBER_LEGACY
        if doctor_name:
            message = f"Hola, quiero agendar una cita con {doctor_name} (#{code})"
        else:
            message = f"Hola, quiero agendar una cita (#{code})"
    
    return f"https://wa.me/{number}?text={quote(message)}"

@api_router.get("/superadmin/stats", response_model=SuperAdminStats)
async def get_superadmin_stats(admin: dict = Depends(require_super_admin)):
    """Get super admin global statistics"""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        
        clinics_result = supabase.table("clinics").select("id", count="exact").execute()
        active_clinics_result = supabase.table("clinics").select("id", count="exact").eq("is_active", True).execute()
        patients_result = supabase.table("patients").select("id", count="exact").execute()
        appointments_result = supabase.table("appointments").select("id", count="exact").execute()
        today_appointments_result = supabase.table("appointments").select("id", count="exact").eq("date", today).execute()
        alerts_result = supabase.table("alerts").select("id", count="exact").eq("status", "pending").execute()
        
        return SuperAdminStats(
            total_clinics=clinics_result.count or 0,
            active_clinics=active_clinics_result.count or 0,
            total_patients=patients_result.count or 0,
            total_appointments=appointments_result.count or 0,
            appointments_today=today_appointments_result.count or 0,
            pending_alerts=alerts_result.count or 0
        )
    except Exception as e:
        logger.error(f"Get superadmin stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")

@api_router.get("/superadmin/clinics", response_model=List[ClinicResponse])
async def get_all_clinics(admin: dict = Depends(require_super_admin)):
    """Get all clinics (super admin only)"""
    try:
        # Ignore clinics that have been marked as deleted
        result = supabase.table("clinics").select("*").eq("is_active", True).order("created_at", desc=True).execute()
        
        clinics = []
        for clinic in result.data:
            clinic["whatsapp_link"] = generate_whatsapp_link(clinic)
            clinics.append(clinic)
        
        return clinics
    except Exception as e:
        logger.error(f"Get clinics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get clinics")

@api_router.get("/superadmin/clinics/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Get a specific clinic"""
    try:
        result = supabase.table("clinics").select("*").eq("id", clinic_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Clinic not found")
        
        clinic = result.data[0]
        clinic["whatsapp_link"] = generate_whatsapp_link(clinic)
        return clinic
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get clinic error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get clinic")

@api_router.post("/superadmin/clinics", response_model=ClinicResponse)
async def create_clinic(clinic_data: ClinicCreate, admin: dict = Depends(require_super_admin)):
    """Create a new clinic/doctor"""
    try:
        # Check if code already exists
        existing = supabase.table("clinics").select("id").eq("code", clinic_data.code.upper()).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Clinic code already exists")
        
        clinic_id = str(uuid.uuid4())
        new_clinic = {
            "id": clinic_id,
            "code": clinic_data.code.upper(),
            "name": clinic_data.name,
            "clinic_name": clinic_data.clinic_name,
            "specialty": clinic_data.specialty,
            "phone": clinic_data.phone,
            "email": clinic_data.email,
            "address": clinic_data.address,
            "welcome_message": clinic_data.welcome_message or f"¡Hola! Soy el asistente del {clinic_data.name}. ¿En qué puedo ayudarte?",
            "notes": clinic_data.notes,
            "whatsapp_number": clinic_data.whatsapp_number,
            "whatsapp_phone_id": clinic_data.whatsapp_phone_id,
            "whatsapp_display_name": clinic_data.whatsapp_display_name,
            "is_active": True,
            "subscription_status": "active",
            "subscription_start": datetime.now(timezone.utc).date().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("clinics").insert(new_clinic).execute()
        
        new_clinic["whatsapp_link"] = generate_whatsapp_link(new_clinic)
        return new_clinic
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create clinic error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create clinic")

@api_router.put("/superadmin/clinics/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(clinic_id: str, update_data: ClinicUpdate, admin: dict = Depends(require_super_admin)):
    """Update a clinic"""
    try:
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        supabase.table("clinics").update(update_dict).eq("id", clinic_id).execute()
        
        result = supabase.table("clinics").select("*").eq("id", clinic_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Clinic not found")
        
        clinic = result.data[0]
        clinic["whatsapp_link"] = generate_whatsapp_link(clinic)
        return clinic
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update clinic error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update clinic")

@api_router.delete("/superadmin/clinics/{clinic_id}")
async def delete_clinic(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Hard delete a clinic and all associated data"""
    errors = []
    
    try:
        # 1. Get all patients in this clinic
        patients = supabase.table("patients").select("id").eq("clinic_id", clinic_id).execute()
        patient_ids = [p["id"] for p in (patients.data or [])]
        
        # 2. Delete per-patient data
        for pid in patient_ids:
            # Messages (via conversations)
            try:
                convos = supabase.table("conversations").select("id").eq("patient_id", pid).execute()
                for conv in (convos.data or []):
                    try: supabase.table("messages").delete().eq("conversation_id", conv["id"]).execute()
                    except: pass
            except Exception as e: errors.append(f"messages for patient {pid}: {e}")
            
            for table in ["conversations", "appointments", "consultation_notes", "medical_records", "alerts"]:
                try: supabase.table(table).delete().eq("patient_id", pid).execute()
                except Exception as e: errors.append(f"{table} for patient {pid}: {e}")
        
        # 3. Delete clinic-level data (some tables also have clinic_id directly)
        for table in ["conversations", "appointments", "alerts"]:
            try: supabase.table(table).delete().eq("clinic_id", clinic_id).execute()
            except: pass
        
        # 4. Delete patients, availability, admins, then the clinic itself
        for table, col, val in [
            ("patients", "clinic_id", clinic_id),
            ("availability", "clinic_id", clinic_id),
            ("admins", "clinic_id", clinic_id),
            ("clinics", "id", clinic_id),
        ]:
            try: supabase.table(table).delete().eq(col, val).execute()
            except Exception as e: errors.append(f"{table}: {e}")
        
        if errors:
            logger.warning(f"Clinic {clinic_id} deleted with warnings: {errors}")
        
        return {"message": "Clinic permanently deleted"}
    except Exception as e:
        logger.error(f"Delete clinic error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete clinic: {str(e)}")

@api_router.post("/superadmin/clinics/{clinic_id}/create-admin")
async def create_clinic_admin(clinic_id: str, admin_data: AdminCreate, admin: dict = Depends(require_super_admin)):
    """Create an admin account for a clinic"""
    try:
        # Verify clinic exists
        clinic_result = supabase.table("clinics").select("id, name").eq("id", clinic_id).execute()
        if not clinic_result.data:
            raise HTTPException(status_code=404, detail="Clinic not found")
        
        # Check if email already exists
        existing = supabase.table("admins").select("id").eq("email", admin_data.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        admin_id = str(uuid.uuid4())
        password_hash = get_password_hash(admin_data.password)
        
        new_admin = {
            "id": admin_id,
            "email": admin_data.email,
            "password_hash": password_hash,
            "name": admin_data.name,
            "clinic_id": clinic_id,
            "is_super_admin": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("admins").insert(new_admin).execute()
        
        return {
            "message": "Admin created successfully",
            "admin_id": admin_id,
            "email": admin_data.email,
            "clinic_id": clinic_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create clinic admin error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create admin")

@api_router.get("/superadmin/clinics/{clinic_id}/stats")
async def get_clinic_stats(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Get statistics for a specific clinic"""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        
        patients = supabase.table("patients").select("id", count="exact").eq("clinic_id", clinic_id).execute()
        appointments = supabase.table("appointments").select("id", count="exact").eq("clinic_id", clinic_id).execute()
        today_appointments = supabase.table("appointments").select("id", count="exact").eq("clinic_id", clinic_id).eq("date", today).execute()
        alerts = supabase.table("alerts").select("id", count="exact").eq("clinic_id", clinic_id).eq("status", "pending").execute()
        
        return {
            "total_patients": patients.count or 0,
            "total_appointments": appointments.count or 0,
            "appointments_today": today_appointments.count or 0,
            "pending_alerts": alerts.count or 0
        }
    except Exception as e:
        logger.error(f"Get clinic stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get clinic stats")

@api_router.post("/superadmin/fix-orphan-patients/{clinic_id}")
async def fix_orphan_patients(clinic_id: str, admin: dict = Depends(get_current_admin)):
    """Assign orphan patients (without clinic_id) to a specific clinic - Super Admin only"""
    if not admin.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only super admin can perform this action")
    
    try:
        # Get all patients without clinic_id
        orphan_patients = supabase.table("patients").select("id, phone").is_("clinic_id", "null").execute()
        
        if not orphan_patients.data:
            return {"message": "No orphan patients found", "updated": 0}
        
        # Update them to the specified clinic
        updated_count = 0
        for patient in orphan_patients.data:
            supabase.table("patients").update({"clinic_id": clinic_id}).eq("id", patient["id"]).execute()
            updated_count += 1
            logger.info(f"Assigned patient {patient['phone']} to clinic {clinic_id}")
        
        # Also update orphan conversations
        orphan_convs = supabase.table("conversations").select("id").is_("clinic_id", "null").execute()
        for conv in orphan_convs.data or []:
            supabase.table("conversations").update({"clinic_id": clinic_id}).eq("id", conv["id"]).execute()
        
        return {
            "message": f"Successfully assigned {updated_count} patients to clinic",
            "updated": updated_count
        }
    except Exception as e:
        logger.error(f"Fix orphan patients error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fix orphan patients")

# ============ PATIENTS ENDPOINTS ============

@api_router.get("/patients", response_model=List[PatientResponse])
async def get_patients(admin: dict = Depends(get_current_admin)):
    """Get all patients (filtered by clinic for non-super-admins)"""
    try:
        query = supabase.table("patients").select("*")
        
        # Filter by clinic if not super admin
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        result = query.order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Get patients error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patients")

@api_router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, admin: dict = Depends(get_current_admin)):
    """Get a specific patient (verified by clinic ownership)"""
    try:
        query = supabase.table("patients").select("*").eq("id", patient_id)
        
        # Verify patient belongs to admin's clinic
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        result = query.execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Patient not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get patient error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patient")

@api_router.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, update_data: PatientUpdate, admin: dict = Depends(get_current_admin)):
    """Update patient information (verified by clinic ownership)"""
    try:
        # Verify patient belongs to admin's clinic
        verify_query = supabase.table("patients").select("id").eq("id", patient_id)
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            verify_query = verify_query.eq("clinic_id", admin["clinic_id"])
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        supabase.table("patients").update(update_dict).eq("id", patient_id).execute()
        
        result = supabase.table("patients").select("*").eq("id", patient_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Patient not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update patient error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update patient")

@api_router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: str, admin: dict = Depends(get_current_admin)):
    """Delete a patient and all associated data (verified by clinic ownership)"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify patient belongs to admin's clinic
        verify_query = supabase.table("patients").select("id, name, phone").eq("id", patient_id)
        if not admin.get("is_super_admin") and clinic_id:
            verify_query = verify_query.eq("clinic_id", clinic_id)
        verify_result = verify_query.execute()
        
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
        patient_info = verify_result.data[0]
        logger.info(f"Deleting patient {patient_id} ({patient_info.get('name', 'N/A')}) by admin {admin.get('id')}")
        
        # Delete all related data in order (cascade)
        # 1. Delete messages (linked to conversations)
        conv_result = supabase.table("conversations").select("id").eq("patient_id", patient_id).execute()
        if conv_result.data:
            conv_ids = [c["id"] for c in conv_result.data]
            for conv_id in conv_ids:
                supabase.table("messages").delete().eq("conversation_id", conv_id).execute()
        
        # 2. Delete conversations
        supabase.table("conversations").delete().eq("patient_id", patient_id).execute()
        
        # 3. Delete appointments
        supabase.table("appointments").delete().eq("patient_id", patient_id).execute()
        
        # 4. Delete consultation notes
        supabase.table("consultation_notes").delete().eq("patient_id", patient_id).execute()
        
        # 5. Delete medical records
        supabase.table("medical_records").delete().eq("patient_id", patient_id).execute()
        
        # 6. Delete alerts
        supabase.table("alerts").delete().eq("patient_id", patient_id).execute()
        
        # 7. Finally delete the patient
        supabase.table("patients").delete().eq("id", patient_id).execute()
        
        logger.info(f"Patient {patient_id} and all associated data deleted successfully")
        
        return {
            "success": True,
            "message": f"Paciente {patient_info.get('name', 'desconocido')} eliminado correctamente",
            "deleted_patient_id": patient_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete patient error: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar el paciente")

# ============ MEDICAL RECORDS ENDPOINTS ============

@api_router.get("/patients/{patient_id}/medical-record", response_model=MedicalRecordResponse)
async def get_medical_record(patient_id: str, admin: dict = Depends(get_current_admin)):
    """Get patient's medical record (verified by clinic ownership)"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify patient belongs to admin's clinic
        if not admin.get("is_super_admin") and clinic_id:
            patient_check = supabase.table("patients").select("id").eq("id", patient_id).eq("clinic_id", clinic_id).execute()
            if not patient_check.data:
                raise HTTPException(status_code=404, detail="Patient not found")
        
        result = supabase.table("medical_records").select("*").eq("patient_id", patient_id).execute()
        if not result.data:
            # Create empty record if doesn't exist
            record_id = str(uuid.uuid4())
            new_record = {
                "id": record_id,
                "patient_id": patient_id,
                "clinic_id": clinic_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            supabase.table("medical_records").insert(new_record).execute()
            return new_record
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get medical record error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get medical record")

@api_router.put("/patients/{patient_id}/medical-record", response_model=MedicalRecordResponse)
async def update_medical_record(patient_id: str, update_data: MedicalRecordUpdate, admin: dict = Depends(get_current_admin)):
    """Update patient's medical record (verified by clinic ownership)"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify patient belongs to admin's clinic
        if not admin.get("is_super_admin") and clinic_id:
            patient_check = supabase.table("patients").select("id").eq("id", patient_id).eq("clinic_id", clinic_id).execute()
            if not patient_check.data:
                raise HTTPException(status_code=404, detail="Patient not found")
        
        # Check if record exists
        existing = supabase.table("medical_records").select("id").eq("patient_id", patient_id).execute()
        
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if not existing.data:
            # Create new record
            record_id = str(uuid.uuid4())
            update_dict["id"] = record_id
            update_dict["patient_id"] = patient_id
            update_dict["clinic_id"] = clinic_id
            update_dict["created_at"] = datetime.now(timezone.utc).isoformat()
            supabase.table("medical_records").insert(update_dict).execute()
        else:
            supabase.table("medical_records").update(update_dict).eq("patient_id", patient_id).execute()
        
        result = supabase.table("medical_records").select("*").eq("patient_id", patient_id).execute()
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update medical record error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update medical record")

# ============ CONSULTATION NOTES ENDPOINTS ============

@api_router.get("/patients/{patient_id}/consultation-notes", response_model=List[ConsultationNoteResponse])
async def get_consultation_notes(patient_id: str, admin: dict = Depends(get_current_admin)):
    """Get patient's consultation notes (verified by clinic ownership)"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify patient belongs to admin's clinic
        if not admin.get("is_super_admin") and clinic_id:
            patient_check = supabase.table("patients").select("id").eq("id", patient_id).eq("clinic_id", clinic_id).execute()
            if not patient_check.data:
                raise HTTPException(status_code=404, detail="Patient not found")
        
        result = supabase.table("consultation_notes").select("*").eq("patient_id", patient_id).order("date", desc=True).execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get consultation notes error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get consultation notes")

@api_router.post("/patients/{patient_id}/consultation-notes", response_model=ConsultationNoteResponse)
async def create_consultation_note(patient_id: str, note_data: ConsultationNoteCreate, admin: dict = Depends(get_current_admin)):
    """Create a consultation note (verified by clinic ownership)"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify patient belongs to admin's clinic
        if not admin.get("is_super_admin") and clinic_id:
            patient_check = supabase.table("patients").select("id").eq("id", patient_id).eq("clinic_id", clinic_id).execute()
            if not patient_check.data:
                raise HTTPException(status_code=404, detail="Patient not found")
        
        note_id = str(uuid.uuid4())
        new_note = {
            "id": note_id,
            "patient_id": patient_id,
            "clinic_id": clinic_id,
            "appointment_id": note_data.appointment_id,
            "date": note_data.date or datetime.now(timezone.utc).date().isoformat(),
            "symptoms": note_data.symptoms,
            "diagnosis": note_data.diagnosis,
            "treatment": note_data.treatment,
            "observations": note_data.observations,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": admin["id"]
        }
        supabase.table("consultation_notes").insert(new_note).execute()
        return new_note
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create consultation note error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create consultation note")

@api_router.put("/consultation-notes/{note_id}", response_model=ConsultationNoteResponse)
async def update_consultation_note(note_id: str, update_data: ConsultationNoteUpdate, admin: dict = Depends(get_current_admin)):
    """Update a consultation note (verified by clinic ownership)"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify note belongs to admin's clinic
        verify_query = supabase.table("consultation_notes").select("id").eq("id", note_id)
        if not admin.get("is_super_admin") and clinic_id:
            verify_query = verify_query.eq("clinic_id", clinic_id)
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Note not found")
        
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        supabase.table("consultation_notes").update(update_dict).eq("id", note_id).execute()
        
        result = supabase.table("consultation_notes").select("*").eq("id", note_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Note not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update consultation note error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update consultation note")

# ============ APPOINTMENTS ENDPOINTS ============

@api_router.get("/appointments", response_model=List[AppointmentResponse])
async def get_appointments(
    date: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """Get appointments with optional filters (filtered by clinic for non-super-admins)"""
    try:
        query = supabase.table("appointments").select("*, patients(name, phone)")
        
        # Filter by clinic if not super admin
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        if date:
            query = query.eq("date", date)
        if status:
            query = query.eq("status", status)
        
        result = query.order("date", desc=True).order("time").execute()
        
        appointments = []
        for apt in result.data:
            patient = apt.pop("patients", {}) or {}
            appointments.append({
                **apt,
                "patient_name": patient.get("name"),
                "patient_phone": patient.get("phone")
            })
        
        return appointments
    except Exception as e:
        logger.error(f"Get appointments error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get appointments")

@api_router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(appointment: AppointmentCreate, admin: dict = Depends(get_current_admin)):
    """Create a new appointment"""
    try:
        clinic_id = admin.get("clinic_id")
        
        # Verify patient belongs to admin's clinic (if not super admin)
        if not admin.get("is_super_admin") and clinic_id:
            patient_check = supabase.table("patients").select("id").eq("id", appointment.patient_id).eq("clinic_id", clinic_id).execute()
            if not patient_check.data:
                raise HTTPException(status_code=403, detail="Patient does not belong to your clinic")
        
        apt_id = str(uuid.uuid4())
        new_apt = {
            "id": apt_id,
            "patient_id": appointment.patient_id,
            "clinic_id": clinic_id,
            "date": appointment.date,
            "time": appointment.time,
            "reason": appointment.reason,
            "status": appointment.status,
            "priority": appointment.priority,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("appointments").insert(new_apt).execute()
        
        # Get patient info
        patient_result = supabase.table("patients").select("name, phone").eq("id", appointment.patient_id).execute()
        patient = patient_result.data[0] if patient_result.data else {}
        
        return {**new_apt, "patient_name": patient.get("name"), "patient_phone": patient.get("phone")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create appointment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create appointment")

@api_router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str, 
    update_data: AppointmentUpdate,
    admin: dict = Depends(get_current_admin)
):
    """Update an appointment (verified by clinic ownership)"""
    try:
        # Verify appointment belongs to admin's clinic
        verify_query = supabase.table("appointments").select("id").eq("id", appointment_id)
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            verify_query = verify_query.eq("clinic_id", admin["clinic_id"])
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        supabase.table("appointments").update(update_dict).eq("id", appointment_id).execute()
        
        result = supabase.table("appointments").select("*, patients(name, phone)").eq("id", appointment_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        apt = result.data[0]
        patient = apt.pop("patients", {}) or {}
        
        return {**apt, "patient_name": patient.get("name"), "patient_phone": patient.get("phone")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update appointment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update appointment")

@api_router.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str, admin: dict = Depends(get_current_admin)):
    """Delete an appointment (verified by clinic ownership)"""
    try:
        # Verify appointment belongs to admin's clinic
        verify_query = supabase.table("appointments").select("id").eq("id", appointment_id)
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            verify_query = verify_query.eq("clinic_id", admin["clinic_id"])
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        supabase.table("appointments").delete().eq("id", appointment_id).execute()
        return {"message": "Appointment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete appointment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete appointment")

# ============ AVAILABILITY ENDPOINTS ============

@api_router.get("/availability", response_model=List[AvailabilitySlot])
async def get_availability(admin: dict = Depends(get_current_admin)):
    """Get availability slots (filtered by clinic for non-super-admins)"""
    try:
        query = supabase.table("availability").select("*")
        
        # Filter by clinic if not super admin
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        result = query.order("day_of_week").order("start_time").execute()
        return result.data
    except Exception as e:
        logger.error(f"Get availability error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get availability")

@api_router.post("/availability", response_model=AvailabilitySlot)
async def create_availability(slot: AvailabilitySlot, admin: dict = Depends(get_current_admin)):
    """Create a new availability slot"""
    try:
        clinic_id = admin.get("clinic_id")
        slot_id = str(uuid.uuid4())
        new_slot = {
            "id": slot_id,
            "clinic_id": clinic_id,
            "day_of_week": slot.day_of_week,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "is_available": slot.is_available
        }
        
        supabase.table("availability").insert(new_slot).execute()
        return {**new_slot}
    except Exception as e:
        logger.error(f"Create availability error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create availability slot")

@api_router.put("/availability/{slot_id}", response_model=AvailabilitySlot)
async def update_availability(
    slot_id: str,
    slot: AvailabilitySlot,
    admin: dict = Depends(get_current_admin)
):
    """Update an availability slot (verified by clinic ownership)"""
    try:
        # Verify slot belongs to admin's clinic
        verify_query = supabase.table("availability").select("id").eq("id", slot_id)
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            verify_query = verify_query.eq("clinic_id", admin["clinic_id"])
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Slot not found")
        
        update_dict = {
            "day_of_week": slot.day_of_week,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "is_available": slot.is_available
        }
        
        supabase.table("availability").update(update_dict).eq("id", slot_id).execute()
        
        result = supabase.table("availability").select("*").eq("id", slot_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Slot not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update availability error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update availability slot")

@api_router.delete("/availability/{slot_id}")
async def delete_availability(slot_id: str, admin: dict = Depends(get_current_admin)):
    """Delete an availability slot (verified by clinic ownership)"""
    try:
        # Verify slot belongs to admin's clinic
        verify_query = supabase.table("availability").select("id").eq("id", slot_id)
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            verify_query = verify_query.eq("clinic_id", admin["clinic_id"])
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Slot not found")
        
        supabase.table("availability").delete().eq("id", slot_id).execute()
        return {"message": "Availability slot deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete availability error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete availability slot")

# ============ CONVERSATIONS ENDPOINTS ============

@api_router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(admin: dict = Depends(get_current_admin)):
    """Get all conversations (filtered by clinic for non-super-admins)"""
    try:
        query = supabase.table("conversations").select("*, patients(name, phone)")
        
        # Filter by clinic if not super admin
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        result = query.order("last_message_at", desc=True).execute()
        
        conversations = []
        for conv in result.data:
            patient = conv.pop("patients", {}) or {}
            conversations.append({
                **conv,
                "patient_name": patient.get("name"),
                "patient_phone": patient.get("phone")
            })
        
        return conversations
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")

@api_router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, admin: dict = Depends(get_current_admin)):
    """Get a specific conversation with messages (verified by clinic ownership)"""
    try:
        query = supabase.table("conversations").select("*, patients(name, phone)").eq("id", conversation_id)
        
        # Verify conversation belongs to admin's clinic
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        conv_result = query.execute()
        
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv = conv_result.data[0]
        patient = conv.pop("patients", {}) or {}
        
        # Get messages
        msg_result = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("timestamp").execute()
        
        return {
            **conv,
            "patient_name": patient.get("name"),
            "patient_phone": patient.get("phone"),
            "messages": msg_result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation")

# ============ ALERTS ENDPOINTS ============

@api_router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[str] = None, 
    show_all: Optional[bool] = False,
    admin: dict = Depends(get_current_admin)
):
    """Get alerts with optional status filter (filtered by clinic for non-super-admins)
    By default only shows today's alerts and pending alerts. Use show_all=true for all alerts.
    """
    try:
        query = supabase.table("alerts").select("*, patients(name, phone)")
        
        # Filter by clinic if not super admin
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            query = query.eq("clinic_id", admin["clinic_id"])
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("created_at", desc=True).execute()
        
        alerts = []
        today_str = datetime.now(timezone.utc).date().isoformat()
        
        for alert in result.data:
            patient = alert.pop("patients", {}) or {}
            alert_data = {
                **alert,
                "patient_name": patient.get("name"),
                "patient_phone": patient.get("phone")
            }
            
            # If not showing all, filter to only today's alerts or pending ones
            if not show_all:
                alert_date = alert.get("created_at", "")[:10]
                is_today = alert_date == today_str
                is_pending = alert.get("status") == "pending"
                if is_today or is_pending:
                    alerts.append(alert_data)
            else:
                alerts.append(alert_data)
        
        return alerts
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")

@api_router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: str, update_data: AlertUpdate, admin: dict = Depends(get_current_admin)):
    """Update alert status (verified by clinic ownership)"""
    try:
        # Verify alert belongs to admin's clinic
        verify_query = supabase.table("alerts").select("id").eq("id", alert_id)
        if not admin.get("is_super_admin") and admin.get("clinic_id"):
            verify_query = verify_query.eq("clinic_id", admin["clinic_id"])
        verify_result = verify_query.execute()
        if not verify_result.data:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        supabase.table("alerts").update({"status": update_data.status}).eq("id", alert_id).execute()
        
        result = supabase.table("alerts").select("*, patients(name, phone)").eq("id", alert_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = result.data[0]
        patient = alert.pop("patients", {}) or {}
        
        return {**alert, "patient_name": patient.get("name"), "patient_phone": patient.get("phone")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update alert error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")

# ============ DASHBOARD ENDPOINTS ============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(admin: dict = Depends(get_current_admin)):
    """Get dashboard statistics (filtered by clinic for non-super-admins)"""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        clinic_id = admin.get("clinic_id")
        is_super = admin.get("is_super_admin")
        
        # Total patients
        patients_query = supabase.table("patients").select("id", count="exact")
        if not is_super and clinic_id:
            patients_query = patients_query.eq("clinic_id", clinic_id)
        patients_result = patients_query.execute()
        total_patients = patients_result.count or 0
        
        # Today's appointments
        today_query = supabase.table("appointments").select("id", count="exact").eq("date", today)
        if not is_super and clinic_id:
            today_query = today_query.eq("clinic_id", clinic_id)
        today_result = today_query.execute()
        total_appointments_today = today_result.count or 0
        
        # Week's appointments
        week_query = supabase.table("appointments").select("id", count="exact").gte("date", week_start)
        if not is_super and clinic_id:
            week_query = week_query.eq("clinic_id", clinic_id)
        week_result = week_query.execute()
        total_appointments_week = week_result.count or 0
        
        # Pending alerts
        alerts_query = supabase.table("alerts").select("id", count="exact").eq("status", "pending")
        if not is_super and clinic_id:
            alerts_query = alerts_query.eq("clinic_id", clinic_id)
        alerts_result = alerts_query.execute()
        pending_alerts = alerts_result.count or 0
        
        # Confirmed appointments
        confirmed_query = supabase.table("appointments").select("id", count="exact").eq("status", "confirmed")
        if not is_super and clinic_id:
            confirmed_query = confirmed_query.eq("clinic_id", clinic_id)
        confirmed_result = confirmed_query.execute()
        confirmed_appointments = confirmed_result.count or 0
        
        # Cancelled appointments
        cancelled_query = supabase.table("appointments").select("id", count="exact").eq("status", "cancelled")
        if not is_super and clinic_id:
            cancelled_query = cancelled_query.eq("clinic_id", clinic_id)
        cancelled_result = cancelled_query.execute()
        cancelled_appointments = cancelled_result.count or 0
        
        return DashboardStats(
            total_patients=total_patients,
            total_appointments_today=total_appointments_today,
            total_appointments_week=total_appointments_week,
            pending_alerts=pending_alerts,
            confirmed_appointments=confirmed_appointments,
            cancelled_appointments=cancelled_appointments
        )
    except Exception as e:
        logger.error(f"Get dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard stats")

# ============ WEBHOOK ENDPOINT FOR MAKE.COM ============

@api_router.post("/webhook/whatsapp")
async def whatsapp_webhook(message: WebhookMessage):
    """
    Webhook endpoint for receiving WhatsApp messages from Make.com
    This processes patient messages and uses AI to respond
    Now with multi-tenant support - identifies clinic by code
    """
    try:
        import re
        
        phone = message.phone
        content = message.message
        original_content = content  # Keep original for logging
        
        # Handle timestamp - convert Unix timestamp to ISO if needed
        raw_timestamp = message.timestamp
        if raw_timestamp:
            # Check if it's a Unix timestamp (numeric string or number)
            try:
                if isinstance(raw_timestamp, str) and raw_timestamp.isdigit():
                    # Unix timestamp in seconds
                    timestamp = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc).isoformat()
                elif isinstance(raw_timestamp, (int, float)):
                    timestamp = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc).isoformat()
                elif 'T' in str(raw_timestamp) or '-' in str(raw_timestamp):
                    # Already ISO format
                    timestamp = raw_timestamp
                else:
                    timestamp = datetime.now(timezone.utc).isoformat()
            except (ValueError, TypeError, OSError):
                timestamp = datetime.now(timezone.utc).isoformat()
        else:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Webhook received: phone={phone}, message_preview={content[:50] if content else 'empty'}...")
        
        # Determine the target clinic
        clinic_id = None
        clinic = None
        is_first_contact = False # Flag to track if this is first message with code/name
        explicit_clinic_matched = False # Flag to track if clinic was explicitly matched in this message
        
        # 0. PRIORITY: Resolve clinic by destination WhatsApp number or instance_id (Evolution API multi-tenant mode)
        if message.to:
            destination_number = message.to.replace('+', '').strip()
            
            # Check if destination string is a UUID (with or without hyphens - our Evolution instances use no-hyphen format)
            import uuid as uuid_module
            resolved_uuid = None
            try:
                # Try parsing directly (works if standard format with hyphens)
                resolved_uuid = str(uuid_module.UUID(message.to))
            except ValueError:
                # Try inserting hyphens for the 32-char no-hyphen format
                clean = message.to.replace('-', '').strip()
                if len(clean) == 32:
                    try:
                        formatted = f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"
                        resolved_uuid = str(uuid_module.UUID(formatted))
                    except ValueError:
                        pass
            
            if resolved_uuid:
                clinic_by_id = supabase.table("clinics").select("*").eq("id", resolved_uuid).eq("is_active", True).execute()
                if clinic_by_id.data:
                    clinic = clinic_by_id.data[0]
                    clinic_id = clinic["id"]
                    is_first_contact = True
                    explicit_clinic_matched = True
                    logger.info(f"Clinic {clinic_id} resolved by instance ID (normalized UUID)")
            
            if not clinic_id:
                # Not a UUID, treat as classic phone number
                clinic_by_number = supabase.table("clinics").select("*").eq("whatsapp_number", destination_number).eq("is_active", True).execute()
                if clinic_by_number.data:
                    clinic = clinic_by_number.data[0]
                    clinic_id = clinic["id"]
                    is_first_contact = True
                    explicit_clinic_matched = True
                    logger.info(f"Clinic {clinic_id} resolved by destination number: {destination_number}")

        
        # 1. Try to extract clinic code from message
        # Try multiple formats to find clinic code
        # Format 1: #CODE (current format)
        # Format 2: Ref:CODE (legacy format)
        # Format 3: (#CODE) (parentheses format)
        clinic_code_match = re.search(r'#([A-Z0-9]{3,10})\b', content.upper())
        if not clinic_code_match:
            # Try Ref: format
            clinic_code_match = re.search(r'Ref:\s*([A-Z0-9]{3,10})\b', content.upper())
        if not clinic_code_match:
            # Try parentheses format like (#CODE)
            clinic_code_match = re.search(r'\(#([A-Z0-9]{3,10})\)', content.upper())
        
        if clinic_code_match and not clinic_id:
            potential_code = clinic_code_match.group(1)
            clinic_result = supabase.table("clinics").select("*").eq("code", potential_code).eq("is_active", True).execute()
            if clinic_result.data:
                clinic = clinic_result.data[0]
                clinic_id = clinic["id"]
                is_first_contact = True
                explicit_clinic_matched = True
                # Remove the code from message for natural conversation (all formats)
                content = re.sub(r'\(#[A-Za-z0-9]{3,10}\)', '', content).strip()
                content = re.sub(r'#[A-Za-z0-9]{3,10}\b', '', content).strip()
                content = re.sub(r'Ref:\s*[A-Za-z0-9]{3,10}\b', '', content, flags=re.IGNORECASE).strip()
                
        # If no code matched, try matching by Doctor's Name (ilike search)
        if not clinic_id and content:
            # Only do this if content is reasonably long (e.g. > 3 chars) to avoid false positives on "hola"
            # It's better to verify if the message actually CONTAINS a doctor's name.
            # Fetch all active clinics to do a simple python-side inclusion search which is more robust
            # for partial matches like "Hola busco a la doctora Martinez"
            clinics_query = supabase.table("clinics").select("id, name, is_active").eq("is_active", True).execute()
            if clinics_query.data:
                for c in clinics_query.data:
                    content_lower = content.lower()
                    doc_name = c["name"].lower()
                    doc_name_clean = doc_name.replace("dr.", "").replace("dra.", "").replace("doctor", "").replace("doctora", "").strip()
                    
                    # If they typed a significant part of the name (e.g. last name like "Arriaga")
                    name_parts = [p.strip() for p in doc_name_clean.split() if len(p.strip()) > 3]
                    
                    match_found = False
                    for part in name_parts:
                        if part in content_lower:
                            match_found = True
                            break
                            
                    if match_found:
                        # Fetch full clinic data
                        clinic_result = supabase.table("clinics").select("*").eq("id", c["id"]).execute()
                        if clinic_result.data:
                            clinic = clinic_result.data[0]
                            clinic_id = clinic["id"]
                            is_first_contact = True
                            explicit_clinic_matched = True
                            logger.info(f"Clinic {clinic_id} assigned by matching doctor name part: {doc_name_clean}")
                            break
        
        # STEP 1: Check if patient exists (ALWAYS do this first)
        patient_result = supabase.table("patients").select("*").eq("phone", phone).execute()
        
        if patient_result.data:
            patient = patient_result.data[0]
            patient_id = patient["id"]
            
            # IMPORTANT: If patient used a NEW clinic code, update their clinic association
            # This handles the case where a patient switches doctors
            if clinic_id and patient.get("clinic_id") and patient.get("clinic_id") != clinic_id:
                # Patient is switching to a new doctor
                logger.info(f"Patient {phone} switching from clinic {patient.get('clinic_id')} to {clinic_id}")
                supabase.table("patients").update({
                    "clinic_id": clinic_id,
                    "last_interaction": timestamp
                }).eq("id", patient_id).execute()
                patient["clinic_id"] = clinic_id
            elif clinic_id and not patient.get("clinic_id"):
                # Patient had no clinic, now has one
                supabase.table("patients").update({
                    "clinic_id": clinic_id,
                    "last_interaction": timestamp
                }).eq("id", patient_id).execute()
                patient["clinic_id"] = clinic_id
            elif not clinic_id and patient.get("clinic_id"):
                # Use patient's existing clinic
                clinic_id = patient["clinic_id"]
                clinic_result = supabase.table("clinics").select("*").eq("id", clinic_id).eq("is_active", True).execute()
                if clinic_result.data:
                    clinic = clinic_result.data[0]
                    logger.info(f"Returning patient {phone} linked to clinic {clinic_id}")
            
            # Update last interaction
            supabase.table("patients").update({
                "last_interaction": timestamp
            }).eq("id", patient_id).execute()
        else:
            # New patient - need clinic_id from the message code
            if not clinic_id:
                # No clinic identified - ask to use a valid link securely
                return {
                    "success": True,
                    "should_reply": True,
                    "response": "¡Hola! Somos el asistente automatizado de MedicAI. 🏥\n\nPara poder agendar tu cita, por favor asegúrate de hacer clic en el enlace de WhatsApp personalizado que te proporcionó tu doctor, o responde a este mensaje con el código único de tu clínica.",
                    "intent": "no_clinic",
                    "phone": phone
                }
            
            # Create new patient with clinic association
            patient_id = str(uuid.uuid4())
            new_patient = {
                "id": patient_id,
                "phone": phone,
                "name": None,
                "clinic_id": clinic_id,
                "created_at": timestamp,
                "last_interaction": timestamp
            }
            supabase.table("patients").insert(new_patient).execute()
            patient = new_patient
            logger.info(f"New patient {phone} created for clinic {clinic_id}")
        
        # If still no clinic after all checks, return error or general
        if not clinic_id or not clinic:
            # Privacy compliant SaaS: Do not list all doctors.
            reception_msg = "¡Hola! Identificamos que tu doctor anterior ya no se encuentra disponible.🏥\n\nPara poder continuar, por favor responde a este mensaje con el código único de tu nuevo especialista, o utiliza su enlace personalizado."
            
            return {
                "success": True,
                "should_reply": True,
                "response": reception_msg,
                "intent": "no_clinic",
                "phone": phone
            }
        
        # Handle first contact welcome message (after patient is created/found)
        if is_first_contact and not content:
            # Patient just clicked the link, send personalized welcome
            welcome = clinic.get("welcome_message") or f"¡Hola! Soy el asistente del {clinic['name']}. ¿En qué puedo ayudarte hoy?"
            
            # Create/update conversation for tracking
            conv_result = supabase.table("conversations").select("*").eq("patient_id", patient_id).eq("status", "active").execute()
            if not conv_result.data:
                conv_id = str(uuid.uuid4())
                new_conv = {
                    "id": conv_id,
                    "patient_id": patient_id,
                    "clinic_id": clinic_id,
                    "started_at": timestamp,
                    "last_message_at": timestamp,
                    "status": "active"
                }
                supabase.table("conversations").insert(new_conv).execute()
            else:
                conv_id = conv_result.data[0]["id"]
            
            # Save welcome message (intent as None since 'greeting' may not be in DB constraint)
            welcome_msg_id = str(uuid.uuid4())
            welcome_message = {
                "id": welcome_msg_id,
                "conversation_id": conv_id,
                "sender": "ai",
                "content": welcome,
                "timestamp": timestamp,
                "intent": None
            }
            supabase.table("messages").insert(welcome_message).execute()
            
            return {
                "success": True,
                "should_reply": True,
                "response": welcome,
                "intent": "greeting",
                "clinic_id": clinic_id,
                "patient_id": patient_id,
                "phone": phone
            }
        
        # If content is empty but not first contact, set a default
        if not content:
            content = "Hola"
        
        # Get or create conversation
        conv_result = supabase.table("conversations").select("*").eq("patient_id", patient_id).eq("status", "active").execute()
        
        conv_id = None
        has_active_conversation = False
        
        if conv_result.data:
            conversation = conv_result.data[0]
            
            # Check for stale conversation (> 12 hours old)
            from datetime import datetime as dt_class, timezone as tz_class
            try:
                last_msg_time = dt_class.fromisoformat(conversation["last_message_at"].replace('Z', '+00:00'))
                is_stale = (dt_class.now(tz_class.utc) - last_msg_time).total_seconds() > (12 * 3600)
            except Exception:
                is_stale = False
                
            if is_stale or conversation.get("clinic_id") != clinic_id:
                # Close stale or mismatched conversation
                logger.info(f"Closing conversation for {phone} (stale={is_stale}, switched_clinic={conversation.get('clinic_id') != clinic_id})")
                supabase.table("conversations").update({"status": "closed"}).eq("id", conversation["id"]).execute()
            else:
                conv_id = conversation["id"]
                has_active_conversation = True
        
        if not conv_id:
            conv_id = str(uuid.uuid4())
            new_conv = {
                "id": conv_id,
                "patient_id": patient_id,
                "clinic_id": clinic_id,
                "started_at": timestamp,
                "last_message_at": timestamp,
                "status": "active"
            }
            supabase.table("conversations").insert(new_conv).execute()
        
        # ═══════════════════════════════════════════════════════════════
        # INTERCEPT RETURNING PATIENTS WITHOUT EXPLICIT DOCTOR
        # Only fire ONCE per new conversation (check if routing prompt was already sent)
        # ═══════════════════════════════════════════════════════════════
        if patient_result.data and not has_active_conversation and not explicit_clinic_matched and not is_first_contact:
            # Check if we already sent a routing prompt in this conversation
            existing_msgs = supabase.table("messages").select("intent").eq("conversation_id", conv_id).eq("intent", "routing_prompt").limit(1).execute()
            
            if not existing_msgs.data:
                doctor_name = clinic.get('name', 'el doctor')
                routing_prompt = f"¡Hola de nuevo! 👋\n\nVeo que tu última consulta fue con {doctor_name}. ¿Deseas agendar con este mismo especialista, o buscas a otro doctor?\n\n_(Si buscas a otro, por favor escríbeme su nombre o envíame su enlace)_"
                
                # Save patient message
                patient_msg_id = str(uuid.uuid4())
                supabase.table("messages").insert({
                    "id": patient_msg_id, "conversation_id": conv_id,
                    "sender": "patient", "content": content,
                    "timestamp": timestamp, "intent": None
                }).execute()
                
                # Save AI routing prompt
                supabase.table("messages").insert({
                    "id": str(uuid.uuid4()), "conversation_id": conv_id,
                    "sender": "ai", "content": routing_prompt,
                    "timestamp": timestamp, "intent": "routing_prompt"
                }).execute()
                
                return {
                    "success": True, "should_reply": True, "response": routing_prompt,
                    "intent": "routing_prompt", "clinic_id": clinic_id,
                    "patient_id": patient_id, "phone": phone
                }
            # If routing prompt was already sent, fall through to normal AI processing
        
        # Save patient message FIRST
        patient_msg_id = str(uuid.uuid4())
        patient_message = {
            "id": patient_msg_id,
            "conversation_id": conv_id,
            "sender": "patient",
            "content": content,
            "timestamp": timestamp,
            "intent": None
        }
        supabase.table("messages").insert(patient_message).execute()
        
        # ═══════════════════════════════════════════════════════════════
        # MULTI-MESSAGE DEBOUNCE LOGIC
        # Wait a few seconds to let any immediate subsequent messages arrive
        # ═══════════════════════════════════════════════════════════════
        import asyncio
        await asyncio.sleep(4)
        
        # Check if a newer message from the patient arrived for this conversation
        latest_msg_query = supabase.table("messages").select("id").eq("conversation_id", conv_id).eq("sender", "patient").order("timestamp", desc=True).limit(1).execute()
        
        if latest_msg_query.data and latest_msg_query.data[0]["id"] != patient_msg_id:
            logger.info(f"Debounced: Newer message detected for {phone}. Skipping AI generation for this chunk.")
            return {
                "success": True,
                "should_reply": False,
                "response": "",
                "intent": "debounced",
                "clinic_id": clinic_id,
                "patient_id": patient_id,
                "phone": phone
            }
            
        # Get FULL conversation history INCLUDING all the newest debounced messages
        history_result = supabase.table("messages").select("*").eq("conversation_id", conv_id).order("timestamp").limit(30).execute()
        
        # Get availability for context - filtered by clinic
        availability_result = supabase.table("availability").select("*").eq("clinic_id", clinic_id).eq("is_available", True).order("day_of_week").execute()
        availability_info = availability_result.data if availability_result.data else []
        
        # If no clinic-specific availability, get general availability
        if not availability_info:
            availability_result = supabase.table("availability").select("*").is_("clinic_id", "null").eq("is_available", True).order("day_of_week").execute()
            availability_info = availability_result.data if availability_result.data else []
        
        days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        
        # Build conversation history with turn numbers for better AI context
        conversation_history = ""
        if history_result.data:
            turn = 1
            for msg in history_result.data[-15:]:  # Last 15 messages for context
                role = "PACIENTE" if msg["sender"] == "patient" else "ASISTENTE"
                conversation_history += f"[{turn}] {role}: {msg['content']}\n"
                turn += 1
        
        # Get today's date for appointment context - FORCE LOCAL TIMEZONE (UTC-6)
        from datetime import datetime as dt_class, timedelta
        
        # Hardcode America/Mexico_City offset for reliability
        local_time_now = dt_class.now(timezone.utc) + timedelta(hours=-6)
        today = local_time_now.date()
        today_str = today.strftime("%Y-%m-%d")
        
        # Python weekday(): Monday=0, Sunday=6. Our array: Domingo=0, Lunes=1...Sábado=6
        python_weekday = today.weekday()  # 0=Monday, 1=Tuesday... 6=Sunday
        # Convert to our format: Sunday=0, Monday=1... Saturday=6
        our_day_index = (python_weekday + 1) % 7
        day_name = days[our_day_index]
        
        # Get current time for more context
        current_time = local_time_now.strftime("%H:%M")
        
        # Calculate next 7 days with their day names - MORE EXPLICIT
        next_days_info = []
        for i in range(7):
            d = today + timedelta(days=i)
            python_wd = d.weekday()
            day_idx = (python_wd + 1) % 7
            day_label = "HOY" if i == 0 else ("MAÑANA" if i == 1 else days[day_idx])
            next_days_info.append({
                "date": d.strftime('%Y-%m-%d'),
                "day_name": days[day_idx],
                "day_label": day_label,
                "day_num": day_idx
            })
        
        # Build REAL available slots for next 7 days - WITH EXPLICIT LABELS
        available_slots_text = "CALENDARIO (próximos 7 días):\n"
        available_slots_text += f"Hoy es {day_name.upper()} {today_str}, hora actual: {current_time}\n\n"
        for day_info in next_days_info:
            day_availability = [slot for slot in availability_info if slot.get('day_of_week') == day_info['day_num']]
            if day_availability:
                # Strip seconds from times (09:00:00 -> 09:00)
                slots_str = ", ".join([f"{s['start_time'][:5]}-{s['end_time'][:5]}" for s in day_availability])
                available_slots_text += f"{day_info['date']} {day_info['day_label']} ({day_info['day_name']}): {slots_str}\n"
            else:
                available_slots_text += f"{day_info['date']} {day_info['day_label']} ({day_info['day_name']}): CERRADO\n"
        
        if not availability_info:
            available_slots_text = "HORARIOS: No hay horarios configurados. Solicitar al paciente que llame al consultorio.\n"
        
        # Doctor/Clinic info
        doctor_name = clinic.get('name', 'el doctor')
        clinic_name = clinic.get('clinic_name', 'la clínica')
        specialty = clinic.get('specialty', '')
        consultation_price = clinic.get('consultation_price')
        consultation_currency = clinic.get('consultation_currency', 'MXN')
        
        price_info = f"${consultation_price:.0f} {consultation_currency}" if consultation_price else "Consultar directamente"
        
        # Check ALL existing appointments for this patient (confirmed or pending)
        existing_apts_query = supabase.table("appointments").select("*").eq("patient_id", patient_id).eq("clinic_id", clinic_id).gte("date", today_str).in_("status", ["confirmed", "pending"]).order("date").execute()
        existing_appointments = existing_apts_query.data if existing_apts_query.data else []
        
        # Build existing appointments info
        existing_apts_info = ""
        if existing_appointments:
            existing_apts_info = "\n\n⚠️ CITAS EXISTENTES DEL PACIENTE (VERIFICAR ANTES DE CUALQUIER ACCIÓN):\n"
            for apt in existing_appointments:
                existing_apts_info += f"- ID: {apt['id'][:8]} | Fecha: {apt['date']} | Hora: {apt['time']} | Motivo: {apt.get('reason', 'N/A')} | Estado: {apt['status'].upper()}\n"
            existing_apts_info += "\nSI EL PACIENTE QUIERE AGENDAR: Primero informar que YA tiene cita y preguntar si desea mantener, cancelar o reagendar."
        
        # ═══════════════════════════════════════════════════════════════
        # SYSTEM INSTRUCTION (rules - sent separately from conversation)
        # ═══════════════════════════════════════════════════════════════
        system_instruction = f"""Eres la secretaria médica virtual del consultorio del {doctor_name}. Tu ÚNICA función es gestionar citas.

DATOS FIJOS:
- Doctor: {doctor_name}
- Especialidad: {specialty or 'Medicina General'}
- Precio: {price_info}

Paciente actual:
- Nombre: {patient.get('name') or '[NO REGISTRADO - pedir nombre ANTES de agendar]'}
- Teléfono: {phone}
{existing_apts_info}

{available_slots_text}

REGLAS CRÍTICAS:
1. SOLO ofrece horarios que aparecen en el CALENDARIO arriba. NUNCA inventes.
2. Usa formato 24h para las horas (3 PM = 15:00). En el tag [CITA_CONFIRMADA] SIEMPRE usa HH:MM en 24h.
3. Si el paciente dice "a las 3" sin AM/PM y el horario del doctor es diurno, asume PM (15:00).
4. Si el paciente dice "mañana", eso es {next_days_info[1]['date']} ({next_days_info[1]['day_name']}). NO confundas días.
5. NUNCA confirmes una cita sin que el paciente diga explícitamente "sí", "confirmo", "dale" o equivalente.
6. Si el paciente YA tiene cita activa, infórmale primero y pregunta si quiere mantener, cancelar o reagendar.
7. NUNCA repitas preguntas que ya fueron respondidas en el historial de conversación.
8. Si el paciente quiere atenderse con OTRO doctor, responde: "Entendido. Por favor escríbeme el nombre del doctor o envíame su enlace de WhatsApp."

FLUJO PARA AGENDAR:
1. Pedir nombre (si no lo tienes) → [NOMBRE: nombre_completo]
2. Preguntar fecha, hora y motivo
3. Proponer: "Tengo disponible el [fecha] a las [HH:MM]. ¿Confirma?"
4. SOLO cuando el paciente confirme, emitir:
[CITA_CONFIRMADA]
Fecha: YYYY-MM-DD
Hora: HH:MM
Motivo: motivo
Nombre: nombre
[/CITA_CONFIRMADA]

PARA CANCELAR:
[CITA_CANCELADA]
ID: primeros_8_caracteres_del_id
[/CITA_CANCELADA]

ESTILO: Profesional, cortés, directo. Máximo 2-3 oraciones por respuesta. Sin emojis excesivos."""

        # ═══════════════════════════════════════════════════════════════
        # CONVERSATION CONTENTS (sent as user/model turns to Gemini)
        # ═══════════════════════════════════════════════════════════════
        gemini_contents = []
        if history_result.data:
            for msg in history_result.data[-15:]:
                role = "user" if msg["sender"] == "patient" else "model"
                gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        # If conversation is empty or last message isn't the current one, add it
        if not gemini_contents or gemini_contents[-1]["parts"][0]["text"] != content:
            gemini_contents.append({"role": "user", "parts": [{"text": content}]})
        
        # Ensure conversation starts with user message (Gemini requirement)
        if gemini_contents and gemini_contents[0]["role"] != "user":
            gemini_contents = gemini_contents[1:]

        # Process with Google Gemini - using proper system_instruction separation
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            
            import asyncio
            
            def call_gemini():
                return client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=gemini_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3,
                    ),
                )
                
            response = await asyncio.to_thread(call_gemini)
            
            ai_response = response.text
            logger.info("Gemini response generated successfully")
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            ai_response = "Lo siento, mi sistema está demorando en responder. Por favor intente nuevamente en unos minutos."
        
        # Detect and extract patient name if provided
        import re
        name_match = re.search(r'\[NOMBRE:\s*([^\]]+)\]', ai_response)
        if name_match and not patient.get('name'):
            new_name = name_match.group(1).strip()
            supabase.table("patients").update({"name": new_name}).eq("id", patient_id).execute()
            patient['name'] = new_name
            ai_response = re.sub(r'\[NOMBRE:[^\]]+\]\s*', '', ai_response)
        
        # ═══════════════════════════════════════════════════════════════
        # HANDLE APPOINTMENT CANCELLATION
        # ═══════════════════════════════════════════════════════════════
        cancel_match = re.search(r'\[CITA_CANCELADA\](.*?)\[/CITA_CANCELADA\]', ai_response, re.DOTALL)
        if cancel_match:
            cancel_text = cancel_match.group(1)
            id_match = re.search(r'ID:\s*([a-f0-9-]+)', cancel_text, re.IGNORECASE)
            
            if id_match:
                apt_id_prefix = id_match.group(1).strip()
                # Find appointment by ID prefix
                for apt in existing_appointments:
                    if apt['id'].startswith(apt_id_prefix):
                        # Cancel the appointment
                        supabase.table("appointments").update({"status": "cancelled"}).eq("id", apt['id']).execute()
                        logger.info(f"Appointment cancelled: {apt['id']} for patient {patient_id}")
                        break
            else:
                # If no ID provided, cancel the most recent confirmed appointment
                if existing_appointments:
                    apt_to_cancel = existing_appointments[0]
                    supabase.table("appointments").update({"status": "cancelled"}).eq("id", apt_to_cancel['id']).execute()
                    logger.info(f"Appointment cancelled (no ID): {apt_to_cancel['id']} for patient {patient_id}")
            
            # Clean the response
            ai_response = re.sub(r'\[CITA_CANCELADA\].*?\[/CITA_CANCELADA\]\s*', '', ai_response, flags=re.DOTALL)
        
        # ═══════════════════════════════════════════════════════════════
        # HANDLE APPOINTMENT CREATION
        # ═══════════════════════════════════════════════════════════════
        appointment_created = False
        appointment_match = re.search(r'\[CITA_CONFIRMADA\](.*?)\[/CITA_CONFIRMADA\]', ai_response, re.DOTALL)
        
        if appointment_match:
            apt_text = appointment_match.group(1)
            fecha_match = re.search(r'Fecha:\s*(\d{4}-\d{2}-\d{2})', apt_text)
            hora_match = re.search(r'Hora:\s*(\d{1,2}:\d{2})(?:\s*(am|pm|a\.m\.|p\.m\.))?', apt_text, re.IGNORECASE)
            motivo_match = re.search(r'Motivo:\s*(.+?)(?:\n|$)', apt_text)
            
            if fecha_match and hora_match:
                new_date = fecha_match.group(1)
                # Parse hour and normalize PM
                time_str = hora_match.group(1)
                ampm = hora_match.group(2)
                hour, minute = map(int, time_str.split(':'))
                if ampm:
                    ampm_clean = ampm.lower().replace('.', '')
                    if ampm_clean == 'pm' and hour < 12:
                        hour += 12
                    elif ampm_clean == 'am' and hour == 12:
                        hour = 0
                else:
                    # Smart AM/PM inference based on clinic hours
                    # If patient says "a las 3", AI might generate "03:00" (AM). 
                    # If clinic is open 09:00-18:00, 3 AM is invalid, so assume they meant 3 PM (15:00)
                    if hour > 0 and hour <= 11:
                        # Determine day of week for new_date
                        try:
                            from datetime import datetime as dt_class
                            apt_date_obj = dt_class.strptime(new_date, "%Y-%m-%d").date()
                            # Python wd: 0=Mon, 6=Sun -> Our wd: 0=Sun, 1=Mon...
                            wd_idx = (apt_date_obj.weekday() + 1) % 7
                            
                            # Get slots for that day
                            day_slots = [s for s in availability_info if s.get('day_of_week') == wd_idx]
                            
                            # Check if the AM time is valid in any slot
                            am_time_fmt = f"{hour:02d}:{minute:02d}:00"
                            am_is_valid = False
                            for s in day_slots:
                                if s['start_time'] <= am_time_fmt <= s['end_time']:
                                    am_is_valid = True
                                    break
                            
                            if not am_is_valid:
                                # Check if PM time (hour+12) WOULD be valid
                                pm_hour = hour + 12
                                pm_time_fmt = f"{pm_hour:02d}:{minute:02d}:00"
                                pm_is_valid = False
                                for s in day_slots:
                                    if s['start_time'] <= pm_time_fmt <= s['end_time']:
                                        pm_is_valid = True
                                        break
                                
                                # If PM is valid but AM is not, autocorrect to PM!
                                if pm_is_valid:
                                    hour += 12
                                    logger.info(f"Auto-corrected 0{hour-12}:00 to {hour}:00 based on clinic schedule")
                        except Exception as e:
                            logger.error(f"Error autocorrecting AM/PM: {e}")
                            
                new_time = f"{hour:02d}:{minute:02d}"
                new_reason = motivo_match.group(1).strip() if motivo_match else "Consulta general"
                
                # CHECK FOR DUPLICATES: Verify no existing appointment at same date/time
                duplicate_check = supabase.table("appointments").select("id").eq("patient_id", patient_id).eq("clinic_id", clinic_id).eq("date", new_date).eq("time", new_time).eq("status", "confirmed").execute()
                
                if duplicate_check.data:
                    logger.warning(f"Duplicate appointment prevented for patient {patient_id} at {new_date} {new_time}")
                    ai_response = f"Ya tiene una cita confirmada para el {new_date} a las {new_time}. ¿Desea mantenerla, cancelarla o elegir otro horario?"
                else:
                    apt_id = str(uuid.uuid4())
                    new_appointment = {
                        "id": apt_id,
                        "patient_id": patient_id,
                        "clinic_id": clinic_id,
                        "date": new_date,
                        "time": new_time,
                        "reason": new_reason[:100],
                        "status": "confirmed",
                        "priority": "normal",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    supabase.table("appointments").insert(new_appointment).execute()
                    appointment_created = True
                    logger.info(f"Appointment created: {apt_id} for patient {patient_id} at clinic {clinic_id}")
                    
                    # Send real-time notification via WebSocket
                    await manager.broadcast({
                        "type": "new_appointment",
                        "clinic_id": clinic_id,
                        "data": {
                            "id": apt_id,
                            "patient_name": patient.get('name') or 'Paciente nuevo',
                            "patient_phone": phone,
                            "date": new_date,
                            "time": new_time,
                            "reason": new_reason,
                            "doctor_name": clinic.get('name', 'Doctor')
                        }
                    })
            
            # Clean the response to remove the markup
            ai_response = re.sub(r'\[CITA_CONFIRMADA\].*?\[/CITA_CONFIRMADA\]\s*', '', ai_response, flags=re.DOTALL)
        
        # NOTE: Smart Confirmation Detector was REMOVED.
        # All appointment creation must go through the [CITA_CONFIRMADA] tag from the AI.
        # This eliminates ghost appointments caused by false-positive confirmations.
        
        # Detect intent from AI response and original message
        intent = "general"
        content_lower = content.lower()
        
        if "[URGENCIA]" in ai_response or any(word in content_lower for word in ["urgente", "urgencia", "emergencia", "grave", "dolor fuerte", "sangrado"]):
            intent = "urgency"
            ai_response = ai_response.replace("[URGENCIA]", "").strip()
            # Create alert for urgent cases
            alert_id = str(uuid.uuid4())
            alert = {
                "id": alert_id,
                "patient_id": patient_id,
                "clinic_id": clinic_id,
                "message": content,
                "priority": "high",
                "status": "pending",
                "created_at": timestamp
            }
            supabase.table("alerts").insert(alert).execute()
            
        elif appointment_created or any(word in content_lower for word in ["cita", "agendar", "consulta", "turno", "hora"]):
            intent = "appointment"
        elif any(word in content_lower for word in ["precio", "costo", "cuanto", "valor", "tarifa"]):
            intent = "pricing"
        
        # Update patient message with intent
        supabase.table("messages").update({"intent": intent}).eq("id", patient_msg_id).execute()
        
        # Save AI response
        ai_msg_id = str(uuid.uuid4())
        ai_message = {
            "id": ai_msg_id,
            "conversation_id": conv_id,
            "sender": "ai",
            "content": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": None
        }
        supabase.table("messages").insert(ai_message).execute()
        
        # Update conversation last_message_at
        supabase.table("conversations").update({
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", conv_id).execute()
        
        return {
            "success": True,
            "should_reply": True,
            "response": ai_response,
            "intent": intent,
            "patient_id": patient_id,
            "conversation_id": conv_id,
            "phone": phone
        }
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

# ============ DIRECT EVOLUTION API (UNOFFICIAL WHATSAPP WEBSOCKET) ============

EVOLUTION_API_URL = os.environ.get('EVOLUTION_API_URL', 'http://localhost:8080')
EVOLUTION_GLOBAL_API_KEY = os.environ.get('EVOLUTION_GLOBAL_API_KEY', 'your-global-api-key')

async def send_whatsapp_reply(instance_id: str, to: str, message_text: str):
    """Send a WhatsApp reply via Evolution API"""
    if not EVOLUTION_GLOBAL_API_KEY:
        logger.warning("Evolution API Key not set - cannot send reply")
        return None
    
    url = f"{EVOLUTION_API_URL.rstrip('/')}/message/sendText/{instance_id}"
    headers = {
        "apikey": EVOLUTION_GLOBAL_API_KEY,
        "Content-Type": "application/json"
    }

    # Ensure format is correct for Evolution API (needs just country code + number, e.g. 5215512345678)
    to_phone = to.replace('whatsapp:', '').replace('+', '').strip()
    
    payload = {
        "number": to_phone,
        "options": {
            "delay": 1200,
            "presence": "composing"
        },
        "textMessage": {
            "text": message_text
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (200, 201):
                logger.info(f"WhatsApp reply sent to {to} via Evolution API instance {instance_id}")
                return response.json()
            else:
                logger.error(f"Evolution API send failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Evolution API send error: {e}")
        return None

@api_router.post("/webhook/evolution")
async def evolution_webhook_receive(request: Request):
    """
    Receive raw webhooks from Evolution API.
    Evolution API sends JSON with 'event', 'instance' and 'data' fields.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Evolution webhook JSON parse error: {e}")
        return {"status": "ok"}
    
    event_type = body.get("event")
    
    # Log ALL incoming webhooks for debugging
    logger.info(f"Evolution webhook received: event={event_type}, instance={body.get('instance', 'N/A')}, keys={list(body.keys())}")
    
    # We only care about new incoming messages
    if event_type != "messages.upsert":
        return {"status": "ok"}
        
    instance_id = body.get("instance", "")
    message_data = body.get("data", {}).get("message", {})
    key_data = body.get("data", {}).get("key", {})
    
    # Ignore messages sent by the bot itself
    if key_data.get("fromMe", False):
        return {"status": "ok"}
        
    from_phone_raw = key_data.get("remoteJid", "")
    from_phone = from_phone_raw.split("@")[0].strip() if "@" in from_phone_raw else from_phone_raw
    
    # Extract text (could be in conversation or extendedTextMessage)
    text_body = message_data.get("conversation") or message_data.get("extendedTextMessage", {}).get("text") or ""
    
    if not text_body or not from_phone or not instance_id:
        return {"status": "ok"}
        
    logger.info(f"Evolution webhook: from={from_phone}, instance={instance_id}, msg={text_body[:50]}")
    
    try:
        # Reuse existing webhook logic. Note: 'to' becomes the instance_id so it can be uniquely mapped to a clinic
        webhook_message = WebhookMessage(
            phone=from_phone,
            message=text_body,
            to=instance_id  # We map instance_id to 'to' so whatsapp_webhook can resolve the clinic
        )
        result = await whatsapp_webhook(webhook_message)
        
        # Send reply directly via Evolution API
        if result.get("should_reply") and result.get("response"):
            # Use instance_id as the sender
            await send_whatsapp_reply(
                instance_id=instance_id,
                to=from_phone,
                message_text=result["response"]
            )
    except Exception as e:
        logger.error(f"Error processing Evolution webhook message: {e}")
    
    return {"status": "ok"}

@api_router.get("/webhook/evolution/status")
async def evolution_webhook_status(admin: dict = Depends(require_super_admin)):
    """Check Evolution API integration status"""
    try:
        has_api_url = bool(EVOLUTION_API_URL)
        has_api_key = bool(EVOLUTION_GLOBAL_API_KEY)
        
        clinics_result = supabase.table("clinics").select(
            "id, code, name, is_active"
        ).eq("is_active", True).execute()
        
        return {
            "integration": "evolution",
            "environment": {
                "EVOLUTION_API_URL": "✅ configured" if has_api_url else "❌ missing",
                "EVOLUTION_GLOBAL_API_KEY": "✅ configured" if has_api_key else "❌ missing",
            },
            "webhook_url": "/api/webhook/evolution",
            "clinics": len(clinics_result.data or [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/whatsapp/instance/create")
async def create_whatsapp_instance(clinic_id: str, request: Request, admin: dict = Depends(require_super_admin)):
    """Create a new WhatsApp instance in Evolution API for a clinic and return QR"""
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
        
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/create"
    headers = {
        "apikey": EVOLUTION_GLOBAL_API_KEY,
        "Content-Type": "application/json"
    }
    
    # We construct the webhook url assuming the current host domain
    host_url = str(request.base_url).rstrip("/")
    if "localhost" in host_url or "127.0.0.1" in host_url:
        webhook_target = "https://medicai-backend.onrender.com/api/webhook/evolution" # Fallback for local
    else:
        webhook_target = f"{host_url}/api/webhook/evolution"
        
    # Use clinic_id as the instance name for uniqueness
    instance_id = clinic_id.replace("-", "")
    payload = {
        "instanceName": instance_id,
        "token": instance_id,  # Custom token for the instance
        "qrcode": True       # Request base64 QR code response
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            data = response.json()
            
            # Immediately attach Webhook to this instance
            webhook_url = f"{EVOLUTION_API_URL.rstrip('/')}/webhook/set/{instance_id}"
            webhook_payload = {
                "webhook": {
                    "enabled": True,
                    "url": webhook_target,
                    "byEvents": False,
                    "base64": False,
                    "events": ["MESSAGES_UPSERT"]
                }
            }
            await client.post(webhook_url, json=webhook_payload, headers=headers)
            
            return data
    except Exception as e:
        logger.error(f"Error creating Evolution instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/whatsapp/instance/delete")
async def delete_whatsapp_instance(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Delete a WhatsApp instance"""
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
        
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/logout/{clinic_id}"
    headers = {
        "apikey": EVOLUTION_GLOBAL_API_KEY,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First logout to destroy session in DB
            await client.delete(url, headers=headers)
            
            # Then delete the instance entirely
            del_url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/delete/{clinic_id}"
            response = await client.delete(del_url, headers=headers)
            
            return response.json()
    except Exception as e:
        logger.error(f"Error deleting Evolution instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@api_router.get("/whatsapp/instance/qr")
async def get_whatsapp_qr(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Get connection state or QR code for clinic instance"""
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
        
    instance_id = clinic_id.replace("-", "")
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/connect/{instance_id}"
    headers = {
        "apikey": EVOLUTION_GLOBAL_API_KEY,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 404 or response.status_code >= 500:
                return {"status": "not_found"}
            return response.json()
    except Exception as e:
        logger.error(f"Error getting Evolution QR: {e}")
        return {"status": "not_found"}

@api_router.get("/whatsapp/instance/status")
async def get_whatsapp_status(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Get connection status for clinic instance"""
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
        
    instance_id = clinic_id.replace("-", "")
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/connectionState/{instance_id}"
    headers = {
        "apikey": EVOLUTION_GLOBAL_API_KEY,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 404 or response.status_code >= 500:
                return {"instance": {"state": "not_found"}}
            return response.json()
    except Exception as e:
        logger.error(f"Error getting Evolution status: {e}")
        return {"instance": {"state": "not_found"}}


# ============ DOCTOR SELF-SERVICE WHATSAPP QR ============

@api_router.post("/whatsapp/my-instance/create")
async def create_my_whatsapp_instance(request: Request, admin: dict = Depends(get_current_admin)):
    """Doctor creates their own WhatsApp instance"""
    clinic_id = admin.get("clinic_id")
    if not clinic_id:
        raise HTTPException(status_code=400, detail="No clinic associated with this account")
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
    
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/create"
    headers = {"apikey": EVOLUTION_GLOBAL_API_KEY, "Content-Type": "application/json"}
    
    host_url = str(request.base_url).rstrip("/")
    if "localhost" in host_url or "127.0.0.1" in host_url:
        webhook_target = "https://medicai-backend.onrender.com/api/webhook/evolution"
    else:
        webhook_target = f"{host_url}/api/webhook/evolution"
    
    instance_id = clinic_id.replace("-", "")
    headers = {"apikey": EVOLUTION_GLOBAL_API_KEY, "Content-Type": "application/json"}
    
    host_url = str(request.base_url).rstrip("/")
    if "localhost" in host_url or "127.0.0.1" in host_url:
        webhook_target = "https://medicai-backend.onrender.com/api/webhook/evolution"
    else:
        webhook_target = f"{host_url}/api/webhook/evolution"
    
    base_url = EVOLUTION_API_URL.rstrip('/')
    
    # ── STEP 1: Auto-cleanup any existing ghost instance ──────────────────────
    # This prevents the "too many devices" problem if WhatsApp disconnects.
    # We silently try to logout + delete; if it fails we ignore and proceed.
    try:
        async with httpx.AsyncClient(timeout=15.0) as cleanup_client:
            await cleanup_client.delete(f"{base_url}/instance/logout/{instance_id}", headers=headers)
            await cleanup_client.delete(f"{base_url}/instance/delete/{instance_id}", headers=headers)
            logger.info(f"Pre-create cleanup completed for instance {instance_id}")
    except Exception as e:
        logger.warning(f"Pre-create cleanup failed (non-fatal): {e}")
    
    # ── STEP 2: Create fresh instance ─────────────────────────────────────────
    url = f"{base_url}/instance/create"
    payload = {
        "instanceName": instance_id, 
        "token": instance_id, 
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            # Log the full response for debugging
            logger.info(f"Evolution create response: status={response.status_code} body={response.text[:500]}")
            
            if response.status_code == 401:
                logger.error(f"Evolution API key rejected (401). Check EVOLUTION_GLOBAL_API_KEY env var.")
                raise HTTPException(status_code=500, detail="API Key de WhatsApp rechazada. Contacta al administrador.")
            if response.status_code >= 500:
                raise HTTPException(status_code=503, detail="Servidor de WhatsApp iniciando. Por favor, intenta de nuevo en 1 minuto.")
            if response.status_code >= 400:
                logger.error(f"Evolution create error: {response.status_code} - {response.text[:300]}")
                # Parse evolution error message to show in UI
                error_detail = response.text
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict) and error_json.get("message"):
                        error_detail = error_json["message"]
                    elif isinstance(error_json, dict) and error_json.get("error"):
                        error_detail = error_json["error"]
                    elif isinstance(error_json, list) and len(error_json) > 0 and isinstance(error_json[0], str):
                        error_detail = error_json[0]
                except:
                    pass
                raise HTTPException(status_code=500, detail=f"Evolution API dice: {error_detail[:100]}")
            
            try:
                data = response.json()
            except:
                data = {"error": response.text}
            
            # Only set webhook if instance was actually created
            if data and not data.get("error"):
                webhook_url = f"{EVOLUTION_API_URL.rstrip('/')}/webhook/set/{instance_id}"
                webhook_payload = {
                    "webhook": {
                        "enabled": True,
                        "url": webhook_target,
                        "byEvents": False,
                        "base64": False,
                        "events": [
                            "MESSAGES_UPSERT",
                            "MESSAGES_UPDATE",
                            "CONNECTION_UPDATE"
                        ]
                    }
                }
                wh_resp = await client.post(webhook_url, json=webhook_payload, headers=headers)
                logger.info(f"Webhook set response: {wh_resp.status_code} - {wh_resp.text[:200]}")
            
            return data
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Network error Evolution API: {e}")
        raise HTTPException(status_code=503, detail="Servidor de WhatsApp iniciando. Por favor, intenta de nuevo en 1 minuto.")
    except Exception as e:
        logger.error(f"Error creating Evolution instance (doctor): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/whatsapp/my-instance/qr")
async def get_my_whatsapp_qr(admin: dict = Depends(get_current_admin)):
    """Doctor gets their QR code"""
    clinic_id = admin.get("clinic_id")
    if not clinic_id:
        raise HTTPException(status_code=400, detail="No clinic associated")
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
    
    instance_id = clinic_id.replace("-", "")
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/connect/{instance_id}"
    headers = {"apikey": EVOLUTION_GLOBAL_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 500:
                return {"status": "offline"}
            if response.status_code == 404:
                return {"status": "not_found"}
            return response.json()
    except httpx.RequestError:
        return {"status": "offline"}
    except Exception as e:
        return {"status": "not_found"}

@api_router.get("/whatsapp/my-instance/status")
async def get_my_whatsapp_status(admin: dict = Depends(get_current_admin)):
    """Doctor checks their WhatsApp connection status"""
    clinic_id = admin.get("clinic_id")
    if not clinic_id:
        raise HTTPException(status_code=400, detail="No clinic associated")
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
    
    instance_id = clinic_id.replace("-", "")
    url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/connectionState/{instance_id}"
    headers = {"apikey": EVOLUTION_GLOBAL_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 500:
                return {"instance": {"state": "offline"}}
            if response.status_code == 404:
                return {"instance": {"state": "not_found"}}
            return response.json()
    except httpx.RequestError:
        return {"instance": {"state": "offline"}}
    except Exception as e:
        return {"instance": {"state": "not_found"}}

@api_router.delete("/whatsapp/my-instance/disconnect")
async def disconnect_my_whatsapp(admin: dict = Depends(get_current_admin)):
    """Doctor disconnects their WhatsApp"""
    clinic_id = admin.get("clinic_id")
    if not clinic_id:
        raise HTTPException(status_code=400, detail="No clinic associated")
    if not EVOLUTION_GLOBAL_API_KEY:
        raise HTTPException(status_code=500, detail="Evolution API Key not set")
    
    headers = {"apikey": EVOLUTION_GLOBAL_API_KEY}
    instance_id = clinic_id.replace("-", "")
    base_url = EVOLUTION_API_URL.rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Silently ignore logout errors (instance may not be connected)
            try:
                await client.delete(f"{base_url}/instance/logout/{instance_id}", headers=headers)
            except Exception:
                pass
            # Delete the instance
            response = await client.delete(f"{base_url}/instance/delete/{instance_id}", headers=headers)
            # Return success regardless of what Evolution says (instance is gone)
            try:
                return response.json()
            except Exception:
                return {"status": "deleted", "code": response.status_code}
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        # Return success anyway — from the doctor's perspective they are disconnected
        return {"status": "disconnected"}

# ============ PRIVACY POLICY (required by Meta) ============

@api_router.get("/privacy")
async def privacy_policy():
    """Simple privacy policy page required by Meta for app publishing"""
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Política de Privacidad - MedicAI</title>
<style>body{font-family:system-ui,sans-serif;max-width:700px;margin:40px auto;padding:0 20px;color:#333;line-height:1.6}
h1{color:#0284c7}h2{color:#0369a1;margin-top:2em}</style></head>
<body>
<h1>Política de Privacidad — MedicAI</h1>
<p><strong>Última actualización:</strong> Marzo 2026</p>
<h2>1. Información que Recopilamos</h2>
<p>MedicAI recopila información proporcionada voluntariamente por los pacientes a través de WhatsApp, incluyendo: nombre, número de teléfono, y motivo de consulta. Esta información se utiliza exclusivamente para la gestión de citas médicas.</p>
<h2>2. Uso de la Información</h2>
<p>La información recopilada se utiliza únicamente para: agendar, confirmar y gestionar citas médicas; enviar recordatorios; y mejorar la atención al paciente. No vendemos ni compartimos datos con terceros.</p>
<h2>3. Almacenamiento y Seguridad</h2>
<p>Los datos se almacenan de forma segura en servidores protegidos con cifrado. Solo el personal autorizado del consultorio médico tiene acceso a la información del paciente.</p>
<h2>4. Derechos del Usuario</h2>
<p>Los pacientes pueden solicitar la eliminación de sus datos en cualquier momento contactando directamente al consultorio médico.</p>
<h2>5. WhatsApp y Meta</h2>
<p>Este servicio utiliza la API de WhatsApp Business de Meta. Los mensajes se procesan para generar respuestas automatizadas. Meta puede procesar metadatos según su propia política de privacidad.</p>
<h2>6. Contacto</h2>
<p>Para dudas sobre esta política, contactar al administrador del sistema MedicAI.</p>
</body></html>"""
    return HTMLResponse(content=html)

# ============ HEALTH CHECK ============

@api_router.get("/")
async def root():
    return {"message": "MedicAI API v1.0", "status": "healthy"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ============ WEBSOCKET ENDPOINT ============

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down MedicAI API")
