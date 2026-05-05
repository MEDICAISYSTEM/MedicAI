import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("medicai_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("medicai_token");
      localStorage.removeItem("medicai_admin");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (email, password) =>
  api.post("/auth/login", { email, password });

export const register = (email, password, name) =>
  api.post("/auth/register", { email, password, name });

export const getCurrentUser = () => api.get("/auth/me");

// Dashboard
export const getDashboardStats = () => api.get("/dashboard/stats");

// Patients
export const getPatients = () => api.get("/patients");
export const getPatient = (id) => api.get(`/patients/${id}`);
export const updatePatient = (id, data) => api.put(`/patients/${id}`, data);
export const deletePatient = (id) => api.delete(`/patients/${id}`);

// Medical Records
export const getMedicalRecord = (patientId) => api.get(`/patients/${patientId}/medical-record`);
export const updateMedicalRecord = (patientId, data) => api.put(`/patients/${patientId}/medical-record`, data);

// Consultation Notes
export const getConsultationNotes = (patientId) => api.get(`/patients/${patientId}/consultation-notes`);
export const createConsultationNote = (patientId, data) => api.post(`/patients/${patientId}/consultation-notes`, data);
export const updateConsultationNote = (noteId, data) => api.put(`/consultation-notes/${noteId}`, data);

// Appointments
export const getAppointments = (params) => api.get("/appointments", { params });
export const createAppointment = (data) => api.post("/appointments", data);
export const updateAppointment = (id, data) => api.put(`/appointments/${id}`, data);
export const deleteAppointment = (id) => api.delete(`/appointments/${id}`);

// Availability
export const getAvailability = () => api.get("/availability");
export const createAvailability = (data) => api.post("/availability", data);
export const updateAvailability = (id, data) => api.put(`/availability/${id}`, data);
export const deleteAvailability = (id) => api.delete(`/availability/${id}`);

// Conversations
export const getConversations = () => api.get("/conversations");
export const getConversation = (id) => api.get(`/conversations/${id}`);

// Alerts
export const getAlerts = (params) => api.get("/alerts", { params });
export const updateAlert = (id, data) => api.put(`/alerts/${id}`, data);

// Super Admin - Clinics
export const getSuperAdminStats = () => api.get("/superadmin/stats");
export const getClinics = () => api.get("/superadmin/clinics");
export const getClinic = (id) => api.get(`/superadmin/clinics/${id}`);
export const createClinic = (data) => api.post("/superadmin/clinics", data);
export const updateClinic = (id, data) => api.put(`/superadmin/clinics/${id}`, data);
export const deleteClinic = (id) => api.delete(`/superadmin/clinics/${id}`);
export const createClinicAdmin = (clinicId, data) => api.post(`/superadmin/clinics/${clinicId}/create-admin`, data);
export const getClinicStats = (clinicId) => api.get(`/superadmin/clinics/${clinicId}/stats`);

// WhatsApp Integration (Evolution API) - Super Admin
export const createWhatsAppInstance = (clinicId) => api.post(`/whatsapp/instance/create?clinic_id=${clinicId}`);
export const getWhatsAppQr = (clinicId) => api.get(`/whatsapp/instance/qr?clinic_id=${clinicId}`);
export const getWhatsAppStatus = (clinicId) => api.get(`/whatsapp/instance/status?clinic_id=${clinicId}`);
export const deleteWhatsAppInstance = (clinicId) => api.delete(`/whatsapp/instance/delete?clinic_id=${clinicId}`);

// WhatsApp Integration - Doctor Self-Service (Evolution API - Legacy)
export const createMyWhatsAppInstance = () => api.post('/whatsapp/my-instance/create');
export const getMyWhatsAppQr = () => api.get('/whatsapp/my-instance/qr');
export const getMyWhatsAppStatus = () => api.get('/whatsapp/my-instance/status');
export const disconnectMyWhatsApp = () => api.delete('/whatsapp/my-instance/disconnect');

// WhatsApp Cloud API - Official (Meta Embedded Signup)
export const completeEmbeddedSignup = (data) => api.post('/whatsapp/embedded-signup/complete', data);
export const getMyWhatsAppAccount = () => api.get('/whatsapp/my-account');
export const disconnectMyWhatsAppAccount = () => api.delete('/whatsapp/my-account');
export const generateEncryptionKey = () => api.post('/whatsapp/generate-encryption-key');

export default api;
