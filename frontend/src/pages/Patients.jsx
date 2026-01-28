import { useState, useEffect } from "react";
import { getPatients, updatePatient, getMedicalRecord, updateMedicalRecord, getConsultationNotes, createConsultationNote } from "../lib/api";
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
} from "../components/ui/dialog";
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
  Edit2,
  FileText,
  Heart,
  AlertCircle,
  Plus,
  User,
  Droplet,
  X
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Edit patient dialog
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  
  // Medical record dialog
  const [recordDialogOpen, setRecordDialogOpen] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [medicalRecord, setMedicalRecord] = useState(null);
  const [consultationNotes, setConsultationNotes] = useState([]);
  const [loadingRecord, setLoadingRecord] = useState(false);
  
  // New consultation note
  const [newNote, setNewNote] = useState({
    symptoms: "",
    diagnosis: "",
    treatment: "",
    observations: ""
  });

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

  const handleEditPatient = (patient) => {
    setEditingPatient({ ...patient });
    setEditDialogOpen(true);
  };

  const handleSavePatient = async () => {
    try {
      await updatePatient(editingPatient.id, {
        name: editingPatient.name,
        phone: editingPatient.phone
      });
      toast.success("Paciente actualizado");
      setEditDialogOpen(false);
      fetchPatients();
    } catch (error) {
      toast.error("Error al actualizar paciente");
    }
  };

  const handleOpenRecord = async (patient) => {
    setSelectedPatient(patient);
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

  const handleSaveMedicalRecord = async () => {
    try {
      await updateMedicalRecord(selectedPatient.id, medicalRecord);
      toast.success("Expediente actualizado");
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
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-sky-600 font-semibold">
                          {patient.name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-900">
                          {patient.name || 'Sin nombre'}
                        </h3>
                        <p className="text-sm text-slate-500 flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          {patient.phone}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-xs text-slate-400 mb-3">
                    <p className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Registrado: {format(parseISO(patient.created_at), "d MMM yyyy", { locale: es })}
                    </p>
                    {patient.last_interaction && (
                      <p className="mt-1">
                        Última interacción: {format(parseISO(patient.last_interaction), "d MMM, HH:mm", { locale: es })}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="flex-1"
                      onClick={() => handleEditPatient(patient)}
                      data-testid={`edit-patient-${patient.id}`}
                    >
                      <Edit2 className="w-3 h-3 mr-1" />
                      Editar
                    </Button>
                    <Button 
                      size="sm" 
                      className="flex-1 btn-primary"
                      onClick={() => handleOpenRecord(patient)}
                      data-testid={`record-patient-${patient.id}`}
                    >
                      <FileText className="w-3 h-3 mr-1" />
                      Expediente
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Patient Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <User className="w-5 h-5 text-sky-500" />
              Editar Paciente
            </DialogTitle>
          </DialogHeader>
          {editingPatient && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Nombre completo</Label>
                <Input
                  value={editingPatient.name || ""}
                  onChange={(e) => setEditingPatient({ ...editingPatient, name: e.target.value })}
                  placeholder="Nombre del paciente"
                  className="input-base"
                  data-testid="edit-patient-name"
                />
              </div>
              <div className="space-y-2">
                <Label>Teléfono</Label>
                <Input
                  value={editingPatient.phone || ""}
                  onChange={(e) => setEditingPatient({ ...editingPatient, phone: e.target.value })}
                  placeholder="+52 1 XXX XXX XXXX"
                  className="input-base"
                  data-testid="edit-patient-phone"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSavePatient} className="btn-primary" data-testid="save-patient-btn">
              Guardar cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Medical Record Dialog */}
      <Dialog open={recordDialogOpen} onOpenChange={setRecordDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-sky-500" />
              Expediente - {selectedPatient?.name || 'Paciente'}
            </DialogTitle>
          </DialogHeader>
          
          {loadingRecord ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
            </div>
          ) : (
            <Tabs defaultValue="info" className="flex-1 overflow-hidden flex flex-col">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="info" data-testid="tab-info">
                  <Heart className="w-4 h-4 mr-2" />
                  Información Médica
                </TabsTrigger>
                <TabsTrigger value="notes" data-testid="tab-notes">
                  <FileText className="w-4 h-4 mr-2" />
                  Notas de Consulta
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="info" className="flex-1 overflow-auto mt-4">
                <div className="space-y-4">
                  {/* Blood Type & Emergency Contact */}
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
                          <SelectValue placeholder="Seleccionar" />
                        </SelectTrigger>
                        <SelectContent>
                          {BLOOD_TYPES.map((type) => (
                            <SelectItem key={type} value={type}>{type}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Contacto de emergencia</Label>
                      <Input
                        value={medicalRecord?.emergency_contact || ""}
                        onChange={(e) => setMedicalRecord({ ...medicalRecord, emergency_contact: e.target.value })}
                        placeholder="Nombre del contacto"
                        className="input-base"
                      />
                    </div>
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
                  
                  {/* Allergies */}
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-500" />
                      Alergias
                    </Label>
                    <Textarea
                      value={medicalRecord?.allergies || ""}
                      onChange={(e) => setMedicalRecord({ ...medicalRecord, allergies: e.target.value })}
                      placeholder="Ej: Penicilina, mariscos, látex..."
                      className="input-base min-h-[80px]"
                      data-testid="allergies-input"
                    />
                  </div>
                  
                  {/* Pathologies */}
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Heart className="w-4 h-4 text-red-500" />
                      Patologías previas
                    </Label>
                    <Textarea
                      value={medicalRecord?.pathologies || ""}
                      onChange={(e) => setMedicalRecord({ ...medicalRecord, pathologies: e.target.value })}
                      placeholder="Ej: Diabetes tipo 2, hipertensión, asma..."
                      className="input-base min-h-[80px]"
                      data-testid="pathologies-input"
                    />
                  </div>
                  
                  {/* General Notes */}
                  <div className="space-y-2">
                    <Label>Notas generales</Label>
                    <Textarea
                      value={medicalRecord?.notes || ""}
                      onChange={(e) => setMedicalRecord({ ...medicalRecord, notes: e.target.value })}
                      placeholder="Observaciones adicionales del paciente..."
                      className="input-base min-h-[80px]"
                    />
                  </div>
                  
                  <Button onClick={handleSaveMedicalRecord} className="w-full btn-primary" data-testid="save-record-btn">
                    Guardar información médica
                  </Button>
                </div>
              </TabsContent>
              
              <TabsContent value="notes" className="flex-1 overflow-hidden flex flex-col mt-4">
                {/* New Note Form */}
                <Card className="mb-4 border-sky-200 bg-sky-50/50">
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
                          placeholder="Síntomas del paciente..."
                          className="input-base min-h-[60px] text-sm"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Diagnóstico</Label>
                        <Textarea
                          value={newNote.diagnosis}
                          onChange={(e) => setNewNote({ ...newNote, diagnosis: e.target.value })}
                          placeholder="Diagnóstico..."
                          className="input-base min-h-[60px] text-sm"
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
                          className="input-base min-h-[60px] text-sm"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Observaciones</Label>
                        <Textarea
                          value={newNote.observations}
                          onChange={(e) => setNewNote({ ...newNote, observations: e.target.value })}
                          placeholder="Observaciones adicionales..."
                          className="input-base min-h-[60px] text-sm"
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
                      <p>No hay notas de consulta</p>
                    </div>
                  ) : (
                    <div className="space-y-3 pr-4">
                      {consultationNotes.map((note) => (
                        <Card key={note.id} className="border-slate-200">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between mb-3">
                              <Badge className="badge-neutral">
                                {format(parseISO(note.date), "d MMM yyyy", { locale: es })}
                              </Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-3 text-sm">
                              {note.symptoms && (
                                <div>
                                  <p className="font-medium text-slate-700">Síntomas:</p>
                                  <p className="text-slate-600">{note.symptoms}</p>
                                </div>
                              )}
                              {note.diagnosis && (
                                <div>
                                  <p className="font-medium text-slate-700">Diagnóstico:</p>
                                  <p className="text-slate-600">{note.diagnosis}</p>
                                </div>
                              )}
                              {note.treatment && (
                                <div>
                                  <p className="font-medium text-slate-700">Tratamiento:</p>
                                  <p className="text-slate-600">{note.treatment}</p>
                                </div>
                              )}
                              {note.observations && (
                                <div>
                                  <p className="font-medium text-slate-700">Observaciones:</p>
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
    </div>
  );
}
