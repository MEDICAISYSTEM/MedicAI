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
  Shield
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { useState } from "react";

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

  const handleLogout = () => {
    localStorage.removeItem("medicai_token");
    localStorage.removeItem("medicai_admin");
    navigate("/login");
  };

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
            <div className="flex items-center gap-3 px-3 py-2 mb-2">
              <div className={`w-10 h-10 ${isSuperAdmin ? 'bg-amber-100' : 'bg-sky-100'} rounded-full flex items-center justify-center`}>
                <span className={`${isSuperAdmin ? 'text-amber-600' : 'text-sky-600'} font-semibold text-sm`}>
                  {admin.name?.charAt(0)?.toUpperCase() || 'A'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{admin.name || 'Admin'}</p>
                <p className="text-xs text-slate-500 truncate">{admin.email || ''}</p>
              </div>
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
    </div>
  );
}
