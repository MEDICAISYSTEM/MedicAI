from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
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

WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '521XXXXXXXXXX')  # Tu número de WhatsApp Business

def generate_whatsapp_link(code, doctor_name=""):
    """Generate a user-friendly WhatsApp link with natural message"""
    # Mensaje natural que el paciente NO querrá borrar
    # El código va al final entre paréntesis para que sea menos intrusivo
    if doctor_name:
        message = f"Hola, quiero agendar una cita con {doctor_name} (#{code})"
    else:
        message = f"Hola, quiero agendar una cita (#{code})"
    
    # Encode para URL
    from urllib.parse import quote
    encoded_message = quote(message)
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_message}"

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
        result = supabase.table("clinics").select("*").order("created_at", desc=True).execute()
        
        clinics = []
        for clinic in result.data:
            clinic["whatsapp_link"] = generate_whatsapp_link(clinic['code'], clinic['name'])
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
        clinic["whatsapp_link"] = generate_whatsapp_link(clinic['code'], clinic['name'])
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
            "is_active": True,
            "subscription_status": "active",
            "subscription_start": datetime.now(timezone.utc).date().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("clinics").insert(new_clinic).execute()
        
        new_clinic["whatsapp_link"] = generate_whatsapp_link(new_clinic['code'], new_clinic['name'])
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
        clinic["whatsapp_link"] = generate_whatsapp_link(clinic['code'])
        return clinic
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update clinic error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update clinic")

