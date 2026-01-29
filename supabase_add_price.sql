-- Add consultation price columns to clinics table
-- Run this in your Supabase SQL Editor

ALTER TABLE clinics 
ADD COLUMN IF NOT EXISTS consultation_price DECIMAL(10,2) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS consultation_currency VARCHAR(10) DEFAULT 'MXN';

-- Verify the columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'clinics' 
AND column_name IN ('consultation_price', 'consultation_currency');
