import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { getDashboardStats, getAppointments, getAlerts, createConsultationNote, getMedicalRecord, updateMedicalRecord, updateAlert, updateAppointment } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
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
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  FileText,
  Stethoscope,
  Bell,
  RefreshCw,
  Heart,
  Droplet,
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Phone
} from "lucide-react";
import { format, addDays, subDays, startOfWeek, parseISO } from "date-fns";
import { es } from "date-fns/locale";

const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const HOURS = Array.from({ length: 14 }, (_, i) => i + 7); // 7:00 - 20:00

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [weekAppointments, setWeekAppointments] = useState({});
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [draggedApt, setDraggedApt] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
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

  // Generate the 7 days of the current week
  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  }, [weekStart]);

  const fetchData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      // Fetch stats and alerts
      const [statsRes, alertsRes] = await Promise.all([
        getDashboardStats(),
        getAlerts({ status: "pending" }),
      ]);
      setStats(statsRes.data);
      setRecentAlerts(alertsRes.data.slice(0, 5));

      // Fetch appointments for all 7 days in parallel
      const dayDates = Array.from({ length: 7 }, (_, i) =>
        format(addDays(weekStart, i), "yyyy-MM-dd")
      );
      const dayResults = await Promise.all(
        dayDates.map(d => getAppointments({ date: d }))
      );

      const aptsMap = {};
      dayDates.forEach((d, idx) => {
        aptsMap[d] = (dayResults[idx].data || []).sort((a, b) =>
          a.time.localeCompare(b.time)
        );
      });
      setWeekAppointments(aptsMap);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [weekStart]);

  // WebSocket connection for real-time notifications
  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = process.env.REACT_APP_BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');
      const ws = new WebSocket(`${wsUrl}/ws/notifications`);

      ws.onopen = () => console.log('WebSocket connected');

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'new_appointment') {
            const apt = message.data;
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
              { duration: 10000, action: { label: "Ver", onClick: () => fetchData(true) } }
            );
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
      ws.onerror = (error) => console.error('WebSocket error:', error);
      wsRef.current = ws;
    };

    connectWebSocket();
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, [fetchData]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ═══════════════════════════════════════════
  // DRAG AND DROP
  // ═══════════════════════════════════════════
  const handleDragStart = (e, apt) => {
    setDraggedApt(apt);
    e.dataTransfer.effectAllowed = "move";
    // Make the drag image semi-transparent
    if (e.target) {
      e.target.style.opacity = "0.5";
    }
  };

  const handleDragEnd = (e) => {
    if (e.target) e.target.style.opacity = "1";
    setDraggedApt(null);
    setDropTarget(null);
  };

  const handleDragOver = (e, dateStr, hour) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDropTarget({ date: dateStr, hour });
  };

  const handleDragLeave = () => {
    setDropTarget(null);
  };

  const handleDrop = async (e, dateStr, hour) => {
    e.preventDefault();
    setDropTarget(null);
    if (!draggedApt) return;

    const newTime = `${String(hour).padStart(2, '0')}:00`;
    const oldDate = draggedApt.date;
    const oldTime = draggedApt.time;

    // Skip if dropped on same slot
    if (oldDate === dateStr && oldTime === newTime) {
      setDraggedApt(null);
      return;
    }

    try {
      await updateAppointment(draggedApt.id, { date: dateStr, time: newTime });
      toast.success(
        `Cita de ${draggedApt.patient_name || 'Paciente'} movida a ${dateStr} ${newTime}`,
        { duration: 4000 }
      );
      fetchData(true);
    } catch (error) {
      toast.error("Error al mover la cita");
      console.error("Error updating appointment:", error);
    }
    setDraggedApt(null);
  };

  // ═══════════════════════════════════════════
  // CONSULTATION NOTES
  // ═══════════════════════════════════════════
  const handleOpenNoteDialog = async (appointment) => {
    setSelectedAppointment(appointment);
    setConsultationNote({ symptoms: "", diagnosis: "", treatment: "", observations: "" });
    setMedicalRecord(null);
    setNoteDialogOpen(true);

    setLoadingMedicalRecord(true);
    try {
      const recordRes = await getMedicalRecord(appointment.patient_id);
      setMedicalRecord(recordRes.data);
    } catch (error) {
      setMedicalRecord({ blood_type: "", allergies: "", pathologies: "" });
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
      if (medicalRecord && (medicalRecord.blood_type || medicalRecord.allergies || medicalRecord.pathologies)) {
        await updateMedicalRecord(selectedAppointment.patient_id, medicalRecord);
      }
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

  // ═══════════════════════════════════════════
  // NAVIGATION
  // ═══════════════════════════════════════════
  const handlePreviousWeek = () => setWeekStart(prev => subDays(prev, 7));
  const handleNextWeek = () => setWeekStart(prev => addDays(prev, 7));
  const handleThisWeek = () => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }));

  const todayStr = format(new Date(), "yyyy-MM-dd");
  const isCurrentWeek = weekDays.some(d => format(d, "yyyy-MM-dd") === todayStr);

  // ═══════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════
  const statCards = [
    { title: "Pacientes", value: stats?.total_patients || 0, icon: Users, bgColor: "bg-sky-50", iconColor: "text-sky-500" },
    { title: "Hoy", value: stats?.total_appointments_today || 0, icon: CalendarIcon, bgColor: "bg-emerald-50", iconColor: "text-emerald-500" },
    { title: "Semana", value: stats?.total_appointments_week || 0, icon: CalendarCheck, bgColor: "bg-violet-50", iconColor: "text-violet-500" },
    { title: "Alertas", value: stats?.pending_alerts || 0, icon: AlertTriangle, bgColor: "bg-amber-50", iconColor: "text-amber-500" },
    { title: "Confirmadas", value: stats?.confirmed_appointments || 0, icon: CheckCircle, bgColor: "bg-emerald-50", iconColor: "text-emerald-500" },
    { title: "Canceladas", value: stats?.cancelled_appointments || 0, icon: XCircle, bgColor: "bg-red-50", iconColor: "text-red-500" },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return { bg: 'bg-emerald-100 border-emerald-300', text: 'text-emerald-800', dot: 'bg-emerald-500' };
      case 'cancelled': return { bg: 'bg-red-100 border-red-300', text: 'text-red-800', dot: 'bg-red-500' };
      case 'pending': return { bg: 'bg-amber-100 border-amber-300', text: 'text-amber-800', dot: 'bg-amber-500' };
      case 'completed': return { bg: 'bg-sky-100 border-sky-300', text: 'text-sky-800', dot: 'bg-sky-500' };
      default: return { bg: 'bg-slate-100 border-slate-300', text: 'text-slate-700', dot: 'bg-slate-500' };
    }
  };

  // Get appointments for a specific day+hour
  const getAptsForSlot = (dateStr, hour) => {
    const dayApts = weekAppointments[dateStr] || [];
    return dayApts.filter(apt => {
      const aptHour = parseInt(apt.time?.split(':')[0], 10);
      return aptHour === hour;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in" data-testid="dashboard-page">
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

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map((stat, index) => (
          <Card key={stat.title} className="stat-card" data-testid={`stat-card-${index}`}>
            <CardContent className="p-3">
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

      {/* Main Content: Calendar + Alerts */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4">

        {/* Weekly Calendar */}
        <Card className="stat-card overflow-hidden" data-testid="weekly-calendar-card">
          <CardHeader className="pb-2 border-b border-slate-100">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-900">
                <CalendarIcon className="w-4 h-4 text-violet-500" />
                Agenda Semanal
              </CardTitle>

              <div className="flex items-center gap-1.5">
                <Button variant="outline" size="icon" className="h-7 w-7" onClick={handlePreviousWeek}>
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  className="h-7 px-3 text-xs font-medium"
                  onClick={handleThisWeek}
                >
                  {format(weekStart, "d MMM", { locale: es })} – {format(addDays(weekStart, 6), "d MMM yyyy", { locale: es })}
                </Button>
                <Button variant="outline" size="icon" className="h-7 w-7" onClick={handleNextWeek}>
                  <ChevronRight className="w-4 h-4" />
                </Button>
                {!isCurrentWeek && (
                  <Button variant="ghost" size="sm" className="h-7 text-xs text-sky-600" onClick={handleThisWeek}>
                    Esta semana
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <div className="min-w-[800px]">
                {/* Day Headers */}
                <div className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-slate-200 bg-slate-50/50">
                  <div className="p-2 text-xs text-slate-400 font-medium text-center">Hora</div>
                  {weekDays.map(day => {
                    const dateStr = format(day, "yyyy-MM-dd");
                    const isToday = dateStr === todayStr;
                    return (
                      <div
                        key={dateStr}
                        className={`p-2 text-center border-l border-slate-200 ${isToday ? 'bg-sky-50' : ''}`}
                      >
                        <p className={`text-xs font-medium ${isToday ? 'text-sky-600' : 'text-slate-500'}`}>
                          {format(day, "EEE", { locale: es }).toUpperCase()}
                        </p>
                        <p className={`text-lg font-bold ${isToday ? 'text-sky-700 bg-sky-200 w-8 h-8 rounded-full mx-auto flex items-center justify-center' : 'text-slate-800'}`}>
                          {format(day, "d")}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* Time Grid */}
                <div className="relative">
                  {HOURS.map(hour => (
                    <div key={hour} className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-slate-100 min-h-[60px]">
                      {/* Hour label */}
                      <div className="p-1 text-xs text-slate-400 text-right pr-2 pt-1 font-mono">
                        {String(hour).padStart(2, '0')}:00
                      </div>

                      {/* Day cells */}
                      {weekDays.map(day => {
                        const dateStr = format(day, "yyyy-MM-dd");
                        const isToday = dateStr === todayStr;
                        const slotApts = getAptsForSlot(dateStr, hour);
                        const isDropHere = dropTarget?.date === dateStr && dropTarget?.hour === hour;

                        return (
                          <div
                            key={`${dateStr}-${hour}`}
                            className={`border-l border-slate-100 p-0.5 transition-colors relative
                              ${isToday ? 'bg-sky-50/30' : ''}
                              ${isDropHere ? 'bg-sky-100 ring-2 ring-sky-400 ring-inset' : ''}
                            `}
                            onDragOver={(e) => handleDragOver(e, dateStr, hour)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, dateStr, hour)}
                            data-testid={`cell-${dateStr}-${hour}`}
                          >
                            {slotApts.map(apt => {
                              const colors = getStatusColor(apt.status);
                              return (
                                <div
                                  key={apt.id}
                                  draggable={apt.status === 'confirmed'}
                                  onDragStart={(e) => handleDragStart(e, apt)}
                                  onDragEnd={handleDragEnd}
                                  className={`rounded-md border p-1.5 mb-0.5 text-[11px] leading-tight ${colors.bg} ${colors.text}
                                    ${apt.status === 'confirmed' ? 'cursor-grab active:cursor-grabbing hover:shadow-md' : 'cursor-default opacity-70'}
                                    ${apt.priority === 'high' ? 'ring-1 ring-red-400' : ''}
                                    transition-shadow group
                                  `}
                                  title={`${apt.patient_name} — ${apt.reason}\n${apt.patient_phone || ''}`}
                                  data-testid={`apt-block-${apt.id}`}
                                >
                                  {/* Top row: time + drag grip */}
                                  <div className="flex items-center gap-1 mb-0.5">
                                    {apt.status === 'confirmed' && (
                                      <GripVertical className="w-3 h-3 opacity-30 group-hover:opacity-70 flex-shrink-0" />
                                    )}
                                    <span className="font-bold">{apt.time?.slice(0, 5)}</span>
                                    <div className={`w-1.5 h-1.5 rounded-full ${colors.dot} flex-shrink-0`} />
                                  </div>

                                  {/* Patient name */}
                                  <p className="font-semibold truncate">{apt.patient_name || 'Sin nombre'}</p>

                                  {/* Reason */}
                                  <p className="truncate opacity-75">{apt.reason}</p>

                                  {/* Phone + Nota button (show on hover) */}
                                  <div className="flex items-center justify-between mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {apt.patient_phone && (
                                      <span className="flex items-center gap-0.5 text-[10px] opacity-60">
                                        <Phone className="w-2.5 h-2.5" />
                                        {apt.patient_phone}
                                      </span>
                                    )}
                                    {apt.status === 'confirmed' && (
                                      <button
                                        onClick={(e) => { e.stopPropagation(); handleOpenNoteDialog(apt); }}
                                        className="flex items-center gap-0.5 text-[10px] font-medium text-sky-700 hover:text-sky-900 bg-white/60 rounded px-1 py-0.5"
                                        data-testid={`note-btn-${apt.id}`}
                                      >
                                        <Stethoscope className="w-2.5 h-2.5" />
                                        Nota
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right Sidebar: Alerts */}
        <div className="space-y-4">
          <Card className="stat-card" data-testid="recent-alerts-card">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-900">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Alertas
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

          {/* Today's Summary */}
          <Card className="stat-card">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Clock className="w-4 h-4 text-sky-500" />
                Hoy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {(weekAppointments[todayStr] || []).length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-3">Sin citas para hoy</p>
              ) : (
                (weekAppointments[todayStr] || []).map(apt => (
                  <div key={apt.id} className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg">
                    <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${getStatusColor(apt.status).dot}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-900 truncate">{apt.patient_name || 'Sin nombre'}</p>
                      <p className="text-[10px] text-slate-500 truncate">{apt.reason}</p>
                    </div>
                    <span className="text-xs font-mono text-slate-600 flex-shrink-0">{apt.time?.slice(0, 5)}</span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

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
                    {selectedAppointment.date} • {selectedAppointment.time} • {selectedAppointment.reason}
                  </p>
                </div>
              </div>

              {/* Medical History */}
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
