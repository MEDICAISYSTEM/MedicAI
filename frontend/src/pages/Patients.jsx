import { useState, useEffect } from "react";
import { getPatients, updatePatient, getMedicalRecord, updateMedicalRecord, getConsultationNotes, createConsultationNote, deletePatient } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { 
  Users, 
  Search, 
  Phone,
  Calendar,
  Loader2,
  FileText,
  Heart,
  AlertCircle,
  Plus,
  User,
  Droplet,
  Save,
  Trash2
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Expediente dialog
  const [recordDialogOpen, setRecordDialogOpen] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [editablePatient, setEditablePatient] = useState(null);
  const [medicalRecord, setMedicalRecord] = useState(null);
  const [consultationNotes, setConsultationNotes] = useState([]);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [savingPatient, setSavingPatient] = useState(false);
  
  // New consultation note
  const [newNote, setNewNote] = useState({
    symptoms: "",
    diagnosis: "",
    treatment: "",
    observations: ""
  });
  
  // Delete confirmation
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [patientToDelete, setPatientToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

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

  const handleOpenRecord = async (patient) => {
    setSelectedPatient(patient);
    setEditablePatient({ ...patient });
    setRecordDialogOpen(true);
    setLoadingRecord(true);
    
    try {
      const [recordRes, notesRes] = await Promise.all([
        getMedicalRecord(patient.id),
        getConsultationNotes(patient.id)
      ]);
      setMedicalRecord(recordRes.data);
      setConsultationNotes(notesRes.data);
    } catch (error) {
      toast.error("Error al cargar expediente");
    } finally {
      setLoadingRecord(false);
    }
  };

  const handleSavePatientInfo = async () => {
    setSavingPatient(true);
    try {
      await updatePatient(editablePatient.id, {
        name: editablePatient.name,
        phone: editablePatient.phone
      });
      setSelectedPatient(editablePatient);
      toast.success("Datos del paciente actualizados");
      fetchPatients();
    } catch (error) {
      toast.error("Error al guardar datos");
    } finally {
      setSavingPatient(false);
    }
  };

  const handleSaveMedicalRecord = async () => {
    try {
      await updateMedicalRecord(selectedPatient.id, medicalRecord);
      toast.success("Expediente médico actualizado");
    } catch (error) {
      toast.error("Error al guardar expediente");
    }
  };

  const handleAddConsultationNote = async () => {
    if (!newNote.symptoms && !newNote.diagnosis && !newNote.treatment && !newNote.observations) {
      toast.error("Agrega al menos un campo a la nota");
      return;
    }
    
    try {
      const response = await createConsultationNote(selectedPatient.id, {
        ...newNote,
        patient_id: selectedPatient.id
      });
      setConsultationNotes([response.data, ...consultationNotes]);
      setNewNote({ symptoms: "", diagnosis: "", treatment: "", observations: "" });
      toast.success("Nota de consulta agregada");
    } catch (error) {
      toast.error("Error al agregar nota");
    }
  };

  const handleDeleteClick = (patient, e) => {
    e.stopPropagation(); // Prevent opening the record dialog
    setPatientToDelete(patient);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!patientToDelete) return;
    
    setDeleting(true);
    try {
      await deletePatient(patientToDelete.id);
      toast.success(`Paciente ${patientToDelete.name || 'eliminado'} correctamente`);
      setDeleteDialogOpen(false);
      setPatientToDelete(null);
      // Close record dialog if open
      if (selectedPatient?.id === patientToDelete.id) {
        setRecordDialogOpen(false);
      }
      // Refresh patient list
      fetchPatients();
    } catch (error) {
      toast.error("Error al eliminar el paciente");
      console.error("Delete error:", error);
    } finally {
      setDeleting(false);
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
                  className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer group relative"
                  onClick={() => handleOpenRecord(patient)}
                  data-testid={`patient-card-${patient.id}`}
                >
                  {/* Delete button - shown on hover */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-600 hover:bg-red-50"
                    onClick={(e) => handleDeleteClick(patient, e)}
                    data-testid={`delete-patient-${patient.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                  
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-sky-600 font-semibold">
                        {patient.name?.charAt(0)?.toUpperCase() || '?'}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-900 truncate">
                        {patient.name || 'Sin nombre'}
                      </h3>
                      <p className="text-sm text-slate-500 flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        {patient.phone}
                      </p>
                    </div>
                    <FileText className="w-5 h-5 text-sky-500 flex-shrink-0" />
                  </div>
                  
                  <div className="text-xs text-slate-400">
                    <p className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Registrado: {format(parseISO(patient.created_at), "d MMM yyyy", { locale: es })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Expediente Dialog */}
      <Dialog open={recordDialogOpen} onOpenChange={setRecordDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-sky-500" />
              Expediente Médico
            </DialogTitle>
          </DialogHeader>
          
          {loadingRecord ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
            </div>
          ) : (
            <Tabs defaultValue="datos" className="flex-1 overflow-hidden flex flex-col">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="datos" data-testid="tab-datos">
                  <User className="w-4 h-4 mr-2" />
                  Datos Personales
                </TabsTrigger>
                <TabsTrigger value="medico" data-testid="tab-medico">
                  <Heart className="w-4 h-4 mr-2" />
                  Info. Médica
                </TabsTrigger>
                <TabsTrigger value="notas" data-testid="tab-notas">
                  <FileText className="w-4 h-4 mr-2" />
                  Historial Consultas
                </TabsTrigger>
              </TabsList>
              
              {/* Tab: Datos Personales */}
              <TabsContent value="datos" className="flex-1 overflow-auto mt-4">
                <Card className="border-slate-200">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-16 h-16 bg-sky-100 rounded-full flex items-center justify-center">
                        <span className="text-sky-600 font-bold text-2xl">
                          {editablePatient?.name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold text-slate-900">
                          {editablePatient?.name || 'Sin nombre'}
                        </h3>
                        <p className="text-slate-500">{editablePatient?.phone}</p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Nombre completo</Label>
                        <Input
                          value={editablePatient?.name || ""}
                          onChange={(e) => setEditablePatient({ ...editablePatient, name: e.target.value })}
                          placeholder="Nombre del paciente"
                          className="input-base"
                          data-testid="edit-patient-name"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Teléfono</Label>
                        <Input
                          value={editablePatient?.phone || ""}
                          onChange={(e) => setEditablePatient({ ...editablePatient, phone: e.target.value })}
                          placeholder="+52 1 XXX XXX XXXX"
                          className="input-base"
                          data-testid="edit-patient-phone"
                        />
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Contacto de emergencia</Label>
                        <Input
                          value={medicalRecord?.emergency_contact || ""}
                          onChange={(e) => setMedicalRecord({ ...medicalRecord, emergency_contact: e.target.value })}
                          placeholder="Nombre del contacto"
                          className="input-base"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Teléfono de emergencia</Label>
                        <Input
                          value={medicalRecord?.emergency_phone || ""}
                          onChange={(e) => setMedicalRecord({ ...medicalRecord, emergency_phone: e.target.value })}
                          placeholder="+52 1 XXX XXX XXXX"
                          className="input-base"
                        />
                      </div>
                    </div>
                    
                    <div className="flex gap-3 pt-4">
                      <Button 
                        onClick={handleSavePatientInfo} 
                        className="btn-primary"
                        disabled={savingPatient}
                        data-testid="save-patient-btn"
                      >
                        {savingPatient ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        Guardar datos personales
                      </Button>
                      <Button 
                        variant="outline"
                        className="text-red-500 border-red-200 hover:bg-red-50 hover:text-red-600"
                        onClick={() => {
                          setPatientToDelete(selectedPatient);
                          setDeleteDialogOpen(true);
                        }}
                        data-testid="delete-patient-dialog-btn"
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Eliminar paciente
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              
              {/* Tab: Información Médica */}
              <TabsContent value="medico" className="flex-1 overflow-auto mt-4">
                <Card className="border-slate-200">
                  <CardContent className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                          <Droplet className="w-4 h-4 text-red-500" />
                          Tipo de sangre
                        </Label>
                        <Select 
                          value={medicalRecord?.blood_type || ""} 
                          onValueChange={(value) => setMedicalRecord({ ...medicalRecord, blood_type: value })}
                        >
                          <SelectTrigger data-testid="blood-type-select">
                            <SelectValue placeholder="Seleccionar tipo" />
                          </SelectTrigger>
                          <SelectContent>
                            {BLOOD_TYPES.map((type) => (
                              <SelectItem key={type} value={type}>{type}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-500" />
                        Alergias conocidas
                      </Label>
                      <Textarea
                        value={medicalRecord?.allergies || ""}
                        onChange={(e) => setMedicalRecord({ ...medicalRecord, allergies: e.target.value })}
                        placeholder="Ej: Penicilina, mariscos, látex, polen..."
                        className="input-base min-h-[100px]"
                        data-testid="allergies-input"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label className="flex items-center gap-2">
                        <Heart className="w-4 h-4 text-red-500" />
                        Patologías y antecedentes
                      </Label>
                      <Textarea
                        value={medicalRecord?.pathologies || ""}
                        onChange={(e) => setMedicalRecord({ ...medicalRecord, pathologies: e.target.value })}
                        placeholder="Ej: Diabetes tipo 2, hipertensión arterial, asma, cirugías previas..."
                        className="input-base min-h-[100px]"
                        data-testid="pathologies-input"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Notas generales</Label>
                      <Textarea
                        value={medicalRecord?.notes || ""}
                        onChange={(e) => setMedicalRecord({ ...medicalRecord, notes: e.target.value })}
                        placeholder="Observaciones adicionales sobre el paciente..."
                        className="input-base min-h-[80px]"
                      />
                    </div>
                    
                    <Button onClick={handleSaveMedicalRecord} className="btn-primary" data-testid="save-record-btn">
                      <Save className="w-4 h-4 mr-2" />
                      Guardar información médica
                    </Button>
                  </CardContent>
                </Card>
              </TabsContent>
              
              {/* Tab: Historial de Consultas */}
              <TabsContent value="notas" className="flex-1 overflow-hidden flex flex-col mt-4">
                {/* New Note Form */}
                <Card className="mb-4 border-sky-200 bg-sky-50/50 flex-shrink-0">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Plus className="w-4 h-4" />
                      Nueva nota de consulta
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Síntomas</Label>
                        <Textarea
                          value={newNote.symptoms}
                          onChange={(e) => setNewNote({ ...newNote, symptoms: e.target.value })}
                          placeholder="Síntomas que presenta el paciente..."
                          className="input-base min-h-[70px] text-sm"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Diagnóstico</Label>
                        <Textarea
                          value={newNote.diagnosis}
                          onChange={(e) => setNewNote({ ...newNote, diagnosis: e.target.value })}
                          placeholder="Diagnóstico médico..."
                          className="input-base min-h-[70px] text-sm"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Tratamiento</Label>
                        <Textarea
                          value={newNote.treatment}
                          onChange={(e) => setNewNote({ ...newNote, treatment: e.target.value })}
                          placeholder="Tratamiento indicado..."
                          className="input-base min-h-[70px] text-sm"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Observaciones</Label>
                        <Textarea
                          value={newNote.observations}
                          onChange={(e) => setNewNote({ ...newNote, observations: e.target.value })}
                          placeholder="Observaciones adicionales..."
                          className="input-base min-h-[70px] text-sm"
                        />
                      </div>
                    </div>
                    <Button onClick={handleAddConsultationNote} size="sm" className="btn-primary" data-testid="add-note-btn">
                      <Plus className="w-3 h-3 mr-1" />
                      Agregar nota
                    </Button>
                  </CardContent>
                </Card>
                
                {/* Notes List */}
                <ScrollArea className="flex-1">
                  {consultationNotes.length === 0 ? (
                    <div className="text-center py-8 text-slate-500">
                      <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                      <p className="font-medium">Sin historial de consultas</p>
                      <p className="text-sm">Las notas de consulta aparecerán aquí</p>
                    </div>
                  ) : (
                    <div className="space-y-3 pr-4">
                      {consultationNotes.map((note) => (
                        <Card key={note.id} className="border-slate-200 hover:border-sky-200 transition-colors">
                          <CardContent className="p-4">
                            <div className="flex items-center gap-2 mb-3">
                              <Badge className="bg-sky-100 text-sky-700 border-sky-200">
                                <Calendar className="w-3 h-3 mr-1" />
                                {format(parseISO(note.date), "EEEE d 'de' MMMM, yyyy", { locale: es })}
                              </Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              {note.symptoms && (
                                <div className="bg-slate-50 p-3 rounded-lg">
                                  <p className="font-semibold text-slate-700 mb-1">Síntomas</p>
                                  <p className="text-slate-600">{note.symptoms}</p>
                                </div>
                              )}
                              {note.diagnosis && (
                                <div className="bg-slate-50 p-3 rounded-lg">
                                  <p className="font-semibold text-slate-700 mb-1">Diagnóstico</p>
                                  <p className="text-slate-600">{note.diagnosis}</p>
                                </div>
                              )}
                              {note.treatment && (
                                <div className="bg-slate-50 p-3 rounded-lg">
                                  <p className="font-semibold text-slate-700 mb-1">Tratamiento</p>
                                  <p className="text-slate-600">{note.treatment}</p>
                                </div>
                              )}
                              {note.observations && (
                                <div className="bg-slate-50 p-3 rounded-lg">
                                  <p className="font-semibold text-slate-700 mb-1">Observaciones</p>
                                  <p className="text-slate-600">{note.observations}</p>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="w-5 h-5" />
              Eliminar paciente
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <p>
                  ¿Estás seguro de que deseas eliminar a <strong>{patientToDelete?.name || 'este paciente'}</strong>?
                </p>
                <p className="text-red-500 font-medium">
                  Esta acción eliminará permanentemente:
                </p>
                <ul className="list-disc list-inside text-sm text-slate-600 space-y-1">
                  <li>Todos los datos del paciente</li>
                  <li>Historial de citas</li>
                  <li>Expediente médico</li>
                  <li>Notas de consulta</li>
                  <li>Conversaciones de WhatsApp</li>
                </ul>
                <p className="text-red-600 font-semibold mt-2">
                  Esta acción no se puede deshacer.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
              data-testid="confirm-delete-btn"
            >
              {deleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Eliminando...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Sí, eliminar
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
