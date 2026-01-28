-- MedicAI - Tabla de expedientes médicos
-- Ejecuta este script en el SQL Editor de Supabase

-- Tabla de expedientes médicos
CREATE TABLE IF NOT EXISTS medical_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE UNIQUE,
    allergies TEXT,
    pathologies TEXT,
    blood_type TEXT,
    emergency_contact TEXT,
    emergency_phone TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de notas de consulta
CREATE TABLE IF NOT EXISTS consultation_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    symptoms TEXT,
    diagnosis TEXT,
    treatment TEXT,
    observations TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES admins(id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_medical_records_patient ON medical_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_consultation_notes_patient ON consultation_notes(patient_id);
CREATE INDEX IF NOT EXISTS idx_consultation_notes_date ON consultation_notes(date);

-- RLS
ALTER TABLE medical_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE consultation_notes ENABLE ROW LEVEL SECURITY;

-- Políticas
CREATE POLICY "Allow all for medical_records" ON medical_records FOR ALL USING (true);
CREATE POLICY "Allow all for consultation_notes" ON consultation_notes FOR ALL USING (true);

SELECT 'Medical records tables created!' as status;
