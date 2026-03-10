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
  Phone,
  ChevronDown,
  X
} from "lucide-react";
import { format, addDays, subDays, startOfWeek } from "date-fns";
import { es } from "date-fns/locale";

const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const HOURS = Array.from({ length: 14 }, (_, i) => i + 7); // 7:00 - 20:00
const SLOT_HEIGHT = 56; // Fixed pixel height per hour slot

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [weekAppointments, setWeekAppointments] = useState({});
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [draggedApt, setDraggedApt] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const [expandedCard, setExpandedCard] = useState(null);
  const wsRef = useRef(null);

  // Consultation note modal
  const [noteDialogOpen, setNoteDialogOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [savingNote, setSavingNote] = useState(false);
  const [loadingMedicalRecord, setLoadingMedicalRecord] = useState(false);
  const [medicalRecord, setMedicalRecord] = useState(null);
  const [consultationNote, setConsultationNote] = useState({
    symptoms: "", diagnosis: "", treatment: "", observations: ""
  });

  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  }, [weekStart]);

  const todayStr = format(new Date(), "yyyy-MM-dd");

  // All appointments for the week flattened
  const allWeekApts = useMemo(() => {
    return Object.values(weekAppointments).flat();
  }, [weekAppointments]);

  const todayApts = useMemo(() => {
    return weekAppointments[todayStr] || [];
  }, [weekAppointments, todayStr]);

  const fetchData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const [statsRes, alertsRes] = await Promise.all([
        getDashboardStats(),
        getAlerts({ status: "pending" }),
      ]);
      setStats(statsRes.data);
      setRecentAlerts(alertsRes.data.slice(0, 5));

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

  // WebSocket
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
                  <Bell className="w-4 h-4" /> Nueva cita agendada
                </div>
                <p className="text-sm">{apt.patient_name}</p>
                <p className="text-xs text-slate-500">{apt.date} a las {apt.time}</p>
              </div>,
              { duration: 10000, action: { label: "Ver", onClick: () => fetchData(true) } }
            );
            fetchData(true);
          }
        } catch (e) { console.error('WebSocket message error:', e); }
      };
      ws.onclose = () => setTimeout(connectWebSocket, 5000);
      ws.onerror = (error) => console.error('WebSocket error:', error);
      wsRef.current = ws;
    };
    connectWebSocket();
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, [fetchData]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ═══ DRAG AND DROP ═══
  const handleDragStart = (e, apt) => {
    setDraggedApt(apt);
    e.dataTransfer.effectAllowed = "move";
    if (e.target) e.target.style.opacity = "0.4";
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
  const handleDragLeave = () => setDropTarget(null);
  const handleDrop = async (e, dateStr, hour) => {
    e.preventDefault();
    setDropTarget(null);
    if (!draggedApt) return;
    const newTime = `${String(hour).padStart(2, '0')}:00`;
    if (draggedApt.date === dateStr && draggedApt.time === newTime) { setDraggedApt(null); return; }
    try {
      await updateAppointment(draggedApt.id, { date: dateStr, time: newTime });
      toast.success(`Cita movida a ${dateStr} ${newTime}`);
      fetchData(true);
    } catch (error) {
      toast.error("Error al mover la cita");
    }
    setDraggedApt(null);
  };

  // ═══ CONSULTATION NOTES ═══
  const handleOpenNoteDialog = async (appointment) => {
    setSelectedAppointment(appointment);
    setConsultationNote({ symptoms: "", diagnosis: "", treatment: "", observations: "" });
    setMedicalRecord(null);
    setNoteDialogOpen(true);
    setLoadingMedicalRecord(true);
    try {
      const recordRes = await getMedicalRecord(appointment.patient_id);
      setMedicalRecord(recordRes.data);
    } catch {
      setMedicalRecord({ blood_type: "", allergies: "", pathologies: "" });
    } finally {
      setLoadingMedicalRecord(false);
    }
  };

  const handleResolveAlert = async (alertId) => {
    try {
      await updateAlert(alertId, { status: "resolved" });
      setRecentAlerts(prev => prev.filter(a => a.id !== alertId));
      toast.success("Alerta resuelta");
    } catch { toast.error("Error al resolver la alerta"); }
  };

  const handleSaveConsultationNote = async () => {
    if (!consultationNote.symptoms && !consultationNote.diagnosis && !consultationNote.treatment && !consultationNote.observations) {
      toast.error("Agrega al menos un campo a la nota"); return;
    }
    setSavingNote(true);
    try {
      if (medicalRecord && (medicalRecord.blood_type || medicalRecord.allergies || medicalRecord.pathologies)) {
        await updateMedicalRecord(selectedAppointment.patient_id, medicalRecord);
      }
      await createConsultationNote(selectedAppointment.patient_id, {
        ...consultationNote, patient_id: selectedAppointment.patient_id,
        appointment_id: selectedAppointment.id, date: selectedAppointment.date
      });
      toast.success("Nota guardada exitosamente");
      setNoteDialogOpen(false);
    } catch { toast.error("Error al guardar la nota"); }
    finally { setSavingNote(false); }
  };

  // ═══ NAV ═══
  const handlePreviousWeek = () => setWeekStart(prev => subDays(prev, 7));
  const handleNextWeek = () => setWeekStart(prev => addDays(prev, 7));
  const handleThisWeek = () => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const isCurrentWeek = weekDays.some(d => format(d, "yyyy-MM-dd") === todayStr);

  // ═══ STAT CARD CONFIG ═══
  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-800', dot: 'bg-emerald-500' };
      case 'cancelled': return { bg: 'bg-red-50 border-red-200', text: 'text-red-800', dot: 'bg-red-500' };
      case 'pending': return { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-800', dot: 'bg-amber-500' };
      case 'completed': return { bg: 'bg-sky-50 border-sky-200', text: 'text-sky-800', dot: 'bg-sky-500' };
      default: return { bg: 'bg-slate-50 border-slate-200', text: 'text-slate-700', dot: 'bg-slate-400' };
    }
  };

  const statCards = [
    {
      id: "patients", title: "Pacientes", value: stats?.total_patients || 0,
      icon: Users, bgColor: "bg-sky-500",
      expandContent: () => (
        <p className="text-xs text-slate-500 mt-1">Total registrados en tu clínica</p>
      )
    },
    {
      id: "today", title: "Citas Hoy", value: stats?.total_appointments_today || 0,
      icon: CalendarIcon, bgColor: "bg-emerald-500",
      expandContent: () => (
        <div className="mt-2 space-y-1">
          {todayApts.length === 0 ? (
            <p className="text-xs text-slate-400">Sin citas para hoy</p>
          ) : todayApts.slice(0, 3).map(apt => (
            <div key={apt.id} className="flex items-center justify-between text-xs">
              <span className="text-slate-700 truncate flex-1">{apt.patient_name || 'Sin nombre'}</span>
              <span className="text-slate-500 font-mono ml-2">{apt.time?.slice(0, 5)}</span>
            </div>
          ))}
          {todayApts.length > 3 && <p className="text-[10px] text-slate-400">+{todayApts.length - 3} más</p>}
        </div>
      )
    },
    {
      id: "week", title: "Semana", value: stats?.total_appointments_week || 0,
      icon: CalendarCheck, bgColor: "bg-violet-500",
      expandContent: () => (
        <p className="text-xs text-slate-500 mt-1">{allWeekApts.filter(a => a.status === 'confirmed').length} confirmadas esta semana</p>
      )
    },
    {
      id: "alerts", title: "Alertas", value: stats?.pending_alerts || 0,
      icon: AlertTriangle, bgColor: "bg-amber-500",
      expandContent: () => (
        <div className="mt-2 space-y-1.5">
          {recentAlerts.length === 0 ? (
            <p className="text-xs text-emerald-600 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Sin alertas pendientes</p>
          ) : recentAlerts.slice(0, 3).map(alert => (
            <div key={alert.id} className="flex items-center gap-2 text-xs group">
              <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
              <span className="text-slate-700 truncate flex-1">{alert.patient_name || alert.patient_phone}</span>
              <button onClick={(e) => { e.stopPropagation(); handleResolveAlert(alert.id); }}
                className="opacity-0 group-hover:opacity-100 text-emerald-600 hover:text-emerald-800 transition-opacity">
                <Check className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )
    },
    {
      id: "confirmed", title: "Confirmadas", value: stats?.confirmed_appointments || 0,
      icon: CheckCircle, bgColor: "bg-emerald-500",
      expandContent: () => (
        <p className="text-xs text-slate-500 mt-1">Total de citas confirmadas</p>
      )
    },
    {
      id: "cancelled", title: "Canceladas", value: stats?.cancelled_appointments || 0,
      icon: XCircle, bgColor: "bg-red-500",
      expandContent: () => (
        <p className="text-xs text-slate-500 mt-1">Total de citas canceladas</p>
      )
    },
  ];

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
    <div className="space-y-3 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Dashboard
          </h1>
          <p className="text-slate-500 text-sm">
            {format(new Date(), "EEEE, d 'de' MMMM yyyy", { locale: es })}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchData(true)} disabled={refreshing} className="gap-2">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* Interactive Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {statCards.map((stat) => {
          const isExpanded = expandedCard === stat.id;
          return (
            <div
              key={stat.id}
              onClick={() => setExpandedCard(isExpanded ? null : stat.id)}
              className={`relative rounded-xl border bg-white cursor-pointer transition-all duration-200 overflow-hidden
                ${isExpanded
                  ? 'shadow-lg ring-2 ring-sky-200 col-span-2 sm:col-span-1 z-10'
                  : 'shadow-sm hover:shadow-md hover:-translate-y-0.5'
                }
              `}
              data-testid={`stat-card-${stat.id}`}
            >
              <div className="p-3">
                <div className="flex items-center gap-2.5">
                  <div className={`w-8 h-8 ${stat.bgColor} rounded-lg flex items-center justify-center flex-shrink-0`}>
                    <stat.icon className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xl font-bold text-slate-900 leading-none" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {stat.value}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{stat.title}</p>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                </div>

                {/* Expandable content */}
                <div className={`transition-all duration-200 overflow-hidden ${isExpanded ? 'max-h-40 opacity-100 mt-1' : 'max-h-0 opacity-0'}`}>
                  <div className="border-t border-slate-100 pt-2">
                    {stat.expandContent()}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full-Width Weekly Calendar */}
      <Card className="overflow-hidden shadow-sm" data-testid="weekly-calendar-card">
        <CardHeader className="py-2.5 px-4 border-b border-slate-100 bg-white">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <CalendarIcon className="w-4 h-4 text-violet-500" />
              Agenda Semanal
            </CardTitle>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="icon" className="h-7 w-7" onClick={handlePreviousWeek}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button variant="outline" className="h-7 px-2.5 text-xs font-medium" onClick={handleThisWeek}>
                {format(weekStart, "d MMM", { locale: es })} – {format(addDays(weekStart, 6), "d MMM yyyy", { locale: es })}
              </Button>
              <Button variant="outline" size="icon" className="h-7 w-7" onClick={handleNextWeek}>
                <ChevronRight className="w-4 h-4" />
              </Button>
              {!isCurrentWeek && (
                <Button variant="ghost" size="sm" className="h-7 text-xs text-sky-600 ml-1" onClick={handleThisWeek}>
                  Hoy
                </Button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <div className="min-w-[780px]">
              {/* Day Headers — sticky */}
              <div className="grid grid-cols-[50px_repeat(7,1fr)] border-b border-slate-200 bg-slate-50/80 sticky top-0 z-10">
                <div className="p-1.5" />
                {weekDays.map(day => {
                  const dateStr = format(day, "yyyy-MM-dd");
                  const isToday = dateStr === todayStr;
                  const dayAptCount = (weekAppointments[dateStr] || []).length;
                  return (
                    <div key={dateStr} className={`p-1.5 text-center border-l border-slate-200 ${isToday ? 'bg-sky-50/80' : ''}`}>
                      <p className={`text-[10px] font-semibold tracking-wider ${isToday ? 'text-sky-600' : 'text-slate-400'}`}>
                        {format(day, "EEE", { locale: es }).toUpperCase()}
                      </p>
                      <div className="flex items-center justify-center gap-1">
                        <p className={`text-base font-bold leading-none
                          ${isToday ? 'text-white bg-sky-500 w-7 h-7 rounded-full flex items-center justify-center' : 'text-slate-800'}
                        `}>
                          {format(day, "d")}
                        </p>
                        {dayAptCount > 0 && (
                          <span className={`text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center
                            ${isToday ? 'bg-sky-200 text-sky-700' : 'bg-slate-200 text-slate-600'}
                          `}>
                            {dayAptCount}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Time Grid — fixed row heights */}
              <div>
                {HOURS.map(hour => (
                  <div
                    key={hour}
                    className="grid grid-cols-[50px_repeat(7,1fr)] border-b border-slate-50"
                    style={{ height: `${SLOT_HEIGHT}px` }}
                  >
                    {/* Hour label */}
                    <div className="text-[10px] text-slate-400 text-right pr-2 pt-1 font-mono select-none">
                      {String(hour).padStart(2, '0')}:00
                    </div>

                    {/* Day cells — fixed height, overflow hidden */}
                    {weekDays.map(day => {
                      const dateStr = format(day, "yyyy-MM-dd");
                      const isToday = dateStr === todayStr;
                      const slotApts = getAptsForSlot(dateStr, hour);
                      const isDropHere = dropTarget?.date === dateStr && dropTarget?.hour === hour;

                      return (
                        <div
                          key={`${dateStr}-${hour}`}
                          className={`border-l border-slate-100 relative overflow-hidden transition-colors
                            ${isToday ? 'bg-sky-50/20' : ''}
                            ${isDropHere ? 'bg-sky-100 ring-2 ring-inset ring-sky-400' : ''}
                          `}
                          style={{ height: `${SLOT_HEIGHT}px` }}
                          onDragOver={(e) => handleDragOver(e, dateStr, hour)}
                          onDragLeave={handleDragLeave}
                          onDrop={(e) => handleDrop(e, dateStr, hour)}
                        >
                          {slotApts.map((apt, idx) => {
                            const colors = getStatusColor(apt.status);
                            return (
                              <div
                                key={apt.id}
                                draggable={apt.status === 'confirmed'}
                                onDragStart={(e) => handleDragStart(e, apt)}
                                onDragEnd={handleDragEnd}
                                className={`absolute left-0.5 right-0.5 rounded border text-[10px] leading-tight overflow-hidden
                                  ${colors.bg} ${colors.text}
                                  ${apt.status === 'confirmed' ? 'cursor-grab active:cursor-grabbing hover:shadow-md' : 'cursor-default opacity-60'}
                                  ${apt.priority === 'high' ? 'ring-1 ring-red-400' : ''}
                                  transition-shadow group z-[1]
                                `}
                                style={{
                                  top: `${idx * 2}px`,
                                  height: `${SLOT_HEIGHT - 4 - (idx * 2)}px`,
                                  padding: '3px 4px',
                                }}
                                title={`${apt.patient_name || 'Sin nombre'}\n${apt.reason}\n${apt.patient_phone || ''}`}
                              >
                                {/* Row 1: time + grip */}
                                <div className="flex items-center gap-0.5">
                                  {apt.status === 'confirmed' && (
                                    <GripVertical className="w-2.5 h-2.5 opacity-30 group-hover:opacity-70 flex-shrink-0" />
                                  )}
                                  <span className="font-bold">{apt.time?.slice(0, 5)}</span>
                                  <div className={`w-1.5 h-1.5 rounded-full ${colors.dot} flex-shrink-0 ml-auto`} />
                                </div>
                                {/* Row 2: name */}
                                <p className="font-semibold truncate leading-none mt-0.5">{apt.patient_name || 'Sin nombre'}</p>
                                {/* Row 3: reason */}
                                <p className="truncate opacity-70 leading-none mt-0.5">{apt.reason}</p>
                                {/* Hover actions */}
                                <div className="absolute bottom-0.5 left-1 right-1 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                                  {apt.patient_phone && (
                                    <span className="flex items-center gap-0.5 text-[9px] opacity-70">
                                      <Phone className="w-2 h-2" />{apt.patient_phone}
                                    </span>
                                  )}
                                  {apt.status === 'confirmed' && (
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleOpenNoteDialog(apt); }}
                                      className="flex items-center gap-0.5 text-[9px] font-semibold text-sky-700 hover:text-sky-900 bg-white/80 rounded px-1 py-0.5"
                                    >
                                      <Stethoscope className="w-2.5 h-2.5" /> Nota
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

      {/* Consultation Note Dialog — UNCHANGED */}
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

              <div className="p-4 bg-red-50 border border-red-100 rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold text-slate-800 flex items-center gap-2 text-sm">
                    <Heart className="w-4 h-4 text-red-500" /> Antecedentes Médicos
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
                  <div className="flex items-center justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-slate-400" /></div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600 flex items-center gap-1"><Droplet className="w-3 h-3 text-red-500" /> Tipo de sangre</Label>
                      <Select value={medicalRecord?.blood_type || ""} onValueChange={(v) => setMedicalRecord({ ...medicalRecord, blood_type: v })}>
                        <SelectTrigger className="h-8 text-sm bg-white"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                        <SelectContent>{BLOOD_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600 flex items-center gap-1"><AlertCircle className="w-3 h-3 text-amber-500" /> Alergias</Label>
                      <Input value={medicalRecord?.allergies || ""} onChange={(e) => setMedicalRecord({ ...medicalRecord, allergies: e.target.value })} placeholder="Ej: Penicilina..." className="h-8 text-sm bg-white" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600">Patologías</Label>
                      <Input value={medicalRecord?.pathologies || ""} onChange={(e) => setMedicalRecord({ ...medicalRecord, pathologies: e.target.value })} placeholder="Ej: Diabetes..." className="h-8 text-sm bg-white" />
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-sm">Síntomas</Label>
                  <Textarea value={consultationNote.symptoms} onChange={(e) => setConsultationNote({ ...consultationNote, symptoms: e.target.value })} placeholder="Síntomas del paciente..." className="input-base min-h-[90px] text-sm" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm">Diagnóstico</Label>
                  <Textarea value={consultationNote.diagnosis} onChange={(e) => setConsultationNote({ ...consultationNote, diagnosis: e.target.value })} placeholder="Diagnóstico médico..." className="input-base min-h-[90px] text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-sm">Tratamiento</Label>
                  <Textarea value={consultationNote.treatment} onChange={(e) => setConsultationNote({ ...consultationNote, treatment: e.target.value })} placeholder="Tratamiento, medicamentos..." className="input-base min-h-[90px] text-sm" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm">Observaciones</Label>
                  <Textarea value={consultationNote.observations} onChange={(e) => setConsultationNote({ ...consultationNote, observations: e.target.value })} placeholder="Observaciones, seguimiento..." className="input-base min-h-[90px] text-sm" />
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setNoteDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveConsultationNote} className="btn-primary" disabled={savingNote}>
              {savingNote ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Guardando...</>) : (<><FileText className="w-4 h-4 mr-2" /> Guardar</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
