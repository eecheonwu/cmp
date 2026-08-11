// Frontend types for appointments and related entities

// Appointment types
export type AppointmentStatus = 'booked' | 'cancelled' | 'completed' | 'no-show'
export type PaymentStatus = 'pending' | 'deposit_paid' | 'fully_paid' | 'waived' | 'refunded'
export type BookingSource = 'patient' | 'receptionist' | 'admin_override'

export interface Appointment {
    id: string
    doctorId: string
    patientId: string
    branchId: string
    startDatetime: string
    endDatetime: string
    status: AppointmentStatus
    paymentState: PaymentStatus
    bookingSource: BookingSource
    createdAt: string
    updatedAt: string
}

// Branch type
export interface Branch {
    id: string
    name: string
    address: string
    phone: string
    email: string
}

// Doctor type (subset of User)
export interface Doctor {
    id: string
    fullName: string
    specialization?: string
    branchId: string
}

// Available slot type
export interface AvailableSlot {
    start: string
    end: string
    isAvailable: boolean
}

// API request types
export interface BookAppointmentRequest {
    doctorId: string
    branchId: string
    startDatetime: string
    endDatetime: string
}

export interface RescheduleAppointmentRequest {
    startDatetime: string
    endDatetime: string
}

// API response types
export interface CancelAppointmentResponse {
    id: string
    status: AppointmentStatus
    message: string
}