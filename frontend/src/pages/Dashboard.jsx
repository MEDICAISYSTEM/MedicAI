import { useState, useEffect } from "react";
import { getDashboardStats, getAppointments, getAlerts } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { 
  Users, 
  Calendar, 
  CalendarCheck, 
  AlertTriangle,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  CalendarDays
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [todayAppointments, setTodayAppointments] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const today = format(new Date(), "yyyy-MM-dd");
      const [statsRes, appointmentsRes, alertsRes] = await Promise.all([
        getDashboardStats(),
        getAppointments({ date: today }),
        getAlerts({ status: "pending" }),
      ]);
      
      setStats(statsRes.data);
      // Sort appointments by time for the daily schedule
      const sortedAppointments = appointmentsRes.data.sort((a, b) => 
        a.time.localeCompare(b.time)
      );
      setTodayAppointments(sortedAppointments);
      setRecentAlerts(alertsRes.data.slice(0, 5));
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      title: "Pacientes Totales",
      value: stats?.total_patients || 0,
      icon: Users,
      color: "sky",
      bgColor: "bg-sky-50",
      iconColor: "text-sky-500",
    },
    {
      title: "Citas Hoy",
      value: stats?.total_appointments_today || 0,
      icon: Calendar,
      color: "emerald",
      bgColor: "bg-emerald-50",
      iconColor: "text-emerald-500",
    },
    {
      title: "Citas Esta Semana",
      value: stats?.total_appointments_week || 0,
      icon: CalendarCheck,
      color: "violet",
      bgColor: "bg-violet-50",
      iconColor: "text-violet-500",
    },
    {
      title: "Alertas Pendientes",
      value: stats?.pending_alerts || 0,
      icon: AlertTriangle,
      color: "amber",
      bgColor: "bg-amber-50",
      iconColor: "text-amber-500",
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
    <div className="space-y-8 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Dashboard
        </h1>
        <p className="text-slate-500 mt-1">
          Resumen de tu clínica - {format(new Date(), "EEEE, d 'de' MMMM", { locale: es })}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <Card 
            key={stat.title} 
            className="stat-card animate-slide-up"
            style={{ animationDelay: `${index * 0.1}s` }}
            data-testid={`stat-card-${index}`}
          >
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">{stat.title}</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {stat.value}
                  </p>
                </div>
                <div className={`w-12 h-12 ${stat.bgColor} rounded-xl flex items-center justify-center`}>
                  <stat.icon className={`w-6 h-6 ${stat.iconColor}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="stat-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Confirmadas</p>
                <p className="text-2xl font-bold text-slate-900">{stats?.confirmed_appointments || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="stat-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center">
                <XCircle className="w-6 h-6 text-red-500" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Canceladas</p>
                <p className="text-2xl font-bold text-slate-900">{stats?.cancelled_appointments || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stat-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-sky-50 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-sky-500" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Tasa de Confirmación</p>
                <p className="text-2xl font-bold text-slate-900">
                  {stats?.confirmed_appointments && stats?.total_appointments_week
                    ? Math.round((stats.confirmed_appointments / stats.total_appointments_week) * 100)
                    : 0}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Two Column Layout - Appointments and Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Appointments */}
        <Card className="stat-card" data-testid="today-appointments-card">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <Clock className="w-5 h-5 text-sky-500" />
              Citas de Hoy
            </CardTitle>
          </CardHeader>
          <CardContent>
            {todayAppointments.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Calendar className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p>No hay citas programadas para hoy</p>
              </div>
            ) : (
              <div className="space-y-3">
                {todayAppointments.slice(0, 5).map((apt) => (
                  <div 
                    key={apt.id} 
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-xl"
                    data-testid={`appointment-${apt.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center">
                        <span className="text-sky-600 font-semibold text-sm">
                          {apt.patient_name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{apt.patient_name || 'Sin nombre'}</p>
                        <p className="text-sm text-slate-500">{apt.reason}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-slate-900">{apt.time}</p>
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
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Alertas Recientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentAlerts.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-300" />
                <p>No hay alertas pendientes</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentAlerts.map((alert) => (
                  <div 
                    key={alert.id} 
                    className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-100 rounded-xl"
                    data-testid={`alert-${alert.id}`}
                  >
                    <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-slate-900">{alert.patient_name || alert.patient_phone}</p>
                        <Badge className={alert.priority === 'high' ? 'badge-error' : 'badge-warning'}>
                          {alert.priority === 'high' ? 'Alta' : 'Normal'}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-600 truncate">{alert.message}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {format(parseISO(alert.created_at), "d MMM, HH:mm", { locale: es })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Daily Schedule Table */}
      <Card className="stat-card" data-testid="daily-schedule-card">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <CalendarDays className="w-5 h-5 text-violet-500" />
            Agenda del Día - {format(new Date(), "EEEE d 'de' MMMM", { locale: es })}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {todayAppointments.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <CalendarDays className="w-16 h-16 mx-auto mb-4 text-slate-300" />
              <p className="text-lg font-medium">Sin citas programadas</p>
              <p className="text-sm">Tu agenda está libre para hoy</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider w-24">Hora</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Paciente</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Motivo</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Teléfono</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {todayAppointments.map((apt, index) => (
                    <tr 
                      key={apt.id} 
                      className={`hover:bg-slate-50 transition-colors ${
                        apt.priority === 'high' ? 'bg-red-50/50' : ''
                      }`}
                      data-testid={`schedule-row-${apt.id}`}
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            apt.status === 'confirmed' ? 'bg-emerald-500' :
                            apt.status === 'cancelled' ? 'bg-red-500' :
                            'bg-amber-500'
                          }`}></div>
                          <span className="font-semibold text-slate-900">{apt.time}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-sky-100 rounded-full flex items-center justify-center">
                            <span className="text-sky-600 font-semibold text-xs">
                              {apt.patient_name?.charAt(0)?.toUpperCase() || '?'}
                            </span>
                          </div>
                          <span className="font-medium text-slate-900">{apt.patient_name || 'Sin nombre'}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-slate-600">{apt.reason}</span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-slate-500 text-sm">{apt.patient_phone || '-'}</span>
                      </td>
                      <td className="py-4 px-4">
                        {getStatusBadge(apt.status)}
                        {apt.priority === 'high' && (
                          <Badge className="badge-error ml-2 text-xs">Urgente</Badge>
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
    </div>
  );
}
