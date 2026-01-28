# MedicAI - PRD (Product Requirements Document)

## Problema Original
Sistema Inteligente de Gestión Médica multi-tenant (SaaS) que utiliza IA para triaje y gestión de citas vía WhatsApp Business API. Diseñado para múltiples doctores/clínicas con datos completamente aislados.

## Arquitectura Implementada

### Stack Tecnológico
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI (Python)
- **Base de Datos**: Supabase (PostgreSQL)
- **IA**: Gemini 3 Flash via Emergent LLM Key
- **Integración**: WhatsApp Business API via Make.com webhooks
- **Autenticación**: JWT con roles (Super Admin / Clinic Admin)

### Módulos del Sistema
1. **Módulo de Comunicación**: Webhook `/api/webhook/whatsapp` recibe mensajes de Make.com
2. **Cerebro de IA**: Gemini 3 Flash procesa mensajes, identifica intenciones (cita, urgencia, precio)
3. **Panel Super Admin**: Gestión de clínicas/doctores, estadísticas globales
4. **Panel Doctor**: Dashboard, gestión de pacientes, citas, expedientes médicos
5. **Multi-tenancy**: Aislamiento completo de datos por clinic_id

## Implementado (28 Enero 2025)

### Sistema Multi-Tenant (SaaS)
- [x] Panel Super Admin para gestión de clínicas
- [x] Creación de cuentas de doctor por clínica
- [x] Links de WhatsApp personalizados por doctor
- [x] Aislamiento de datos completo por clinic_id (VERIFICADO - 19/19 tests)
- [x] Estadísticas filtradas por clínica

### Backend
- [x] Autenticación JWT con roles (Super Admin / Doctor)
- [x] CRUD de pacientes (filtrado por clinic_id)
- [x] CRUD de citas (filtrado por clinic_id)
- [x] CRUD de disponibilidad horaria (filtrado por clinic_id)
- [x] Historial de conversaciones (filtrado por clinic_id)
- [x] Sistema de alertas de urgencia (filtrado por clinic_id)
- [x] Expedientes médicos (Medical Records)
- [x] Notas de consulta
- [x] Dashboard con estadísticas por clínica
- [x] Webhook WhatsApp con detección de código de clínica (#CODE, Ref:CODE, (#CODE))
- [x] WebSocket para notificaciones en tiempo real

### Frontend
- [x] Login con redirección según rol
- [x] Super Admin Dashboard con gestión de clínicas
- [x] Doctor Dashboard con métricas filtradas
- [x] Gestión de citas (filtros, edición, eliminación)
- [x] Directorio de pacientes con expediente médico
- [x] Notas de consulta por paciente
- [x] Historial de conversaciones WhatsApp
- [x] Configuración de disponibilidad por día
- [x] Panel de alertas con prioridades

### Base de Datos (Supabase)
- clinics, admins (con is_super_admin), patients, appointments, availability
- conversations, messages, alerts, medical_records, consultation_notes
- Todas las tablas con clinic_id para multi-tenancy

## Credenciales de Prueba
### Super Admin
- Email: admin@clinica.com
- Password: admin123

### Clínicas de Prueba
- DRCASTELLA (Dr. Hugo Armando Castellano Nuño)
- DEMO01 (Dr. Demo)

## Seguridad (Verificado)
- ✅ Aislamiento de datos: Doctores solo ven datos de su clínica
- ✅ Cross-clinic access: Retorna 404 (no revela existencia)
- ✅ Super Admin: Acceso total a todas las clínicas
- ✅ Protección de endpoints /superadmin/*: 403 para no-super-admins

## Backlog Pendiente

### P0 (Crítico)
- ✅ COMPLETADO - Aislamiento de datos multi-tenant
- ✅ COMPLETADO - Corrección de código WhatsApp

### P1 (Alta Prioridad)
- [ ] Configuración de horarios por doctor desde UI
- [ ] Envío de respuestas de IA de vuelta a WhatsApp via Make.com

### P2 (Mejoras)
- [ ] Gestión automatizada de suscripciones (Stripe)
- [ ] Reportes y analytics avanzados por clínica
- [ ] Exportación de datos a Excel/PDF
- [ ] Notificaciones push para alertas de urgencia

### Refactoring Pendiente
- [ ] Modularizar server.py (~1500 líneas) en routers separados

## Historial de Cambios

### 28 Enero 2025
- Corregido bug de aislamiento de datos: Todas las consultas ahora filtran por clinic_id
- Actualizado formato de link WhatsApp: `Hola, quiero agendar una cita con {Doctor} (#{CODE})`
- Webhook acepta múltiples formatos: #CODE, Ref:CODE, (#CODE)
- 19/19 tests de seguridad pasados

### 26 Enero 2025
- MVP funcional con sistema multi-tenant completo
- Panel Super Admin implementado
- Sistema de expedientes médicos y notas de consulta
