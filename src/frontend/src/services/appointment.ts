import apiClient from './api'
import type {
    Appointment,
    BookAppointmentRequest,
    RescheduleAppointmentRequest,
    CancelAppointmentResponse,
    AvailableSlot,
    Branch,
    Doctor,
} from '../types/appointment'

// Get all appointments for the current user
export const getAppointments = async (): Promise<Appointment[]> => {
    const response = await apiClient.get<Appointment[]>('/appointments')
    return response.data
}

// Get available slots for a doctor on a specific date
export const getAvailableSlots = async (
    doctorId: string,
    date: string
): Promise<AvailableSlot[]> => {
    const response = await apiClient.get<AvailableSlot[]>(
        `/appointments/available-slots?doctor_id=${doctorId}&date=${date}`
    )
    return response.data
}

// Book a new appointment
export const bookAppointment = async (
    data: BookAppointmentRequest
): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>('/appointments', data)
    return response.data
}

// Cancel an appointment
export const cancelAppointment = async (
    appointmentId: string
): Promise<CancelAppointmentResponse> => {
    const response = await apiClient.delete<CancelAppointmentResponse>(
        `/appointments/${appointmentId}`
    )
    return response.data
}

// Reschedule an appointment
export const rescheduleAppointment = async (
    appointmentId: string,
    data: RescheduleAppointmentRequest
): Promise<Appointment> => {
    const response = await apiClient.patch<Appointment>(
        `/appointments/${appointmentId}`,
        data
    )
    return response.data
}

// Get branches (mock implementation - would call real API)
export const getBranches = async (): Promise<Branch[]> => {
    // In production, this would call the actual API
    // For now, return mock data
    return [
        {
            id: 'branch-1',
            name: 'Main Clinic',
            address: '123 Main Street, Lagos',
            phone: '+234-1-234-5678',
            email: 'main@clinic.com',
        },
        {
            id: 'branch-2',
            name: 'Branch Clinic A',
            address: '456 Branch Avenue, Lagos',
            phone: '+234-1-345-6789',
            email: 'branch-a@clinic.com',
        },
        {
            id: 'branch-3',
            name: 'Branch Clinic B',
            address: '789 Branch Road, Lagos',
            phone: '+234-1-456-7890',
            email: 'branch-b@clinic.com',
        },
    ]
}

// Get doctors by branch (mock implementation - would call real API)
export const getDoctorsByBranch = async (branchId: string): Promise<Doctor[]> => {
    // In production, this would call the actual API
    // For now, return mock data
    return [
        {
            id: 'doctor-1',
            fullName: 'Dr. John Smith',
            specialization: 'General Practitioner',
            branchId,
        },
        {
            id: 'doctor-2',
            fullName: 'Dr. Sarah Johnson',
            specialization: 'Pediatrician',
            branchId,
        },
        {
            id: 'doctor-3',
            fullName: 'Dr. Michael Brown',
            specialization: 'Cardiologist',
            branchId,
        },
    ]
}