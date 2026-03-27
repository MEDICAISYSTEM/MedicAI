import { useState, useEffect } from "react";
import { getSuperAdminStats, getClinics, createClinic, updateClinic, deleteClinic, createClinicAdmin, getClinicStats, createWhatsAppInstance, getWhatsAppQr, getWhatsAppStatus, deleteWhatsAppInstance } from "../lib/api";
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
  DialogDescription,
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
  XCircle,
  Wifi,
  WifiOff
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export default function SuperAdmin() {
  const [stats, setStats] = useState(null);

  // QR Modal State
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [qrClinic, setQrClinic] = useState(null);
  const [qrCode, setQrCode] = useState("");
  const [qrStatus, setQrStatus] = useState("loading"); // loading, qr, connected, error
  const [clinics, setClinics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  // Dialogs
  const [clinicDialogOpen, setClinicDialogOpen] = useState(false);
  const [adminDialogOpen, setAdminDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingClinic, setEditingClinic] = useState(null);
  const [selectedClinic, setSelectedClinic] = useState(null);
  const [deletingClinic, setDeletingClinic] = useState(null);
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
    consultation_price: "",
    consultation_currency: "MXN",
    notes: "",
    whatsapp_number: "",
    whatsapp_phone_id: "",
    whatsapp_display_name: ""
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
        consultation_price: clinic.consultation_price || "",
        consultation_currency: clinic.consultation_currency || "MXN",
        notes: clinic.notes || "",
        whatsapp_number: clinic.whatsapp_number || "",
        whatsapp_phone_id: clinic.whatsapp_phone_id || "",
        whatsapp_display_name: clinic.whatsapp_display_name || ""
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
        consultation_price: "",
        consultation_currency: "MXN",
        notes: "",
        whatsapp_number: "",
        whatsapp_phone_id: "",
        whatsapp_display_name: ""
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

  const handleOpenDeleteDialog = (clinic) => {
    setDeletingClinic(clinic);
    setDeleteDialogOpen(true);
  };

  const handleDeleteClinic = async () => {
    if (!deletingClinic) return;
    try {
      await deleteClinic(deletingClinic.id);
      toast.success(`${deletingClinic.name} eliminado correctamente`);
      setDeleteDialogOpen(false);
      setDeletingClinic(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Error al eliminar clínica");
    }
  };

  const getWhatsAppStatus = (clinic) => {
    if (clinic.whatsapp_number) {
      return { color: "emerald", label: "Twilio", icon: Wifi };
    } else {
      return { color: "slate", label: "Código", icon: WifiOff };
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

  const handleOpenQrDialog = async (clinic) => {
    setQrClinic(clinic);
    setQrModalOpen(true);
    setQrStatus("loading");
    setQrCode("");

    try {
      // Check existing status first
      const statusRes = await getWhatsAppStatus(clinic.id);
      if (statusRes.data?.instance?.state === "open") {
        setQrStatus("connected");
        return;
      }

      // If not connected, request QR
      const qrRes = await getWhatsAppQr(clinic.id);

      // If instance not found or no QR, create it
      if (qrRes.data?.status === "not_found" || !qrRes.data?.base64) {
        const createRes = await createWhatsAppInstance(clinic.id);
        if (createRes.data?.qrcode?.base64) {
          setQrCode(createRes.data.qrcode.base64);
          setQrStatus("qr");
        } else {
          setQrStatus("error");
        }
      } else {
        setQrCode(qrRes.data.base64);
        setQrStatus("qr");
      }
    } catch (e) {
      console.error(e);
      setQrStatus("error");
    }
  };

  const handleDisconnectWhatsApp = async (clinic) => {
    if (window.confirm("¿Seguro que deseas desconectar el bot de WhatsApp para esta clínica?")) {
      try {
        await deleteWhatsAppInstance(clinic.id);
        toast.success("WhatsApp desconectado");
        await updateClinic(clinic.id, { whatsapp_number: "" });
        fetchData();
      } catch (e) {
        toast.error("Error al desconectar");
      }
    }
  };

  // Polling effect while QR Modal is open
  useEffect(() => {
    let interval;
    if (qrModalOpen && qrStatus === "qr" && qrClinic) {
      interval = setInterval(async () => {
        try {
          const statusRes = await getWhatsAppStatus(qrClinic.id);
          if (statusRes.data?.instance?.state === "open") {
            setQrStatus("connected");
            toast.success("¡Dispositivo vinculado exitosamente!");
            fetchData();
          }
        } catch (e) { }
      }, 4000);
    }
    return () => clearInterval(interval);
  }, [qrModalOpen, qrStatus, qrClinic]);


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
                className={`p-4 rounded-xl border transition-colors ${clinic.is_active ? 'bg-white border-slate-200 hover:border-sky-200' : 'bg-slate-50 border-slate-200 opacity-60'
                  }`}
                data-testid={`clinic-card-${clinic.id}`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-sky-100 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-6 h-6 text-sky-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="font-semibold text-slate-900">{clinic.name}</h3>
                        <Badge className="bg-slate-100 text-slate-600 font-mono text-xs">{clinic.code}</Badge>
                        <Badge className={clinic.is_active ? 'badge-success' : 'badge-error'}>
                          {clinic.is_active ? 'Activa' : 'Inactiva'}
                        </Badge>
                        {(() => {
                          const waStatus = getWhatsAppStatus(clinic);
                          return (
                            <Badge className={`bg-${waStatus.color}-50 text-${waStatus.color}-700 text-xs flex items-center gap-1`}>
                              <waStatus.icon className="w-3 h-3" />
                              {waStatus.label}
                            </Badge>
                          );
                        })()}
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
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-500 hover:text-red-700 hover:bg-red-50 hover:border-red-200"
                        onClick={() => handleOpenDeleteDialog(clinic)}
                        data-testid={`delete-clinic-${clinic.id}`}
                      >
                        <Trash2 className="w-3 h-3" />
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

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Precio de consulta</Label>
                <Input
                  type="number"
                  value={clinicForm.consultation_price}
                  onChange={(e) => setClinicForm({ ...clinicForm, consultation_price: e.target.value })}
                  placeholder="500"
                  className="input-base"
                />
                <p className="text-xs text-slate-500">El bot usará este precio cuando pregunten por costos</p>
              </div>
              <div className="space-y-2">
                <Label>Moneda</Label>
                <select
                  value={clinicForm.consultation_currency}
                  onChange={(e) => setClinicForm({ ...clinicForm, consultation_currency: e.target.value })}
                  className="input-base w-full h-10 rounded-md border border-slate-200 px-3"
                >
                  <option value="MXN">MXN (Pesos mexicanos)</option>
                  <option value="USD">USD (Dólares)</option>
                  <option value="EUR">EUR (Euros)</option>
                </select>
              </div>
            </div>

            {/* WhatsApp Configuration */}
            <div className="p-4 bg-green-50 rounded-xl border border-green-200">
              <p className="text-sm font-semibold text-green-800 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" /></svg>
                WhatsApp Bot (Conexión por Código QR)
              </p>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="space-y-1">
                  <Label className="text-xs">Número Interno (Referencia)</Label>
                  <Input
                    value={clinicForm.whatsapp_number}
                    onChange={(e) => setClinicForm({ ...clinicForm, whatsapp_number: e.target.value })}
                    placeholder="521XXXXXXXXXX"
                    className="input-base font-mono text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Nombre de Display</Label>
                  <Input
                    value={clinicForm.whatsapp_display_name}
                    onChange={(e) => setClinicForm({ ...clinicForm, whatsapp_display_name: e.target.value })}
                    placeholder="Dr. Pérez - Fisioterapia"
                    className="input-base text-sm"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-green-200/60">
                <p className="text-xs text-green-800 mb-3">
                  Para activar el asistente virtual, haz clic en vincular y escanea el código con tu app móvil de WhatsApp.
                </p>
                {editingClinic && editingClinic.whatsapp_number ? (
                  <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-green-200">
                    <span className="text-sm font-medium text-slate-700">📱 Celular Vinculado ({editingClinic.whatsapp_number})</span>
                    <Button type="button" variant="destructive" size="sm" onClick={() => handleDisconnectWhatsApp(editingClinic)}>
                      Desconectar
                    </Button>
                  </div>
                ) : (
                  <div>
                    {editingClinic ? (
                      <Button type="button" onClick={() => handleOpenQrDialog(editingClinic)} className="w-full bg-[#25D366] hover:bg-[#128C7E] text-white flex items-center justify-center gap-2 rounded-lg py-5 shadow-sm transition-all hover:shadow">
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" /></svg>
                        Escanear Código QR para Vincular
                      </Button>
                    ) : (
                      <p className="text-sm text-slate-500 italic">Guarda la clínica primero para poder vincular un celular.</p>
                    )}
                  </div>
                )}
              </div>
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="w-5 h-5" />
              Eliminar Clínica
            </DialogTitle>
            <DialogDescription className="text-slate-600 pt-2">
              ¿Estás seguro de que deseas eliminar a <strong>{deletingClinic?.name}</strong> ({deletingClinic?.code})?
            </DialogDescription>
          </DialogHeader>

          <div className="py-3">
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-700">
                ⚠️ Esta acción desactivará la clínica y el doctor perderá acceso al sistema. Los datos de pacientes y citas se conservarán.
              </p>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => { setDeleteDialogOpen(false); setDeletingClinic(null); }}>
              Cancelar
            </Button>
            <Button
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={handleDeleteClinic}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Sí, eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* WhatsApp QR Dialog */}
      <Dialog open={qrModalOpen} onOpenChange={setQrModalOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Vincular Celular a MedicAI</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-6">
            {qrStatus === "loading" && (
              <div className="flex flex-col items-center text-slate-500 gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-[#25D366]" />
                <p>Generando código QR desde el servidor...</p>
              </div>
            )}

            {qrStatus === "error" && (
              <div className="flex flex-col items-center text-red-500 gap-3 text-center">
                <XCircle className="w-12 h-12" />
                <p>Ocurrió un error al contactar al servidor de WhatsApp. Asegúrate de que las credenciales de la API están configuradas.</p>
              </div>
            )}

            {qrStatus === "qr" && (
              <div className="flex flex-col items-center gap-4 text-center">
                <p className="text-sm text-slate-600">
                  1. Abre WhatsApp en tu celular.<br />
                  2. Toca Menú y selecciona Dispositivos Vinculados.<br />
                  3. Apunta tu cámara a este código.
                </p>
                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
                  {qrCode ? (
                    <img src={qrCode} alt="WhatsApp QR Code" className="w-[250px] h-[250px] object-cover" />
                  ) : (
                    <div className="w-[250px] h-[250px] bg-slate-100 animate-pulse flex items-center justify-center text-xs text-slate-400">QR no disponible</div>
                  )}
                </div>
                <p className="text-xs text-slate-400 flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" /> Esperando conexión...
                </p>
              </div>
            )}

            {qrStatus === "connected" && (
              <div className="flex flex-col items-center text-emerald-600 gap-3 text-center px-4">
                <CheckCircle className="w-16 h-16" />
                <p className="font-semibold text-lg text-slate-800">¡Conexión Exitosa!</p>
                <p className="text-sm text-slate-600">El bot de IA ya tomó el control parcial de la línea y responderá automáticamente.</p>
                <Button className="mt-4 w-full" onClick={() => setQrModalOpen(false)}>Cerrar</Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
