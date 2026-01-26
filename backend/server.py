from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import jwt
from passlib.context import CryptContext

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

# Create the main app
app = FastAPI(title="MedicAI API", version="1.0.0")

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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    admin: dict

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
        return {"id": admin_id, "email": payload.get("email")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============ AUTH ENDPOINTS ============

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: AdminLogin):
    """Admin login endpoint"""
    try:
        result = supabase.table("admins").select("*").eq("email", credentials.email).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        admin = result.data[0]
        
        if not verify_password(credentials.password, admin["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        access_token = create_access_token(
            data={"sub": admin["id"], "email": admin["email"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            admin={"id": admin["id"], "email": admin["email"], "name": admin["name"]}
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
        result = supabase.table("admins").select("id, email, name, created_at").eq("id", admin["id"]).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Admin not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin info")

# ============ PATIENTS ENDPOINTS ============

@api_router.get("/patients", response_model=List[PatientResponse])
async def get_patients(admin: dict = Depends(get_current_admin)):
    """Get all patients"""
    try:
        result = supabase.table("patients").select("*").order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Get patients error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patients")

@api_router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, admin: dict = Depends(get_current_admin)):
    """Get a specific patient"""
    try:
        result = supabase.table("patients").select("*").eq("id", patient_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Patient not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get patient error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patient")

# ============ APPOINTMENTS ENDPOINTS ============

@api_router.get("/appointments", response_model=List[AppointmentResponse])
async def get_appointments(
    date: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """Get appointments with optional filters"""
    try:
        query = supabase.table("appointments").select("*, patients(name, phone)")
        
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
        apt_id = str(uuid.uuid4())
        new_apt = {
            "id": apt_id,
            "patient_id": appointment.patient_id,
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
    except Exception as e:
        logger.error(f"Create appointment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create appointment")

@api_router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str, 
    update_data: AppointmentUpdate,
    admin: dict = Depends(get_current_admin)
):
    """Update an appointment"""
    try:
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
    """Delete an appointment"""
    try:
        supabase.table("appointments").delete().eq("id", appointment_id).execute()
        return {"message": "Appointment deleted"}
    except Exception as e:
        logger.error(f"Delete appointment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete appointment")

# ============ AVAILABILITY ENDPOINTS ============

@api_router.get("/availability", response_model=List[AvailabilitySlot])
async def get_availability(admin: dict = Depends(get_current_admin)):
    """Get availability slots"""
    try:
        result = supabase.table("availability").select("*").order("day_of_week").order("start_time").execute()
        return result.data
    except Exception as e:
        logger.error(f"Get availability error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get availability")

@api_router.post("/availability", response_model=AvailabilitySlot)
async def create_availability(slot: AvailabilitySlot, admin: dict = Depends(get_current_admin)):
    """Create a new availability slot"""
    try:
        slot_id = str(uuid.uuid4())
        new_slot = {
            "id": slot_id,
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
    """Update an availability slot"""
    try:
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
    """Delete an availability slot"""
    try:
        supabase.table("availability").delete().eq("id", slot_id).execute()
        return {"message": "Availability slot deleted"}
    except Exception as e:
        logger.error(f"Delete availability error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete availability slot")

# ============ CONVERSATIONS ENDPOINTS ============

@api_router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(admin: dict = Depends(get_current_admin)):
    """Get all conversations"""
    try:
        result = supabase.table("conversations").select("*, patients(name, phone)").order("last_message_at", desc=True).execute()
        
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
    """Get a specific conversation with messages"""
    try:
        conv_result = supabase.table("conversations").select("*, patients(name, phone)").eq("id", conversation_id).execute()
        
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
async def get_alerts(status: Optional[str] = None, admin: dict = Depends(get_current_admin)):
    """Get alerts with optional status filter"""
    try:
        query = supabase.table("alerts").select("*, patients(name, phone)")
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("created_at", desc=True).execute()
        
        alerts = []
        for alert in result.data:
            patient = alert.pop("patients", {}) or {}
            alerts.append({
                **alert,
                "patient_name": patient.get("name"),
                "patient_phone": patient.get("phone")
            })
        
        return alerts
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")

@api_router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: str, update_data: AlertUpdate, admin: dict = Depends(get_current_admin)):
    """Update alert status"""
    try:
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
    """Get dashboard statistics"""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        
        # Total patients
        patients_result = supabase.table("patients").select("id", count="exact").execute()
        total_patients = patients_result.count or 0
        
        # Today's appointments
        today_result = supabase.table("appointments").select("id", count="exact").eq("date", today).execute()
        total_appointments_today = today_result.count or 0
        
        # Week's appointments
        week_result = supabase.table("appointments").select("id", count="exact").gte("date", week_start).execute()
        total_appointments_week = week_result.count or 0
        
        # Pending alerts
        alerts_result = supabase.table("alerts").select("id", count="exact").eq("status", "pending").execute()
        pending_alerts = alerts_result.count or 0
        
        # Confirmed appointments
        confirmed_result = supabase.table("appointments").select("id", count="exact").eq("status", "confirmed").execute()
        confirmed_appointments = confirmed_result.count or 0
        
        # Cancelled appointments
        cancelled_result = supabase.table("appointments").select("id", count="exact").eq("status", "cancelled").execute()
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
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        phone = message.phone
        content = message.message
        timestamp = message.timestamp or datetime.now(timezone.utc).isoformat()
        
        # Check if patient exists
        patient_result = supabase.table("patients").select("*").eq("phone", phone).execute()
        
        if patient_result.data:
            patient = patient_result.data[0]
            patient_id = patient["id"]
            # Update last interaction
            supabase.table("patients").update({
                "last_interaction": timestamp
            }).eq("id", patient_id).execute()
        else:
            # Create new patient
            patient_id = str(uuid.uuid4())
            new_patient = {
                "id": patient_id,
                "phone": phone,
                "name": None,
                "created_at": timestamp,
                "last_interaction": timestamp
            }
            supabase.table("patients").insert(new_patient).execute()
            patient = new_patient
        
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
                "started_at": timestamp,
                "last_message_at": timestamp,
                "status": "active"
            }
            supabase.table("conversations").insert(new_conv).execute()
        
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
        
        # Get conversation history for context
        history_result = supabase.table("messages").select("*").eq("conversation_id", conv_id).order("timestamp").limit(10).execute()
        
        # Get availability for context
        availability_result = supabase.table("availability").select("*").eq("is_available", True).execute()
        availability_info = availability_result.data if availability_result.data else []
        
        days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        availability_text = "\n".join([
            f"- {days[slot['day_of_week']]}: {slot['start_time']} - {slot['end_time']}"
            for slot in availability_info
        ]) if availability_info else "Horarios no disponibles actualmente."
        
        # Build conversation history for AI
        conversation_history = ""
        for msg in history_result.data[:-1]:  # Exclude current message
            role = "Paciente" if msg["sender"] == "patient" else "Asistente"
            conversation_history += f"{role}: {msg['content']}\n"
        
        # System prompt for medical AI assistant
        system_prompt = f"""Eres MedicAI, un asistente virtual de una clínica médica. Tu rol es EXCLUSIVAMENTE administrativo.

REGLAS ESTRICTAS:
1. NUNCA des diagnósticos médicos ni recomendaciones de tratamiento
2. NUNCA recetes medicamentos ni des consejos de salud específicos
3. Solo puedes ayudar con: agendar citas, consultar precios, informar horarios, y atender urgencias administrativas

INFORMACIÓN DE LA CLÍNICA:
Horarios disponibles:
{availability_text}

PACIENTE ACTUAL:
- Nombre: {patient.get('name') or 'No registrado'}
- Teléfono: {phone}

HISTORIAL DE CONVERSACIÓN:
{conversation_history}

FLUJO DE CONVERSACIÓN:
1. Si es paciente nuevo (sin nombre), solicita su nombre amablemente
2. Identifica la intención: CITA, URGENCIA, PRECIO, o CONSULTA_GENERAL
3. Si detectas una urgencia médica, indica que contactarás al personal médico inmediatamente
4. Para citas, ofrece los horarios disponibles y confirma la cita
5. Siempre sé amable, profesional y empático

RESPONDE EN ESPAÑOL. Sé conciso pero amable."""

        # Process with Gemini AI
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        
        chat = LlmChat(
            api_key=emergent_key,
            session_id=conv_id,
            system_message=system_prompt
        )
        chat.with_model("gemini", "gemini-3-flash-preview")
        
        user_msg = UserMessage(text=content)
        ai_response = await chat.send_message(user_msg)
        
        # Detect intent from AI response and original message
        intent = "general"
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["urgente", "urgencia", "emergencia", "grave", "dolor fuerte", "sangrado"]):
            intent = "urgency"
            # Create alert for urgent cases
            alert_id = str(uuid.uuid4())
            alert = {
                "id": alert_id,
                "patient_id": patient_id,
                "message": content,
                "priority": "high",
                "status": "pending",
                "created_at": timestamp
            }
            supabase.table("alerts").insert(alert).execute()
            
        elif any(word in content_lower for word in ["cita", "agendar", "consulta", "turno", "hora"]):
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
