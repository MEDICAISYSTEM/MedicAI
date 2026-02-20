import { useState, useEffect, useRef, useCallback } from "react";
import { getDashboardStats, getAppointments, getAlerts, createConsultationNote, getMedicalRecord, updateMedicalRecord, updateAlert } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Calendar } from "../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { 
  Users, 
  Calendar as CalendarIcon, 
  CalendarCheck, 
  AlertTriangle,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  CalendarDays,
  FileText,
  Stethoscope,
  Bell,
  RefreshCw,
  Heart,
  Droplet,
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { format, parseISO, addDays, subDays } from "date-fns";
import { es } from "date-fns/locale";

const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [todayAppointments, setTodayAppointments] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [calendarOpen, setCalendarOpen] = useState(false);
  const wsRef = useRef(null);
  
  // Consultation note modal
  const [noteDialogOpen, setNoteDialogOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [savingNote, setSavingNote] = useState(false);
  const [loadingMedicalRecord, setLoadingMedicalRecord] = useState(false);
  const [medicalRecord, setMedicalRecord] = useState(null);
  const [consultationNote, setConsultationNote] = useState({
    symptoms: "",
    diagnosis: "",
    treatment: "",
    observations: ""
  });

  const fetchData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const today = format(new Date(), "yyyy-MM-dd");
      const [statsRes, appointmentsRes, alertsRes] = await Promise.all([
        getDashboardStats(),
        getAppointments({ date: today }),
        getAlerts({ status: "pending" }),
      ]);
      
      setStats(statsRes.data);
      const sortedAppointments = appointmentsRes.data.sort((a, b) => 
        a.time.localeCompare(b.time)
      );
      setTodayAppointments(sortedAppointments);
      setRecentAlerts(alertsRes.data.slice(0, 5));
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // WebSocket connection for real-time notifications
  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = process.env.REACT_APP_BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');
      const ws = new WebSocket(`${wsUrl}/ws/notifications`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'new_appointment') {
            const apt = message.data;
            // Show toast notification
            toast.success(
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2 font-semibold">
                  <Bell className="w-4 h-4" />
                  Nueva cita agendada
                </div>
                <p className="text-sm">{apt.patient_name}</p>
                <p className="text-xs text-slate-500">
                  {apt.date} a las {apt.time} - {apt.reason}
                </p>
              </div>,
              {
                duration: 10000,
                action: {
                  label: "Ver",
                  onClick: () => fetchData(true)
                }
              }
            );
            
            // Auto-refresh data
            fetchData(true);
          }
        } catch (e) {
          console.error('WebSocket message error:', e);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 5s...');
        setTimeout(connectWebSocket, 5000);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      wsRef.current = ws;
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [fetchData]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpenNoteDialog = async (appointment) => {
    setSelectedAppointment(appointment);
    setConsultationNote({
      symptoms: "",
      diagnosis: "",
      treatment: "",
      observations: ""
    });
    setMedicalRecord(null);
    setNoteDialogOpen(true);
    
    // Load medical record for this patient
    setLoadingMedicalRecord(true);
    try {
      const recordRes = await getMedicalRecord(appointment.patient_id);
      setMedicalRecord(recordRes.data);
    } catch (error) {
      console.error("Error loading medical record:", error);
      // If no record exists, initialize empty one
      setMedicalRecord({
        blood_type: "",
        allergies: "",
        pathologies: ""
      });
    } finally {
      setLoadingMedicalRecord(false);
    }
  };

  const handleResolveAlert = async (alertId) => {
    try {
      await updateAlert(alertId, { status: "resolved" });
      setRecentAlerts(prev => prev.filter(a => a.id !== alertId));
      toast.success("Alerta marcada como resuelta");
    } catch (error) {
      toast.error("Error al resolver la alerta");
    }
  };

  const handleSaveConsultationNote = async () => {
    if (!consultationNote.symptoms && !consultationNote.diagnosis && !consultationNote.treatment && !consultationNote.observations) {
      toast.error("Agrega al menos un campo a la nota");
      return;
    }
    
    setSavingNote(true);
    try {
      // First, save/update medical record if there are changes
      if (medicalRecord && (medicalRecord.blood_type || medicalRecord.allergies || medicalRecord.pathologies)) {
        await updateMedicalRecord(selectedAppointment.patient_id, medicalRecord);
      }
      
      // Then save the consultation note
      await createConsultationNote(selectedAppointment.patient_id, {
        ...consultationNote,
        patient_id: selectedAppointment.patient_id,
        appointment_id: selectedAppointment.id,
        date: selectedAppointment.date
      });
      toast.success("Nota de consulta guardada exitosamente");
      setNoteDialogOpen(false);
    } catch (error) {
      toast.error("Error al guardar la nota");
    } finally {
      setSavingNote(false);
    }
  };

  const statCards = [
    {
      title: "Pacientes",
      value: stats?.total_patients || 0,
      icon: Users,
      bgColor: "bg-sky-50",
      iconColor: "text-sky-500",
    },
    {
      title: "Hoy",
      value: stats?.total_appointments_today || 0,
      icon: Calendar,
      bgColor: "bg-emerald-50",
      iconColor: "text-emerald-500",
    },
    {
      title: "Semana",
      value: stats?.total_appointments_week || 0,
      icon: CalendarCheck,
      bgColor: "bg-violet-50",
      iconColor: "text-violet-500",
    },
    {
      title: "Alertas",
      value: stats?.pending_alerts || 0,
      icon: AlertTriangle,
      bgColor: "bg-amber-50",
      iconColor: "text-amber-500",
    },
    {
      title: "Confirmadas",
      value: stats?.confirmed_appointments || 0,
      icon: CheckCircle,
      bgColor: "bg-emerald-50",
      iconColor: "text-emerald-500",
    },
    {
      title: "Canceladas",
      value: stats?.cancelled_appointments || 0,
      icon: XCircle,
      bgColor: "bg-red-50",
      iconColor: "text-red-500",
    },
  ];

  const getStatusBadge = (status) => {
    switch (status) {
      case 'confirmed':
        return <Badge className="badge-success text-xs">Confirmada</Badge>;
      case 'cancelled':
        return <Badge className="badge-error text-xs">Cancelada</Badge>;
      case 'pending':
        return <Badge className="badge-warning text-xs">Pendiente</Badge>;
      default:
        return <Badge className="badge-neutral text-xs">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Dashboard
          </h1>
          <p className="text-slate-500 text-sm">
            {format(new Date(), "EEEE, d 'de' MMMM", { locale: es })}
          </p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => fetchData(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* Compact Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map((stat, index) => (
          <Card 
            key={stat.title} 
            className="stat-card"
            data-testid={`stat-card-${index}`}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 ${stat.bgColor} rounded-lg flex items-center justify-center flex-shrink-0`}>
                  <stat.icon className={`w-4 h-4 ${stat.iconColor}`} />
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {stat.value}
                  </p>
                  <p className="text-xs text-slate-500">{stat.title}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick View Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Appointments Quick View */}
        <Card className="stat-card" data-testid="today-appointments-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <Clock className="w-4 h-4 text-sky-500" />
              Próximas Citas
            </CardTitle>
          </CardHeader>
          <CardContent>
            {todayAppointments.length === 0 ? (
              <div className="text-center py-6 text-slate-500">
                <Calendar className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                <p className="text-sm">Sin citas para hoy</p>
              </div>
            ) : (
              <div className="space-y-2">
                {todayAppointments.slice(0, 4).map((apt) => (
                  <div 
                    key={apt.id} 
                    className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 bg-sky-100 rounded-full flex items-center justify-center">
                        <span className="text-sky-600 font-semibold text-xs">
                          {apt.patient_name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 text-sm">{apt.patient_name || 'Sin nombre'}</p>
                        <p className="text-xs text-slate-500">{apt.reason}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-slate-900 text-sm">{apt.time}</p>
                      {getStatusBadge(apt.status)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Alerts */}
        <Card className="stat-card" data-testid="recent-alerts-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Alertas del Día
              {recentAlerts.length > 0 && (
                <Badge className="badge-warning text-xs">{recentAlerts.length}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentAlerts.length === 0 ? (
              <div className="text-center py-6 text-slate-500">
                <CheckCircle className="w-10 h-10 mx-auto mb-2 text-emerald-300" />
                <p className="text-sm">Sin alertas pendientes</p>
              </div>
            ) : (
              <div className="space-y-2">
                {recentAlerts.map((alert) => (
                  <div 
                    key={alert.id} 
                    className="flex items-start gap-2.5 p-2.5 bg-amber-50 border border-amber-100 rounded-lg group"
                  >
                    <div className="w-7 h-7 bg-amber-100 rounded flex items-center justify-center flex-shrink-0">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="font-medium text-slate-900 text-sm">{alert.patient_name || alert.patient_phone}</p>
                        <Badge className={`text-[10px] ${alert.priority === 'high' ? 'badge-error' : 'badge-warning'}`}>
                          {alert.priority === 'high' ? 'Alta' : 'Normal'}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-600 truncate">{alert.message}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleResolveAlert(alert.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                      title="Marcar como resuelta"
                    >
                      <Check className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Daily Schedule Table */}
      <Card className="stat-card" data-testid="daily-schedule-card">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <CalendarDays className="w-4 h-4 text-violet-500" />
              Agenda del Día
            </CardTitle>
            <p className="text-xs text-slate-500">
              Clic en "Nota" para registrar consulta
            </p>
          </div>
        </CardHeader>
        <CardContent>
          {todayAppointments.length === 0 ? (
            <div className="text-center py-10 text-slate-500">
              <CalendarDays className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="font-medium">Sin citas programadas</p>
              <p className="text-sm">Tu agenda está libre para hoy</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider w-20">Hora</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Paciente</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Motivo</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">Teléfono</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider w-20">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {todayAppointments.map((apt) => (
                    <tr 
                      key={apt.id} 
                      className={`hover:bg-sky-50/50 transition-colors ${
                        apt.priority === 'high' ? 'bg-red-50/50' : ''
                      }`}
                      data-testid={`schedule-row-${apt.id}`}
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <div className={`w-1.5 h-1.5 rounded-full ${
                            apt.status === 'confirmed' ? 'bg-emerald-500' :
                            apt.status === 'cancelled' ? 'bg-red-500' :
                            'bg-amber-500'
                          }`}></div>
                          <span className="font-semibold text-slate-900 text-sm">{apt.time}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 bg-sky-100 rounded-full flex items-center justify-center">
                            <span className="text-sky-600 font-semibold text-xs">
                              {apt.patient_name?.charAt(0)?.toUpperCase() || '?'}
                            </span>
                          </div>
                          <span className="font-medium text-slate-900 text-sm">{apt.patient_name || 'Sin nombre'}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-slate-600 text-sm">{apt.reason}</span>
                      </td>
                      <td className="py-3 px-3 hidden sm:table-cell">
                        <span className="text-slate-500 text-xs">{apt.patient_phone || '-'}</span>
                      </td>
                      <td className="py-3 px-3">
                        {getStatusBadge(apt.status)}
                      </td>
                      <td className="py-3 px-3">
                        {apt.status === 'confirmed' && (
                          <Button 
                            size="sm" 
                            variant="outline"
                            className="h-7 text-xs text-sky-600 border-sky-200 hover:bg-sky-50 px-2"
                            onClick={() => handleOpenNoteDialog(apt)}
                            data-testid={`note-btn-${apt.id}`}
                          >
                            <Stethoscope className="w-3 h-3 mr-1" />
                            Nota
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Consultation Note Dialog */}
      <Dialog open={noteDialogOpen} onOpenChange={setNoteDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Stethoscope className="w-5 h-5 text-sky-500" />
              Nota de Consulta
            </DialogTitle>
          </DialogHeader>
          
          {selectedAppointment && (
            <div className="space-y-4">
              {/* Patient Info */}
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                <div className="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center">
                  <span className="text-sky-600 font-bold text-sm">
                    {selectedAppointment.patient_name?.charAt(0)?.toUpperCase() || '?'}
                  </span>
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">{selectedAppointment.patient_name || 'Sin nombre'}</h3>
                  <p className="text-xs text-slate-500">
                    {format(parseISO(selectedAppointment.date), "d MMM yyyy", { locale: es })} • {selectedAppointment.time} • {selectedAppointment.reason}
                  </p>
                </div>
              </div>
              
              {/* Medical History / Antecedentes - NUEVO */}
              <div className="p-4 bg-red-50 border border-red-100 rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold text-slate-800 flex items-center gap-2 text-sm">
                    <Heart className="w-4 h-4 text-red-500" />
                    Antecedentes Médicos
                  </h4>
                  {loadingMedicalRecord ? (
                    <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                  ) : (!medicalRecord?.blood_type && !medicalRecord?.allergies && !medicalRecord?.pathologies) ? (
                    <Badge className="badge-warning text-xs">Primera consulta</Badge>
                  ) : (
                    <Badge className="badge-success text-xs">Expediente registrado</Badge>
                  )}
                </div>
                
                {loadingMedicalRecord ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600 flex items-center gap-1">
                        <Droplet className="w-3 h-3 text-red-500" />
                        Tipo de sangre
                      </Label>
                      <Select 
                        value={medicalRecord?.blood_type || ""} 
                        onValueChange={(value) => setMedicalRecord({ ...medicalRecord, blood_type: value })}
                      >
                        <SelectTrigger className="h-8 text-sm bg-white">
                          <SelectValue placeholder="Seleccionar" />
                        </SelectTrigger>
                        <SelectContent>
                          {BLOOD_TYPES.map((type) => (
                            <SelectItem key={type} value={type}>{type}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 text-amber-500" />
                        Alergias
                      </Label>
                      <Input
                        value={medicalRecord?.allergies || ""}
                        onChange={(e) => setMedicalRecord({ ...medicalRecord, allergies: e.target.value })}
                        placeholder="Ej: Penicilina..."
                        className="h-8 text-sm bg-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600">Patologías</Label>
                      <Input
                        value={medicalRecord?.pathologies || ""}
                        onChange={(e) => setMedicalRecord({ ...medicalRecord, pathologies: e.target.value })}
                        placeholder="Ej: Diabetes..."
                        className="h-8 text-sm bg-white"
                      />
                    </div>
                  </div>
                )}
              </div>
              
              {/* Note Form */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-sm">Síntomas</Label>
                  <Textarea
                    value={consultationNote.symptoms}
                    onChange={(e) => setConsultationNote({ ...consultationNote, symptoms: e.target.value })}
                    placeholder="Síntomas del paciente..."
                    className="input-base min-h-[90px] text-sm"
                    data-testid="note-symptoms"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm">Diagnóstico</Label>
                  <Textarea
                    value={consultationNote.diagnosis}
                    onChange={(e) => setConsultationNote({ ...consultationNote, diagnosis: e.target.value })}
                    placeholder="Diagnóstico médico..."
                    className="input-base min-h-[90px] text-sm"
                    data-testid="note-diagnosis"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-sm">Tratamiento</Label>
                  <Textarea
                    value={consultationNote.treatment}
                    onChange={(e) => setConsultationNote({ ...consultationNote, treatment: e.target.value })}
                    placeholder="Tratamiento, medicamentos..."
                    className="input-base min-h-[90px] text-sm"
                    data-testid="note-treatment"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm">Observaciones</Label>
                  <Textarea
                    value={consultationNote.observations}
                    onChange={(e) => setConsultationNote({ ...consultationNote, observations: e.target.value })}
                    placeholder="Observaciones, seguimiento..."
                    className="input-base min-h-[90px] text-sm"
                    data-testid="note-observations"
                  />
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setNoteDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveConsultationNote} 
              className="btn-primary"
              disabled={savingNote}
              data-testid="save-note-btn"
            >
              {savingNote ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Guardar
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
