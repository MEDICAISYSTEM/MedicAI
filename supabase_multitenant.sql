-- MedicAI - Sistema Multi-tenant (Multi-doctor)
-- Ejecuta este script en el SQL Editor de Supabase

-- 1. Tabla de clínicas/doctores
CREATE TABLE IF NOT EXISTS clinics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) UNIQUE NOT NULL,  -- Código único para el link (DOC001, DRPEREZ, etc.)
    name TEXT NOT NULL,                 -- Nombre del doctor
    clinic_name TEXT,                   -- Nombre del consultorio
    specialty TEXT,                     -- Especialidad
    phone TEXT,                         -- Teléfono del consultorio
    email TEXT,                         -- Email del doctor
    address TEXT,                       -- Dirección
    welcome_message TEXT,               -- Mensaje de bienvenida personalizado
    is_active BOOLEAN DEFAULT TRUE,
    subscription_status TEXT DEFAULT 'active',  -- active, suspended, cancelled
    subscription_start DATE DEFAULT CURRENT_DATE,
    subscription_end DATE,
    notes TEXT,                         -- Notas internas (para super admin)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Agregar clinic_id a admins (doctores que acceden al panel)
ALTER TABLE admins ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE admins ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT FALSE;

-- 3. Agregar clinic_id a todas las tablas existentes
ALTER TABLE patients ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE availability ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);
ALTER TABLE consultation_notes ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES clinics(id);

-- 4. Índices para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_clinics_code ON clinics(code);
CREATE INDEX IF NOT EXISTS idx_clinics_active ON clinics(is_active);
CREATE INDEX IF NOT EXISTS idx_patients_clinic ON patients(clinic_id);
CREATE INDEX IF NOT EXISTS idx_appointments_clinic ON appointments(clinic_id);
CREATE INDEX IF NOT EXISTS idx_conversations_clinic ON conversations(clinic_id);
CREATE INDEX IF NOT EXISTS idx_alerts_clinic ON alerts(clinic_id);
CREATE INDEX IF NOT EXISTS idx_availability_clinic ON availability(clinic_id);

-- 5. RLS para clinics
ALTER TABLE clinics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for clinics" ON clinics FOR ALL USING (true);

-- 6. Crear super admin inicial (TÚ)
-- Primero verificamos si ya existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM admins WHERE is_super_admin = TRUE) THEN
        INSERT INTO admins (id, email, password_hash, name, is_super_admin, created_at)
        VALUES (
            gen_random_uuid(),
            'superadmin@medicai.com',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G8Ht8xDqzKF6Hy', -- password: SuperAdmin123!
            'Super Administrador',
            TRUE,
            NOW()
        );
    END IF;
END $$;

-- 7. Insertar una clínica de ejemplo
INSERT INTO clinics (code, name, clinic_name, specialty, phone, email, welcome_message)
VALUES (
    'DEMO01',
    'Dr. Demo',
    'Consultorio Demo',
    'Medicina General',
    '+521234567890',
    'demo@medicai.com',
    '¡Hola! Soy el asistente del Dr. Demo. ¿En qué puedo ayudarte hoy?'
) ON CONFLICT (code) DO NOTHING;

SELECT 'Multi-tenant setup complete!' as status;