@api_router.delete("/superadmin/clinics/{clinic_id}")
async def delete_clinic(clinic_id: str, admin: dict = Depends(require_super_admin)):
    """Delete a clinic (soft delete by deactivating)"""
    try:
        supabase.table("clinics").update({
            "is_active": False,
            "subscription_status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", clinic_id).execute()
        return {"message": "Clinic deactivated"}
    except Exception as e:
        logger.error(f"Delete clinic error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete clinic")

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
        is_first_contact = False  # Flag to track if this is first message with code
        
        # Check if message contains a clinic code (format: #CODIGO or Ref:CODIGO or (CODIGO))
        clinic_id = None
        clinic = None
        
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
        
        if clinic_code_match:
            potential_code = clinic_code_match.group(1)
            clinic_result = supabase.table("clinics").select("*").eq("code", potential_code).eq("is_active", True).execute()
            if clinic_result.data:
                clinic = clinic_result.data[0]
                clinic_id = clinic["id"]
                is_first_contact = True
                # Remove the code from message for natural conversation (all formats)
                content = re.sub(r'\(#[A-Za-z0-9]{3,10}\)', '', content).strip()
                content = re.sub(r'#[A-Za-z0-9]{3,10}\b', '', content).strip()
                content = re.sub(r'Ref:\s*[A-Za-z0-9]{3,10}\b', '', content, flags=re.IGNORECASE).strip()
        
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
                # No clinic identified - ask to use a valid link
                return {
                    "success": True,
                    "response": "¡Hola! Para atenderte necesito que uses el link de WhatsApp de tu doctor. Solicítalo en tu próxima cita.",
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
        
        # If still no clinic after all checks, return error
        if not clinic_id or not clinic:
            return {
                "success": False,
                "response": "No pudimos identificar tu clínica. Por favor usa el link de WhatsApp que te proporcionó tu doctor.",
                "intent": "error",
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
        
        if conv_result.data:
            conversation = conv_result.data[0]
            conv_id = conversation["id"]
        else:
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
        
        # Get conversation history BEFORE saving current message
        history_result = supabase.table("messages").select("*").eq("conversation_id", conv_id).order("timestamp").limit(20).execute()
        
        # Save patient message
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
        
        # Get availability for context - filtered by clinic
        availability_result = supabase.table("availability").select("*").eq("clinic_id", clinic_id).eq("is_available", True).order("day_of_week").execute()
        availability_info = availability_result.data if availability_result.data else []
        
        # If no clinic-specific availability, get general availability
        if not availability_info:
            availability_result = supabase.table("availability").select("*").is_("clinic_id", "null").eq("is_available", True).order("day_of_week").execute()
            availability_info = availability_result.data if availability_result.data else []
        
        days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        availability_text = "\n".join([
            f"- {days[slot['day_of_week']]}: {slot['start_time']} - {slot['end_time']}"
            for slot in availability_info
        ]) if availability_info else "Horarios no disponibles actualmente."
        
        # Build conversation history for AI context - format more clearly
        conversation_history = ""
        if history_result.data:
            for msg in history_result.data[-10:]:  # Last 10 messages max for clarity
                role = "PACIENTE" if msg["sender"] == "patient" else "ASISTENTE"
                conversation_history += f"{role}: {msg['content']}\n\n"
        
        # Get today's date for appointment context - BE VERY EXPLICIT
        from datetime import date
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        # Python weekday(): Monday=0, Sunday=6. Our array: Domingo=0, Lunes=1...Sábado=6
        python_weekday = today.weekday()  # 0=Monday, 1=Tuesday... 6=Sunday
        # Convert to our format: Sunday=0, Monday=1... Saturday=6
        our_day_index = (python_weekday + 1) % 7
        day_name = days[our_day_index]
        
        # Get current time for more context
        from datetime import datetime as dt_class
        current_time = dt_class.now().strftime("%H:%M")
        
        # Calculate next 7 days with their day names - MORE EXPLICIT
        from datetime import timedelta
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
        available_slots_text = "CALENDARIO DE DISPONIBILIDAD (próximos 7 días):\n"
        available_slots_text += f"⚡ REFERENCIA: Hoy es {day_name.upper()} {today_str}\n\n"
        for day_info in next_days_info:
            day_availability = [slot for slot in availability_info if slot.get('day_of_week') == day_info['day_num']]
            if day_availability:
                slots_str = ", ".join([f"{s['start_time']}-{s['end_time']}" for s in day_availability])
                available_slots_text += f"📅 {day_info['date']} = {day_info['day_label']} ({day_info['day_name']}): {slots_str}\n"
            else:
                available_slots_text += f"❌ {day_info['date']} = {day_info['day_label']} ({day_info['day_name']}): SIN DISPONIBILIDAD\n"
        
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
        
        # STRICT SECRETARY PROMPT
        system_prompt = f"""Eres una SECRETARIA MÉDICA profesional y estricta del consultorio del {doctor_name}.
Tu única función es gestionar la agenda de citas de manera precisa y consistente.

═══════════════════════════════════════════════════════════════
INFORMACIÓN DEL SISTEMA (¡DATOS REALES, NO INVENTES!)
═══════════════════════════════════════════════════════════════
Doctor: {doctor_name}
Especialidad: {specialty or 'Medicina General'}
Precio consulta: {price_info}

⏰ FECHA Y HORA ACTUAL (REAL DEL SERVIDOR):
   - Fecha: {today_str}
   - Día: {day_name.upper()}
   - Hora: {current_time}
   ⚠️ IMPORTANTE: Hoy es {day_name.upper()}. Si el paciente dice "mañana", 
   eso significa {next_days_info[1]['date']} ({next_days_info[1]['day_name']}).
   NO confundas los días. Usa SOLO las fechas del calendario abajo.

{available_slots_text}

═══════════════════════════════════════════════════════════════
DATOS DEL PACIENTE
═══════════════════════════════════════════════════════════════
Nombre: {patient.get('name') or '[SIN REGISTRAR - SOLICITAR ANTES DE CUALQUIER ACCIÓN]'}
Teléfono: {phone}{existing_apts_info}

═══════════════════════════════════════════════════════════════
REGLAS ABSOLUTAS (NO NEGOCIABLES)
═══════════════════════════════════════════════════════════════
1. NUNCA confirmes una cita sin que el paciente diga explícitamente "sí", "confirmo" o equivalente
2. NUNCA inventes horarios - solo ofrece los que aparecen arriba como DISPONIBLES
3. NUNCA crees una cita si el paciente ya tiene una activa - primero pregunta qué desea hacer
4. NUNCA asumas intenciones - siempre pregunta y confirma
5. Si hay CUALQUIER duda o inconsistencia, pide tiempo para verificar

═══════════════════════════════════════════════════════════════
FLUJOS OBLIGATORIOS
═══════════════════════════════════════════════════════════════

📋 AGENDAR CITA (paciente sin cita existente):
1. Verificar que tienes el nombre del paciente
2. Preguntar fecha, hora preferida y motivo
3. Ofrecer SOLO horarios disponibles reales
4. Confirmar datos: "Tengo disponible [fecha] a las [hora]. ¿Desea confirmar?"
5. SOLO si el paciente confirma, responde con el formato de confirmación

📋 PACIENTE CON CITA EXISTENTE:
Mensaje obligatorio: "Tiene una cita programada para [fecha] a las [hora]. ¿Desea mantenerla, cancelarla o reagendarla?"
NO agendes nada nuevo hasta que el paciente elija.

📋 CANCELAR CITA:
Si el paciente quiere cancelar, responde:
[CITA_CANCELADA]
ID: (los primeros 8 caracteres del ID de la cita)
[/CITA_CANCELADA]
Su cita para [fecha] a las [hora] ha sido cancelada correctamente.

📋 REAGENDAR CITA:
1. Primero cancela la cita existente con [CITA_CANCELADA]
2. Luego ofrece nuevos horarios disponibles
3. Si confirma el nuevo horario, usa [CITA_CONFIRMADA]

═══════════════════════════════════════════════════════════════
FORMATOS DE RESPUESTA DEL SISTEMA
═══════════════════════════════════════════════════════════════

Para CONFIRMAR nueva cita:
[CITA_CONFIRMADA]
Fecha: YYYY-MM-DD
Hora: HH:MM
Motivo: (motivo de consulta)
Nombre: (nombre completo)
[/CITA_CONFIRMADA]
Su cita ha quedado confirmada para el [fecha] a las [hora] con el {doctor_name}.

Para CANCELAR cita:
[CITA_CANCELADA]
ID: (primeros 8 caracteres del ID)
[/CITA_CANCELADA]
Su cita ha sido cancelada correctamente.

Para REGISTRAR nombre del paciente:
[NOMBRE: nombre_completo]

═══════════════════════════════════════════════════════════════
TONO Y ESTILO
═══════════════════════════════════════════════════════════════
- Profesional y cortés, pero directo
- Sin emojis excesivos
- Sin suposiciones
- Sin frases ambiguas
- Confirma todo antes de actuar

HISTORIAL DE LA CONVERSACIÓN:
{conversation_history}

MENSAJE ACTUAL DEL PACIENTE: {content}

Responde como secretaria médica profesional:"""

        # Process with Google Gemini (gemini-1.5-flash for speed and cost-effectiveness)
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            
            # Using asyncio.to_thread to run the synchronous SDK call without blocking the event loop
            import asyncio
            
            def call_gemini():
                return client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=system_prompt,
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
            hora_match = re.search(r'Hora:\s*(\d{1,2}:\d{2})', apt_text)
            motivo_match = re.search(r'Motivo:\s*(.+?)(?:\n|$)', apt_text)
            
            if fecha_match and hora_match:
                new_date = fecha_match.group(1)
                new_time = hora_match.group(1)
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
        
        # ═══════════════════════════════════════════════════════════════
        # SMART CONFIRMATION DETECTOR (Fallback when AI doesn't generate tag)
        # ═══════════════════════════════════════════════════════════════
        if not appointment_created and patient.get('name'):
            content_lower = content.lower().strip()
            # Detect confirmation words
            confirmation_words = ["sí", "si", "confirmo", "confirmar", "ok", "dale", "perfecto", 
                                  "está bien", "esta bien", "de acuerdo", "acepto", "va", "listo", 
                                  "correcto", "afirmativo", "claro", "por favor", "adelante"]
            is_confirmation = any(word in content_lower for word in confirmation_words) and len(content_lower) < 60
            
            if is_confirmation:
                # Look for date/time in the LAST bot message from conversation history
                # The bot usually proposes: "Tengo disponible 2026-01-30 a las 10:00"
                last_bot_msg = ""
                if history_result.data:
                    for msg in reversed(history_result.data):
                        if msg.get("sender") == "ai":
                            last_bot_msg = msg.get("content", "")
                            break
                
                # Also check current AI response for proposed times
                search_text = last_bot_msg + " " + ai_response
                
                # Extract date - look for YYYY-MM-DD format
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', search_text)
                
                # Extract time - look for HH:MM format
                time_match = re.search(r'(\d{1,2}):(\d{2})', search_text)
                
                # Also try to find "mañana", "hoy" patterns
                target_date = None
                target_time = None
                
                if date_match:
                    target_date = date_match.group(1)
                elif 'mañana' in search_text.lower():
                    target_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                elif 'hoy' in search_text.lower():
                    target_date = today.strftime('%Y-%m-%d')
                
                if time_match:
                    hour = int(time_match.group(1))
                    minute = time_match.group(2)
                    # Handle PM times
                    if ('pm' in search_text.lower() or 'p.m' in search_text.lower()) and hour < 12:
                        hour += 12
                    target_time = f"{hour:02d}:{minute}"
                
                # Try to extract reason from conversation
                reason = "Consulta general"
                reason_patterns = [
                    r'(?:motivo|por|para)[:\s]+([^\.]+?)(?:\.|$)',
                    r'(?:dolor|consulta|revisión|chequeo|cita)[:\s]*(?:de|por)?\s*([^\.]+?)(?:\.|$)'
                ]
                for pattern in reason_patterns:
                    reason_match = re.search(pattern, search_text.lower())
                    if reason_match:
                        reason = reason_match.group(1).strip().capitalize()[:50]
                        break
                
                if target_date and target_time:
                    # Check for duplicates
                    dup_check = supabase.table("appointments").select("id").eq("patient_id", patient_id).eq("clinic_id", clinic_id).eq("date", target_date).eq("time", target_time).eq("status", "confirmed").execute()
                    
                    if not dup_check.data:
                        apt_id = str(uuid.uuid4())
                        new_apt = {
                            "id": apt_id,
                            "patient_id": patient_id,
                            "clinic_id": clinic_id,
                            "date": target_date,
                            "time": target_time,
                            "reason": reason,
                            "status": "confirmed",
                            "priority": "normal",
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        supabase.table("appointments").insert(new_apt).execute()
                        appointment_created = True
                        logger.info(f"Appointment created (smart detector): {apt_id} for {patient.get('name')} at {target_date} {target_time}")
                        
                        # Override AI response with confirmation
                        ai_response = f"Perfecto. Su cita ha quedado confirmada para el {target_date} a las {target_time} con el {doctor_name}. Le esperamos."
                        
                        # WebSocket notification
                        await manager.broadcast({
                            "type": "new_appointment",
                            "clinic_id": clinic_id,
                            "data": {
                                "id": apt_id,
                                "patient_name": patient.get('name'),
                                "patient_phone": phone,
                                "date": target_date,
                                "time": target_time,
                                "reason": reason,
                                "doctor_name": doctor_name
                            }
                        })
                    else:
                        logger.warning(f"Duplicate prevented (smart detector): {patient_id} at {target_date} {target_time}")
        
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
            "response": ai_response,
            "intent": intent,
            "patient_id": patient_id,
            "conversation_id": conv_id,
            "phone": phone
        }
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

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
