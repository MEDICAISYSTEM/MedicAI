import { useState, useEffect } from "react";
import { getPatients } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { 
  Users, 
  Search, 
  Phone,
  Calendar,
  Loader2
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const response = await getPatients();
      setPatients(response.data);
    } catch (error) {
      toast.error("Error al cargar los pacientes");
    } finally {
      setLoading(false);
    }
  };

  const filteredPatients = patients.filter((patient) => {
    const matchesSearch = 
      patient.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.phone?.includes(searchTerm);
    return matchesSearch;
  });

  return (
    <div className="space-y-6 animate-fade-in" data-testid="patients-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Pacientes
        </h1>
        <p className="text-slate-500 mt-1">Directorio de pacientes registrados</p>
      </div>

      {/* Search */}
      <Card className="stat-card">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Buscar por nombre o teléfono..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 input-base"
              data-testid="search-patients"
            />
          </div>
        </CardContent>
      </Card>

      {/* Patients Grid */}
      <Card className="stat-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-900">
            {filteredPatients.length} paciente{filteredPatients.length !== 1 ? 's' : ''} registrado{filteredPatients.length !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
            </div>
          ) : filteredPatients.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Users className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p>No se encontraron pacientes</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredPatients.map((patient) => (
                <div 
                  key={patient.id} 
                  className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors"
                  data-testid={`patient-card-${patient.id}`}
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-sky-600 font-semibold">
                        {patient.name?.charAt(0)?.toUpperCase() || '?'}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-900 truncate">
                        {patient.name || 'Sin nombre'}
                      </h3>
                      <p className="text-sm text-slate-500 flex items-center gap-1 mt-1">
                        <Phone className="w-3 h-3" />
                        {patient.phone}
                      </p>
                      <p className="text-xs text-slate-400 flex items-center gap-1 mt-2">
                        <Calendar className="w-3 h-3" />
                        Registrado: {format(parseISO(patient.created_at), "d MMM yyyy", { locale: es })}
                      </p>
                      {patient.last_interaction && (
                        <p className="text-xs text-slate-400 mt-1">
                          Última interacción: {format(parseISO(patient.last_interaction), "d MMM, HH:mm", { locale: es })}
                        </p>
                      )}
                    </div>
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
