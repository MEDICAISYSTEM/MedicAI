import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { 
  Activity, 
  LayoutDashboard, 
  Calendar, 
  Users, 
  MessageSquare, 
  Clock, 
  AlertTriangle,
  LogOut,
  Menu,
  X,
  Building2,
  Shield,
  Wifi,
  WifiOff,
  QrCode,
  Loader2,
  CheckCircle
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { getMyWhatsAppStatus, getMyWhatsAppQr, createMyWhatsAppInstance, disconnectMyWhatsApp } from "../lib/api";
import { toast } from "sonner";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", exact: true },
  { to: "/appointments", icon: Calendar, label: "Citas" },
  { to: "/patients", icon: Users, label: "Pacientes" },
  { to: "/conversations", icon: MessageSquare, label: "Conversaciones" },
  { to: "/availability", icon: Clock, label: "Disponibilidad" },
  { to: "/alerts", icon: AlertTriangle, label: "Alertas" },
];

const superAdminNav = [
  { to: "/superadmin", icon: Building2, label: "Super Admin" },
];

export default function Layout() {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const admin = JSON.parse(localStorage.getItem("medicai_admin") || "{}");
  const isSuperAdmin = admin.is_super_admin;

  // WhatsApp state (only for non-super-admin doctors)
  const [waStatus, setWaStatus] = useState("loading");
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const [qrCode, setQrCode] = useState("");
  const [qrLoading, setQrLoading] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("medicai_token");
    localStorage.removeItem("medicai_admin");
    navigate("/login");
  };

  // Check WhatsApp status on mount (doctors only)
  useEffect(() => {
    if (isSuperAdmin) return;
    const check = async () => {
      try {
        const res = await getMyWhatsAppStatus();
        setWaStatus(res.data?.instance?.state === "open" ? "connected" : "disconnected");
      } catch { setWaStatus("disconnected"); }
    };
    check();
    // Re-check every 30s
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, [isSuperAdmin]);

  const handleProfileClick = () => {
    if (isSuperAdmin) return;
    setQrDialogOpen(true);
  };

  const handleOpenQrFlow = async () => {
    setQrLoading(true);
    setQrCode("");
    try {
      const statusRes = await getMyWhatsAppStatus();
      if (statusRes.data?.instance?.state === "open") {
        setWaStatus("connected");
        setQrLoading(false);
        return;
      }
      // Always recreate instance to avoid stuck sessions and update webhooks
      const createRes = await createMyWhatsAppInstance();
      if (createRes.data?.qrcode?.base64) {
        setQrCode(createRes.data.qrcode.base64);
      }
    } catch (e) {
      console.error("QR flow error:", e);
      // Fetch backend custom error message if available
      const errMsg = e.response?.data?.detail || "Error al generar código QR";
      toast.error(errMsg);
    } finally {
      setQrLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (window.confirm("¿Desconectar tu WhatsApp del asistente IA?")) {
      try {
        await disconnectMyWhatsApp();
        setWaStatus("disconnected");
        toast.success("WhatsApp desconectado");
      } catch {
        toast.error("Error al desconectar");
      }
    }
  };

  // Polling while QR dialog is open and not yet connected
  useEffect(() => {
    if (!qrDialogOpen || waStatus === "connected" || qrLoading || isSuperAdmin) return;
    const interval = setInterval(async () => {
      try {
        const res = await getMyWhatsAppStatus();
        if (res.data?.instance?.state === "open") {
          setWaStatus("connected");
          toast.success("¡WhatsApp vinculado exitosamente!");
        }
      } catch {}
    }, 4000);
    return () => clearInterval(interval);
  }, [qrDialogOpen, waStatus, qrLoading, isSuperAdmin]);

  const allNavItems = isSuperAdmin ? [...superAdminNav, ...navItems] : navItems;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white border-b border-slate-200 z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-sky-500 rounded-lg flex items-center justify-center shadow-md shadow-sky-500/20">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>MedicAI</span>
          {isSuperAdmin && <Badge className="badge-warning text-xs">Admin</Badge>}
        </div>
        <Button 
          variant="ghost" 
          size="icon"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          data-testid="mobile-menu-btn"
        >
          {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </header>

      {/* Sidebar */}
      <aside 
        className={`fixed inset-y-0 left-0 w-64 bg-white border-r border-slate-200 z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-100">
            <div className="w-10 h-10 bg-sky-500 rounded-xl flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>MedicAI</span>
              {isSuperAdmin && (
                <Badge className="ml-2 badge-warning text-[10px]">Super Admin</Badge>
              )}
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {allNavItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''} ${item.to === '/superadmin' ? 'bg-amber-50 text-amber-700 hover:bg-amber-100' : ''}`
                }
                data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
                {item.to === '/superadmin' && <Shield className="w-3 h-3 ml-auto" />}
              </NavLink>
            ))}
          </nav>

          {/* User Section */}
          <div className="p-4 border-t border-slate-100">
            {/* Profile - clickable for doctors to open WhatsApp QR */}
            <div 
              className={`flex items-center gap-3 px-3 py-2.5 mb-2 rounded-xl transition-all ${
                !isSuperAdmin 
                  ? 'cursor-pointer hover:bg-sky-50 active:scale-[0.98]' 
                  : ''
              }`}
              onClick={handleProfileClick}
              data-testid="profile-section"
            >
              <div className="relative">
                <div className={`w-10 h-10 ${isSuperAdmin ? 'bg-amber-100' : 'bg-sky-100'} rounded-full flex items-center justify-center`}>
                  <span className={`${isSuperAdmin ? 'text-amber-600' : 'text-sky-600'} font-semibold text-sm`}>
                    {admin.name?.charAt(0)?.toUpperCase() || 'A'}
                  </span>
                </div>
                {/* WhatsApp status indicator for doctors */}
                {!isSuperAdmin && waStatus !== "loading" && (
                  <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-white ${
                    waStatus === "connected" ? "bg-emerald-500" : "bg-slate-300"
                  }`} />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{admin.name || 'Admin'}</p>
                <div className="flex items-center gap-1.5">
                  {!isSuperAdmin ? (
                    <p className={`text-[11px] flex items-center gap-1 ${
                      waStatus === "connected" ? "text-emerald-600" : "text-slate-400"
                    }`}>
                      {waStatus === "loading" ? (
                        <><Loader2 className="w-2.5 h-2.5 animate-spin" /> Verificando...</>
                      ) : waStatus === "connected" ? (
                        <><Wifi className="w-2.5 h-2.5" /> WhatsApp activo</>
                      ) : (
                        <><WifiOff className="w-2.5 h-2.5" /> Toca para vincular</>
                      )}
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500 truncate">{admin.email || ''}</p>
                  )}
                </div>
              </div>
              {/* QR icon for doctors */}
              {!isSuperAdmin && (
                <QrCode className="w-4 h-4 text-slate-300 flex-shrink-0" />
              )}
            </div>
            <Button 
              variant="ghost" 
              className="w-full justify-start text-slate-600 hover:text-red-600 hover:bg-red-50"
              onClick={handleLogout}
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 mr-3" />
              Cerrar Sesión
            </Button>
          </div>
        </div>
      </aside>

      {/* Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="lg:pl-64 pt-16 lg:pt-0 min-h-screen">
        <div className="p-6 lg:p-8">
          <Outlet />
        </div>
      </main>

      {/* WhatsApp QR Dialog (doctors only) */}
      {!isSuperAdmin && (
        <Dialog open={qrDialogOpen} onOpenChange={setQrDialogOpen}>
          <DialogContent className="sm:max-w-[420px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-lg">
                <div className="w-8 h-8 bg-[#25D366]/10 rounded-lg flex items-center justify-center">
                  <QrCode className="w-4 h-4 text-[#25D366]" />
                </div>
                Asistente WhatsApp
              </DialogTitle>
            </DialogHeader>
            
            <div className="flex flex-col items-center justify-center py-2">
              {/* Already connected state */}
              {waStatus === "connected" && !qrLoading && (
                <div className="flex flex-col items-center gap-4 w-full">
                  <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center">
                    <CheckCircle className="w-8 h-8 text-emerald-500" />
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-slate-800 text-lg">¡Conectado!</p>
                    <p className="text-sm text-slate-500 mt-1">Tu asistente IA está respondiendo mensajes por WhatsApp.</p>
                  </div>
                  <div className="flex gap-2 w-full mt-2">
                    <Button 
                      variant="outline" 
                      className="flex-1 text-red-600 border-red-200 hover:bg-red-50 text-sm"
                      onClick={handleDisconnect}
                    >
                      <WifiOff className="w-3.5 h-3.5 mr-2" /> Desconectar
                    </Button>
                    <Button className="flex-1 text-sm" onClick={() => setQrDialogOpen(false)}>
                      Cerrar
                    </Button>
                  </div>
                </div>
              )}

              {/* Disconnected — show connect button */}
              {waStatus !== "connected" && !qrLoading && !qrCode && (
                <div className="flex flex-col items-center gap-4 w-full">
                  <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center">
                    <WifiOff className="w-8 h-8 text-slate-400" />
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-slate-800">WhatsApp no vinculado</p>
                    <p className="text-sm text-slate-500 mt-1">Vincula tu número para que el asistente IA responda a tus pacientes automáticamente.</p>
                  </div>
                  <Button 
                    className="w-full bg-[#25D366] hover:bg-[#128C7E] text-white gap-2 mt-2"
                    onClick={handleOpenQrFlow}
                  >
                    <QrCode className="w-4 h-4" /> Generar Código QR
                  </Button>
                </div>
              )}

              {/* Loading QR */}
              {qrLoading && (
                <div className="flex flex-col items-center gap-3 py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-[#25D366]" />
                  <p className="text-sm text-slate-500">Generando código QR...</p>
                </div>
              )}

              {/* QR Code displayed */}
              {!qrLoading && qrCode && waStatus !== "connected" && (
                <div className="flex flex-col items-center gap-4 w-full">
                  <div className="bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
                    <img src={qrCode} alt="WhatsApp QR Code" className="w-[240px] h-[240px] object-contain" />
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3 text-sm text-slate-600 w-full">
                    <p className="font-medium text-slate-700 mb-1.5">Instrucciones:</p>
                    <ol className="list-decimal pl-4 space-y-0.5 text-xs">
                      <li>Abre <strong>WhatsApp</strong> en tu celular</li>
                      <li>Ve a <strong>Menú → Dispositivos Vinculados</strong></li>
                      <li>Toca <strong>"Vincular un dispositivo"</strong></li>
                      <li>Apunta tu cámara a este código QR</li>
                    </ol>
                  </div>
                  <p className="text-xs text-slate-400 flex items-center gap-2">
                    <Loader2 className="w-3 h-3 animate-spin" /> Esperando que escanees el código...
                  </p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
