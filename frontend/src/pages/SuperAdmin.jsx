import { useState, useEffect } from "react";
import { getSuperAdminStats, getClinics, createClinic, updateClinic, deleteClinic, createClinicAdmin, getClinicStats } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { 
  Building2, 
  Users, 
  Calendar,
  AlertTriangle,
  Plus,
  Edit2,
  Trash2,
  Loader2,
  Copy,
  ExternalLink,
  UserPlus,
  Activity,
  Search,
  CheckCircle,
  XCircle
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export default function SuperAdmin() {
  const [stats, setStats] = useState(null);
  const [clinics, setClinics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Dialogs
  const [clinicDialogOpen, setClinicDialogOpen] = useState(false);
  const [adminDialogOpen, setAdminDialogOpen] = useState(false);
  const [editingClinic, setEditingClinic] = useState(null);
  const [selectedClinic, setSelectedClinic] = useState(null);
  const [clinicStats, setClinicStats] = useState(null);
  
  // Forms
  const [clinicForm, setClinicForm] = useState({
    code: "",
    name: "",
    clinic_name: "",
    specialty: "",
    phone: "",
    email: "",
    address: "",
    welcome_message: "",
    notes: ""
  });
  
  const [adminForm, setAdminForm] = useState({
    email: "",
    password: "",
    name: ""
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, clinicsRes] = await Promise.all([
        getSuperAdminStats(),
        getClinics()
      ]);
      setStats(statsRes.data);
      setClinics(clinicsRes.data);
    } catch (error) {
      toast.error("Error al cargar datos");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenClinicDialog = (clinic = null) => {
    if (clinic) {
      setEditingClinic(clinic);
      setClinicForm({
        code: clinic.code,
        name: clinic.name,
        clinic_name: clinic.clinic_name || "",
        specialty: clinic.specialty || "",
        phone: clinic.phone || "",
        email: clinic.email || "",
        address: clinic.address || "",
        welcome_message: clinic.welcome_message || "",
        notes: clinic.notes || ""
      });
    } else {
      setEditingClinic(null);
      setClinicForm({
        code: "",
        name: "",
        clinic_name: "",
        specialty: "",
        phone: "",
        email: "",
        address: "",
        welcome_message: "",
        notes: ""
      });
    }
    setClinicDialogOpen(true);
  };

  const handleSaveClinic = async () => {
    if (!clinicForm.code || !clinicForm.name) {
      toast.error("Código y nombre son requeridos");
      return;
    }
    
    try {
      if (editingClinic) {
        await updateClinic(editingClinic.id, clinicForm);
        toast.success("Clínica actualizada");
      } else {
        await createClinic(clinicForm);
        toast.success("Clínica creada exitosamente");
      }
      setClinicDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Error al guardar clínica");
    }
  };

  const handleToggleActive = async (clinic) => {
    try {
      await updateClinic(clinic.id, { is_active: !clinic.is_active });
      toast.success(clinic.is_active ? "Clínica desactivada" : "Clínica activada");
      fetchData();
    } catch (error) {
      toast.error("Error al actualizar estado");
    }
  };

  const handleOpenAdminDialog = async (clinic) => {
    setSelectedClinic(clinic);
    setAdminForm({ email: "", password: "", name: clinic.name });
    
    try {
      const statsRes = await getClinicStats(clinic.id);
      setClinicStats(statsRes.data);
    } catch (error) {
      setClinicStats(null);
    }
    
    setAdminDialogOpen(true);
  };

  const handleCreateAdmin = async () => {
    if (!adminForm.email || !adminForm.password || !adminForm.name) {
      toast.error("Todos los campos son requeridos");
      return;
    }
    
    try {
      await createClinicAdmin(selectedClinic.id, adminForm);
      toast.success("Cuenta de acceso creada exitosamente");
      setAdminDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Error al crear cuenta");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success("Copiado al portapapeles");
  };

  const filteredClinics = clinics.filter(clinic => 
    clinic.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    clinic.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
    clinic.specialty?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const statCards = [
    { title: "Clínicas Totales", value: stats?.total_clinics || 0, icon: Building2, color: "sky" },
    { title: "Clínicas Activas", value: stats?.active_clinics || 0, icon: CheckCircle, color: "emerald" },
    { title: "Pacientes Totales", value: stats?.total_patients || 0, icon: Users, color: "violet" },
    { title: "Citas Totales", value: stats?.total_appointments || 0, icon: Calendar, color: "amber" },
    { title: "Citas Hoy", value: stats?.appointments_today || 0, icon: Activity, color: "sky" },
    { title: "Alertas", value: stats?.pending_alerts || 0, icon: AlertTriangle, color: "red" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="superadmin-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Panel Super Admin
          </h1>
          <p className="text-slate-500 text-sm">Gestión de clínicas y doctores</p>
        </div>
        <Button onClick={() => handleOpenClinicDialog()} className="btn-primary" data-testid="add-clinic-btn">
          <Plus className="w-4 h-4 mr-2" />
          Nueva Clínica
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map((stat) => (
          <Card key={stat.title} className="stat-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 bg-${stat.color}-50 rounded-lg flex items-center justify-center flex-shrink-0`}>
                  <stat.icon className={`w-4 h-4 text-${stat.color}-500`} />
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-900">{stat.value}</p>
                  <p className="text-xs text-slate-500">{stat.title}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Search */}
      <Card className="stat-card">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Buscar por nombre, código o especialidad..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 input-base"
            />
          </div>
        </CardContent>
      </Card>

      {/* Clinics List */}
      <Card className="stat-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-900">
            {filteredClinics.length} clínica{filteredClinics.length !== 1 ? 's' : ''} registrada{filteredClinics.length !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredClinics.map((clinic) => (
              <div 
                key={clinic.id}
                className={`p-4 rounded-xl border transition-colors ${
                  clinic.is_active ? 'bg-white border-slate-200 hover:border-sky-200' : 'bg-slate-50 border-slate-200 opacity-60'
                }`}
                data-testid={`clinic-card-${clinic.id}`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-sky-100 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-6 h-6 text-sky-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-slate-900">{clinic.name}</h3>
                        <Badge className="bg-slate-100 text-slate-600 font-mono text-xs">{clinic.code}</Badge>
                        <Badge className={clinic.is_active ? 'badge-success' : 'badge-error'}>
                          {clinic.is_active ? 'Activa' : 'Inactiva'}
                        </Badge>
                      </div>
                      {clinic.clinic_name && (
                        <p className="text-sm text-slate-600">{clinic.clinic_name}</p>
                      )}
                      {clinic.specialty && (
                        <p className="text-sm text-slate-500">{clinic.specialty}</p>
                      )}
                      <p className="text-xs text-slate-400 mt-1">
                        Registrado: {format(parseISO(clinic.created_at), "d MMM yyyy", { locale: es })}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                    {/* WhatsApp Link */}
                    <div className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg">
                      <span className="text-xs text-slate-500">Link WhatsApp:</span>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-7 px-2"
                        onClick={() => copyToClipboard(clinic.whatsapp_link)}
                      >
                        <Copy className="w-3 h-3 mr-1" />
                        Copiar
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-7 px-2"
                        onClick={() => window.open(clinic.whatsapp_link, '_blank')}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </Button>
                    </div>
                    
                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleOpenAdminDialog(clinic)}
                        data-testid={`manage-clinic-${clinic.id}`}
                      >
                        <UserPlus className="w-3 h-3 mr-1" />
                        Gestionar
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleOpenClinicDialog(clinic)}
                      >
                        <Edit2 className="w-3 h-3" />
                      </Button>
                      <Switch 
                        checked={clinic.is_active}
                        onCheckedChange={() => handleToggleActive(clinic)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Create/Edit Clinic Dialog */}
      <Dialog open={clinicDialogOpen} onOpenChange={setClinicDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-sky-500" />
              {editingClinic ? 'Editar Clínica' : 'Nueva Clínica'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Código único *</Label>
                <Input
                  value={clinicForm.code}
                  onChange={(e) => setClinicForm({ ...clinicForm, code: e.target.value.toUpperCase() })}
                  placeholder="Ej: DRPEREZ, DOC001"
                  className="input-base font-mono"
                  maxLength={10}
                  disabled={!!editingClinic}
                  data-testid="clinic-code-input"
                />
                <p className="text-xs text-slate-500">Este código se usa en el link de WhatsApp</p>
              </div>
              <div className="space-y-2">
                <Label>Nombre del doctor *</Label>
                <Input
                  value={clinicForm.name}
                  onChange={(e) => setClinicForm({ ...clinicForm, name: e.target.value })}
                  placeholder="Dr. Juan Pérez"
                  className="input-base"
                  data-testid="clinic-name-input"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre del consultorio</Label>
                <Input
                  value={clinicForm.clinic_name}
                  onChange={(e) => setClinicForm({ ...clinicForm, clinic_name: e.target.value })}
                  placeholder="Consultorio Médico Pérez"
                  className="input-base"
                />
              </div>
              <div className="space-y-2">
                <Label>Especialidad</Label>
                <Input
                  value={clinicForm.specialty}
                  onChange={(e) => setClinicForm({ ...clinicForm, specialty: e.target.value })}
                  placeholder="Medicina General, Pediatría..."
                  className="input-base"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Teléfono</Label>
                <Input
                  value={clinicForm.phone}
                  onChange={(e) => setClinicForm({ ...clinicForm, phone: e.target.value })}
                  placeholder="+52 1 XXX XXX XXXX"
                  className="input-base"
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  value={clinicForm.email}
                  onChange={(e) => setClinicForm({ ...clinicForm, email: e.target.value })}
                  placeholder="doctor@email.com"
                  className="input-base"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Dirección</Label>
              <Input
                value={clinicForm.address}
                onChange={(e) => setClinicForm({ ...clinicForm, address: e.target.value })}
                placeholder="Calle, número, colonia, ciudad"
                className="input-base"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Mensaje de bienvenida personalizado</Label>
              <Textarea
                value={clinicForm.welcome_message}
                onChange={(e) => setClinicForm({ ...clinicForm, welcome_message: e.target.value })}
                placeholder="¡Hola! Soy el asistente del Dr. Pérez..."
                className="input-base min-h-[80px]"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Notas internas (solo para ti)</Label>
              <Textarea
                value={clinicForm.notes}
                onChange={(e) => setClinicForm({ ...clinicForm, notes: e.target.value })}
                placeholder="Notas sobre el cliente, fecha de pago, etc..."
                className="input-base min-h-[60px]"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setClinicDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSaveClinic} className="btn-primary" data-testid="save-clinic-btn">
              {editingClinic ? 'Guardar cambios' : 'Crear clínica'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manage Clinic / Create Admin Dialog */}
      <Dialog open={adminDialogOpen} onOpenChange={setAdminDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-sky-500" />
              Gestionar: {selectedClinic?.name}
            </DialogTitle>
          </DialogHeader>
          
          {selectedClinic && (
            <Tabs defaultValue="stats" className="mt-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="stats">Estadísticas</TabsTrigger>
                <TabsTrigger value="admin">Crear Acceso</TabsTrigger>
              </TabsList>
              
              <TabsContent value="stats" className="space-y-4 pt-4">
                {clinicStats ? (
                  <div className="grid grid-cols-2 gap-4">
                    <Card className="border-slate-200">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-slate-900">{clinicStats.total_patients}</p>
                        <p className="text-sm text-slate-500">Pacientes</p>
                      </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-slate-900">{clinicStats.total_appointments}</p>
                        <p className="text-sm text-slate-500">Citas Totales</p>
                      </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-slate-900">{clinicStats.appointments_today}</p>
                        <p className="text-sm text-slate-500">Citas Hoy</p>
                      </CardContent>
                    </Card>
                    <Card className="border-slate-200">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-slate-900">{clinicStats.pending_alerts}</p>
                        <p className="text-sm text-slate-500">Alertas</p>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  <p className="text-center text-slate-500 py-4">Sin datos aún</p>
                )}
                
                <div className="p-4 bg-sky-50 rounded-xl">
                  <p className="text-sm font-medium text-slate-700 mb-2">Link de WhatsApp para este doctor:</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-white rounded border text-xs break-all">
                      {selectedClinic.whatsapp_link}
                    </code>
                    <Button size="sm" variant="outline" onClick={() => copyToClipboard(selectedClinic.whatsapp_link)}>
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="admin" className="space-y-4 pt-4">
                <p className="text-sm text-slate-600">
                  Crea una cuenta para que {selectedClinic.name} pueda acceder al panel de administración.
                </p>
                
                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label>Nombre</Label>
                    <Input
                      value={adminForm.name}
                      onChange={(e) => setAdminForm({ ...adminForm, name: e.target.value })}
                      className="input-base"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      value={adminForm.email}
                      onChange={(e) => setAdminForm({ ...adminForm, email: e.target.value })}
                      placeholder="doctor@email.com"
                      className="input-base"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Contraseña</Label>
                    <Input
                      type="password"
                      value={adminForm.password}
                      onChange={(e) => setAdminForm({ ...adminForm, password: e.target.value })}
                      placeholder="Contraseña segura"
                      className="input-base"
                    />
                  </div>
                </div>
                
                <Button onClick={handleCreateAdmin} className="w-full btn-primary">
                  <UserPlus className="w-4 h-4 mr-2" />
                  Crear cuenta de acceso
                </Button>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
