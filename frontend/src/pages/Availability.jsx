import { useState, useEffect } from "react";
import { getAvailability, createAvailability, updateAvailability, deleteAvailability } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { 
  Clock, 
  Plus,
  Trash2,
  Edit2,
  Loader2,
  CheckCircle,
  XCircle
} from "lucide-react";

const DAYS = [
  { value: 0, label: "Domingo" },
  { value: 1, label: "Lunes" },
  { value: 2, label: "Martes" },
  { value: 3, label: "Miércoles" },
  { value: 4, label: "Jueves" },
  { value: 5, label: "Viernes" },
  { value: 6, label: "Sábado" },
];

export default function Availability() {
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState(null);
  const [formData, setFormData] = useState({
    day_of_week: 1,
    start_time: "09:00",
    end_time: "17:00",
    is_available: true,
  });

  useEffect(() => {
    fetchAvailability();
  }, []);

  const fetchAvailability = async () => {
    try {
      const response = await getAvailability();
      setSlots(response.data);
    } catch (error) {
      toast.error("Error al cargar la disponibilidad");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (slot = null, defaultDay = null) => {
    if (slot) {
      setEditingSlot(slot);
      setFormData({
        day_of_week: slot.day_of_week,
        start_time: slot.start_time,
        end_time: slot.end_time,
        is_available: slot.is_available,
      });
    } else {
      setEditingSlot(null);
      setFormData({
        day_of_week: defaultDay !== null ? defaultDay : 1,
        start_time: "09:00",
        end_time: "17:00",
        is_available: true,
      });
    }
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingSlot) {
        await updateAvailability(editingSlot.id, formData);
        toast.success("Horario actualizado");
      } else {
        await createAvailability(formData);
        toast.success("Horario creado");
      }
      setDialogOpen(false);
      fetchAvailability();
    } catch (error) {
      toast.error("Error al guardar el horario");
    }
  };

  const handleDelete = async (slotId) => {
    try {
      await deleteAvailability(slotId);
      toast.success("Horario eliminado");
      fetchAvailability();
    } catch (error) {
      toast.error("Error al eliminar el horario");
    }
  };

  const handleToggleAvailability = async (slot) => {
    try {
      await updateAvailability(slot.id, { 
        ...slot,
        is_available: !slot.is_available 
      });
      toast.success(slot.is_available ? "Horario deshabilitado" : "Horario habilitado");
      fetchAvailability();
    } catch (error) {
      toast.error("Error al actualizar disponibilidad");
    }
  };

  // Group slots by day
  const slotsByDay = DAYS.map((day) => ({
    ...day,
    slots: slots.filter((slot) => slot.day_of_week === day.value),
  }));

  return (
    <div className="space-y-6 animate-fade-in" data-testid="availability-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Disponibilidad
          </h1>
          <p className="text-slate-500 mt-1">Configura los horarios de atención de la clínica</p>
        </div>
        <Button onClick={() => handleOpenDialog()} className="btn-primary" data-testid="add-slot-btn">
          <Plus className="w-4 h-4 mr-2" />
          Agregar Horario
        </Button>
      </div>

      {/* Availability Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {slotsByDay.map((day) => (
            <Card key={day.value} className="stat-card" data-testid={`day-card-${day.value}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                  <Clock className="w-5 h-5 text-sky-500" />
                  {day.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {day.slots.length === 0 ? (
                  <div className="text-center py-6 text-slate-400">
                    <p className="text-sm">Sin horarios configurados</p>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="mt-2 text-sky-500"
                      onClick={() => handleOpenDialog(null, day.value)}
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Agregar
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {day.slots.map((slot) => (
                      <div 
                        key={slot.id}
                        className={`p-3 rounded-xl border transition-colors ${
                          slot.is_available 
                            ? 'bg-emerald-50 border-emerald-100' 
                            : 'bg-slate-50 border-slate-200'
                        }`}
                        data-testid={`slot-${slot.id}`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {slot.is_available ? (
                              <CheckCircle className="w-4 h-4 text-emerald-500" />
                            ) : (
                              <XCircle className="w-4 h-4 text-slate-400" />
                            )}
                            <span className={`font-medium ${slot.is_available ? 'text-emerald-700' : 'text-slate-500'}`}>
                              {slot.start_time} - {slot.end_time}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-8 w-8"
                              onClick={() => handleOpenDialog(slot)}
                              data-testid={`edit-slot-${slot.id}`}
                            >
                              <Edit2 className="w-3 h-3" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50"
                              onClick={() => handleDelete(slot.id)}
                              data-testid={`delete-slot-${slot.id}`}
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                        <div className="mt-2 flex items-center gap-2">
                          <Switch 
                            checked={slot.is_available}
                            onCheckedChange={() => handleToggleAvailability(slot)}
                            data-testid={`toggle-slot-${slot.id}`}
                          />
                          <span className="text-xs text-slate-500">
                            {slot.is_available ? 'Disponible' : 'No disponible'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingSlot ? 'Editar Horario' : 'Agregar Horario'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Día de la semana</Label>
              <Select 
                value={String(formData.day_of_week)} 
                onValueChange={(value) => setFormData({ ...formData, day_of_week: parseInt(value) })}
              >
                <SelectTrigger data-testid="day-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DAYS.map((day) => (
                    <SelectItem key={day.value} value={String(day.value)}>
                      {day.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Hora de inicio</Label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  className="input-base"
                  data-testid="start-time-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Hora de fin</Label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  className="input-base"
                  data-testid="end-time-input"
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch 
                checked={formData.is_available}
                onCheckedChange={(checked) => setFormData({ ...formData, is_available: checked })}
                data-testid="availability-switch"
              />
              <Label>Disponible para citas</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} className="btn-primary" data-testid="save-slot-btn">
              {editingSlot ? 'Guardar cambios' : 'Crear horario'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
