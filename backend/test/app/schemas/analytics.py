from pydantic import BaseModel


class AppointmentsByStatus(BaseModel):
    booked: int = 0
    completed: int = 0
    cancelled: int = 0


class AnalyticsOverview(BaseModel):
    total_documents: int
    total_services: int
    total_staff: int
    active_staff: int
    total_customers: int
    total_appointments: int
    appointments_by_status: AppointmentsByStatus
    appointments_last_7_days: int
    total_chat_sessions: int
    chat_sessions_last_7_days: int
    documents_failed: int
    escalated_chat_sessions: int = 0