import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { login, register } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Activity, Heart, Shield, Loader2 } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [registerData, setRegisterData] = useState({ email: "", password: "", name: "" });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await login(loginData.email, loginData.password);
      localStorage.setItem("medicai_token", response.data.access_token);
      localStorage.setItem("medicai_admin", JSON.stringify(response.data.admin));
      toast.success("¡Bienvenido de vuelta!");
      navigate("/");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await register(registerData.email, registerData.password, registerData.name);
      localStorage.setItem("medicai_token", response.data.access_token);
      localStorage.setItem("medicai_admin", JSON.stringify(response.data.admin));
      toast.success("¡Cuenta creada exitosamente!");
      navigate("/");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Error al registrar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 flex flex-col">
      {/* Header */}
      <header className="p-6">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 bg-sky-500 rounded-xl flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
            MedicAI
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-5xl grid md:grid-cols-2 gap-12 items-center">
          {/* Left Side - Info */}
          <div className="hidden md:block space-y-8">
            <div>
              <h1 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Sistema Inteligente de Gestión Médica
              </h1>
              <p className="mt-4 text-lg text-slate-600 leading-relaxed">
                Gestiona citas, triaje de pacientes y comunicación por WhatsApp con inteligencia artificial.
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-4 p-4 bg-white rounded-2xl border border-slate-100 shadow-sm animate-slide-up" style={{ animationDelay: '0.1s' }}>
                <div className="w-10 h-10 bg-sky-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Activity className="w-5 h-5 text-sky-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Triaje Automático</h3>
                  <p className="text-sm text-slate-500">IA que identifica urgencias y prioriza pacientes</p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 bg-white rounded-2xl border border-slate-100 shadow-sm animate-slide-up" style={{ animationDelay: '0.2s' }}>
                <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Heart className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Gestión de Citas</h3>
                  <p className="text-sm text-slate-500">Agenda automática vía WhatsApp Business</p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 bg-white rounded-2xl border border-slate-100 shadow-sm animate-slide-up" style={{ animationDelay: '0.3s' }}>
                <div className="w-10 h-10 bg-violet-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Shield className="w-5 h-5 text-violet-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Panel Administrativo</h3>
                  <p className="text-sm text-slate-500">Control total de tu clínica en tiempo real</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Side - Auth Card */}
          <Card className="w-full max-w-md mx-auto shadow-xl border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader className="text-center pb-2">
              <div className="md:hidden flex justify-center mb-4">
                <div className="w-12 h-12 bg-sky-500 rounded-xl flex items-center justify-center shadow-lg shadow-sky-500/20">
                  <Activity className="w-6 h-6 text-white" />
                </div>
              </div>
              <CardTitle className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Acceso al Panel
              </CardTitle>
              <CardDescription className="text-slate-500">
                Ingresa a tu cuenta para gestionar la clínica
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="login" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-6">
                  <TabsTrigger value="login" data-testid="login-tab">Iniciar Sesión</TabsTrigger>
                  <TabsTrigger value="register" data-testid="register-tab">Registrarse</TabsTrigger>
                </TabsList>

                <TabsContent value="login">
                  <form onSubmit={handleLogin} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="login-email">Email</Label>
                      <Input
                        id="login-email"
                        type="email"
                        placeholder="admin@clinica.com"
                        value={loginData.email}
                        onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                        className="input-base"
                        data-testid="login-email-input"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="login-password">Contraseña</Label>
                      <Input
                        id="login-password"
                        type="password"
                        placeholder="••••••••"
                        value={loginData.password}
                        onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                        className="input-base"
                        data-testid="login-password-input"
                        required
                      />
                    </div>
                    <Button 
                      type="submit" 
                      className="w-full btn-primary"
                      disabled={loading}
                      data-testid="login-submit-btn"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Ingresando...
                        </>
                      ) : (
                        "Iniciar Sesión"
                      )}
                    </Button>
                  </form>
                </TabsContent>

                <TabsContent value="register">
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="register-name">Nombre</Label>
                      <Input
                        id="register-name"
                        type="text"
                        placeholder="Dr. Juan Pérez"
                        value={registerData.name}
                        onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
                        className="input-base"
                        data-testid="register-name-input"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-email">Email</Label>
                      <Input
                        id="register-email"
                        type="email"
                        placeholder="admin@clinica.com"
                        value={registerData.email}
                        onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                        className="input-base"
                        data-testid="register-email-input"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-password">Contraseña</Label>
                      <Input
                        id="register-password"
                        type="password"
                        placeholder="••••••••"
                        value={registerData.password}
                        onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                        className="input-base"
                        data-testid="register-password-input"
                        required
                      />
                    </div>
                    <Button 
                      type="submit" 
                      className="w-full btn-primary"
                      disabled={loading}
                      data-testid="register-submit-btn"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Creando cuenta...
                        </>
                      ) : (
                        "Crear Cuenta"
                      )}
                    </Button>
                  </form>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="p-6 text-center text-sm text-slate-500">
        <p>© 2024 MedicAI - Sistema de Gestión Médica con IA</p>
      </footer>
    </div>
  );
}
