-- MedicAI - WhatsApp Multi-Number Migration
-- Adds per-clinic WhatsApp number fields for independent numbers per doctor
-- Run this in Supabase SQL Editor

-- 1. Add WhatsApp fields to clinics table
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS whatsapp_number TEXT;        -- Full number: 521XXXXXXXXXX (no + prefix)
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS whatsapp_phone_id TEXT;      -- Meta Cloud API Phone ID
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS whatsapp_display_name TEXT;  -- Display name: "Dr. Pérez - Fisioterapia"

-- 2. Unique index for fast webhook lookup by destination number
-- Only index non-null values (clinics that have their own number)
CREATE UNIQUE INDEX IF NOT EXISTS idx_clinics_whatsapp_number 
ON clinics(whatsapp_number) 
WHERE whatsapp_number IS NOT NULL;

-- 3. Verify
SELECT id, code, name, whatsapp_number, whatsapp_phone_id, whatsapp_display_name 
FROM clinics 
ORDER BY created_at;

SELECT 'WhatsApp multi-number migration complete!' as status;
