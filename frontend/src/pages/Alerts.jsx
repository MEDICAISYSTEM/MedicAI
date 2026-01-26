import { useState, useEffect } from "react";
import { getAlerts, updateAlert } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { 
  AlertTriangle, 
  Search, 
  Phone,
  Clock,
  Loader2,
  CheckCircle,
  Filter
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== "all") {
        params.status = statusFilter;
      }
      const response = await getAlerts(params);
      setAlerts(response.data);
    } catch (error) {
      toast.error("Error al cargar las alertas");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsResolved = async (alertId) => {
    try {
      await updateAlert(alertId, { status: "resolved" });
      toast.success("Alerta marcada como resuelta");
      fetchAlerts();
    } catch (error) {
      toast.error("Error al actualizar la alerta");
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch = 
      alert.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      alert.patient_phone?.includes(searchTerm) ||
      alert.message?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
        return 'bg-red-50 border-red-200';
      case 'medium':
        return 'bg-amber-50 border-amber-200';
      default:
        return 'bg-slate-50 border-slate-200';
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="alerts-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Alertas
        </h1>
        <p className="text-slate-500 mt-1">Urgencias y notificaciones importantes de pacientes</p>
      </div>

      {/* Filters */}
      <Card className="stat-card">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Buscar por paciente o mensaje..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 input-base"
                data-testid="search-alerts"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]" data-testid="status-filter">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="pending">Pendientes</SelectItem>
                <SelectItem value="resolved">Resueltas</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Alerts List */}
      <Card className="stat-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            {filteredAlerts.length} alerta{filteredAlerts.length !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-300" />
              <p className="font-medium">¡Todo en orden!</p>
              <p className="text-sm">No hay alertas pendientes</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredAlerts.map((alert) => (
                <div 
                  key={alert.id}
                  className={`p-4 rounded-xl border ${getPriorityColor(alert.priority)} transition-colors`}
                  data-testid={`alert-card-${alert.id}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      alert.priority === 'high' ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <AlertTriangle className={`w-6 h-6 ${
                        alert.priority === 'high' ? 'text-red-600' : 'text-amber-600'
                      }`} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className="font-semibold text-slate-900">
                          {alert.patient_name || 'Paciente sin nombre'}
                        </span>
                        <Badge className={alert.priority === 'high' ? 'badge-error' : 'badge-warning'}>
                          {alert.priority === 'high' ? 'Urgente' : 'Normal'}
                        </Badge>
                        <Badge className={alert.status === 'pending' ? 'badge-warning' : 'badge-success'}>
                          {alert.status === 'pending' ? 'Pendiente' : 'Resuelta'}
                        </Badge>
                      </div>
                      
                      <p className="text-slate-600 mb-2">{alert.message}</p>
                      
                      <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          {alert.patient_phone}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {format(parseISO(alert.created_at), "d MMM yyyy, HH:mm", { locale: es })}
                        </span>
                      </div>
                    </div>

                    {alert.status === 'pending' && (
                      <Button 
                        onClick={() => handleMarkAsResolved(alert.id)}
                        className="btn-primary flex-shrink-0"
                        data-testid={`resolve-alert-${alert.id}`}
                      >
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Marcar resuelta
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
