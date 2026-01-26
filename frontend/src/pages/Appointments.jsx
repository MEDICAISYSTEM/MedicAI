import { useState, useEffect } from "react";
import { getAppointments, updateAppointment, deleteAppointment } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Calendar } from "../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { 
  Calendar as CalendarIcon, 
  Search, 
  Filter, 
  MoreVertical,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Phone
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { cn } from "../lib/utils";

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedDate, setSelectedDate] = useState(null);
  const [editingAppointment, setEditingAppointment] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  useEffect(() => {
    fetchAppointments();
  }, [selectedDate, statusFilter]);

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedDate) {
        params.date = format(selectedDate, "yyyy-MM-dd");
      }
      if (statusFilter !== "all") {
        params.status = statusFilter;
      }
      const response = await getAppointments(params);
      setAppointments(response.data);
    } catch (error) {
      toast.error("Error al cargar las citas");
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (appointmentId, newStatus) => {
    try {
      await updateAppointment(appointmentId, { status: newStatus });
      toast.success(`Cita ${newStatus === 'confirmed' ? 'confirmada' : newStatus === 'cancelled' ? 'cancelada' : 'actualizada'}`);
      fetchAppointments();
    } catch (error) {
      toast.error("Error al actualizar la cita");
    }
  };

  const handleDelete = async (appointmentId) => {
    try {
      await deleteAppointment(appointmentId);
      toast.success("Cita eliminada");
      fetchAppointments();
    } catch (error) {
      toast.error("Error al eliminar la cita");
    }
  };

  const handleEditSave = async () => {
    try {
      await updateAppointment(editingAppointment.id, {
        date: editingAppointment.date,
        time: editingAppointment.time,
        reason: editingAppointment.reason,
        status: editingAppointment.status,
      });
      toast.success("Cita actualizada");
      setEditDialogOpen(false);
      setEditingAppointment(null);
      fetchAppointments();
    } catch (error) {
      toast.error("Error al actualizar la cita");
    }
  };

  const filteredAppointments = appointments.filter((apt) => {
    const matchesSearch = 
      apt.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      apt.patient_phone?.includes(searchTerm) ||
      apt.reason?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'confirmed':
        return <Badge className="badge-success">Confirmada</Badge>;
      case 'cancelled':
        return <Badge className="badge-error">Cancelada</Badge>;
      case 'pending':
        return <Badge className="badge-warning">Pendiente</Badge>;
      default:
        return <Badge className="badge-neutral">{status}</Badge>;
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high':
        return <Badge className="badge-error">Alta</Badge>;
      case 'normal':
        return <Badge className="badge-neutral">Normal</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="appointments-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Citas
          </h1>
          <p className="text-slate-500 mt-1">Gestiona las citas de tus pacientes</p>
        </div>
      </div>

      {/* Filters */}
      <Card className="stat-card">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Buscar por nombre, teléfono o motivo..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 input-base"
                data-testid="search-appointments"
              />
            </div>

            {/* Date Filter */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    "w-full sm:w-[200px] justify-start text-left font-normal",
                    !selectedDate && "text-muted-foreground"
                  )}
                  data-testid="date-filter-btn"
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedDate ? format(selectedDate, "PPP", { locale: es }) : "Filtrar por fecha"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  locale={es}
                />
                {selectedDate && (
                  <div className="p-2 border-t">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setSelectedDate(null)}
                      className="w-full"
                    >
                      Limpiar filtro
                    </Button>
                  </div>
                )}
              </PopoverContent>
            </Popover>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]" data-testid="status-filter">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="confirmed">Confirmadas</SelectItem>
                <SelectItem value="pending">Pendientes</SelectItem>
                <SelectItem value="cancelled">Canceladas</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Appointments List */}
      <Card className="stat-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-900">
            {filteredAppointments.length} cita{filteredAppointments.length !== 1 ? 's' : ''} encontrada{filteredAppointments.length !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
            </div>
          ) : filteredAppointments.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <CalendarIcon className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p>No se encontraron citas</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Paciente</th>
                    <th>Fecha</th>
                    <th>Hora</th>
                    <th>Motivo</th>
                    <th>Estado</th>
                    <th>Prioridad</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAppointments.map((apt) => (
                    <tr key={apt.id} data-testid={`appointment-row-${apt.id}`}>
                      <td>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center">
                            <span className="text-sky-600 font-semibold text-sm">
                              {apt.patient_name?.charAt(0)?.toUpperCase() || '?'}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{apt.patient_name || 'Sin nombre'}</p>
                            <p className="text-sm text-slate-500 flex items-center gap-1">
                              <Phone className="w-3 h-3" />
                              {apt.patient_phone || 'Sin teléfono'}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td>
                        <p className="text-slate-900">
                          {format(parseISO(apt.date), "d MMM yyyy", { locale: es })}
                        </p>
                      </td>
                      <td>
                        <p className="font-medium text-slate-900">{apt.time}</p>
                      </td>
                      <td>
                        <p className="text-slate-600 max-w-xs truncate">{apt.reason}</p>
                      </td>
                      <td>{getStatusBadge(apt.status)}</td>
                      <td>{getPriorityBadge(apt.priority)}</td>
                      <td className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" data-testid={`apt-actions-${apt.id}`}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem 
                              onClick={() => handleStatusChange(apt.id, 'confirmed')}
                              className="text-emerald-600"
                            >
                              <CheckCircle className="w-4 h-4 mr-2" />
                              Confirmar
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleStatusChange(apt.id, 'cancelled')}
                              className="text-red-600"
                            >
                              <XCircle className="w-4 h-4 mr-2" />
                              Cancelar
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              setEditingAppointment(apt);
                              setEditDialogOpen(true);
                            }}>
                              <Clock className="w-4 h-4 mr-2" />
                              Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleDelete(apt.id)}
                              className="text-red-600"
                            >
                              <XCircle className="w-4 h-4 mr-2" />
                              Eliminar
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Cita</DialogTitle>
          </DialogHeader>
          {editingAppointment && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Fecha</label>
                <Input
                  type="date"
                  value={editingAppointment.date}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, date: e.target.value })}
                  className="input-base"
                  data-testid="edit-date-input"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Hora</label>
                <Input
                  type="time"
                  value={editingAppointment.time}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, time: e.target.value })}
                  className="input-base"
                  data-testid="edit-time-input"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Motivo</label>
                <Input
                  value={editingAppointment.reason}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, reason: e.target.value })}
                  className="input-base"
                  data-testid="edit-reason-input"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Estado</label>
                <Select 
                  value={editingAppointment.status} 
                  onValueChange={(value) => setEditingAppointment({ ...editingAppointment, status: value })}
                >
                  <SelectTrigger data-testid="edit-status-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="confirmed">Confirmada</SelectItem>
                    <SelectItem value="pending">Pendiente</SelectItem>
                    <SelectItem value="cancelled">Cancelada</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleEditSave} className="btn-primary" data-testid="save-edit-btn">
              Guardar cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
