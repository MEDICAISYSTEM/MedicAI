# MedicAI - PRD (Product Requirements Document)

## Problema Original
Sistema Inteligente de Gestión Médica para clínica que utiliza IA para triaje y gestión de citas vía WhatsApp Business API.

## Arquitectura Implementada

### Stack Tecnológico
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI (Python)
- **Base de Datos**: Supabase (PostgreSQL)
- **IA**: Gemini 3 Flash via Emergent LLM Key
- **Integración**: WhatsApp Business API via Make.com webhooks

### Módulos del Sistema
1. **Módulo de Comunicación**: Webhook `/api/webhook/whatsapp` recibe mensajes de Make.com
2. **Cerebro de IA**: Gemini 3 Flash procesa mensajes, identifica intenciones (cita, urgencia, precio)
3. **Panel Administrativo**: Dashboard completo con autenticación JWT

## Implementado (26 Enero 2025)

### Backend
- [x] Autenticación JWT (login/register)
- [x] CRUD de pacientes
- [x] CRUD de citas con filtros
- [x] CRUD de disponibilidad horaria
- [x] Historial de conversaciones
- [x] Sistema de alertas de urgencia
- [x] Dashboard con estadísticas
- [x] Webhook para WhatsApp/Make.com con IA Gemini

### Frontend
- [x] Login/Register con tabs
- [x] Dashboard con métricas en tiempo real
- [x] Gestión de citas (filtros, edición, eliminación)
- [x] Directorio de pacientes
- [x] Historial de conversaciones con visualización de mensajes
- [x] Configuración de disponibilidad por día
- [x] Panel de alertas con prioridades

### Base de Datos (Supabase)
- admins, patients, appointments, availability, conversations, messages, alerts

## Credenciales de Prueba
- Email: admin@clinica.com
- Password: admin123

## Backlog Pendiente

### P0 (Crítico)
- Ninguno - MVP funcional completo

### P1 (Alta Prioridad)
- [ ] Envío de respuestas de IA de vuelta a WhatsApp via Make.com
- [ ] Creación automática de citas cuando el paciente confirma

### P2 (Mejoras)
- [ ] Notificaciones push para alertas de urgencia
- [ ] Reportes y analytics avanzados
- [ ] Exportación de datos a Excel/PDF
- [ ] Multi-tenancy para múltiples clínicas

## Próximos Pasos
1. Configurar el webhook de respuesta en Make.com para enviar mensajes de vuelta al paciente
2. Implementar lógica de confirmación de citas automática
3. Agregar más intenciones de IA (consulta de resultados, recordatorios)
