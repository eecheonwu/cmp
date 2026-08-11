// Frontend types for clinical records

// Clinical record type
export interface ClinicalRecord {
    id: string
    appointmentId: string
    patientId: string
    doctorId: string
    notes: string
    diagnosis: string
    prescriptions: string
    labResults?: string
    labResultsReleased?: boolean
    createdAt: string
    updatedAt: string
}

// API request types
export interface CreateClinicalRecordRequest {
    appointment_id: string
    patient_id: string
    notes: string
    diagnosis: string
    prescriptions: string
}

export interface UpdateClinicalRecordRequest {
    notes?: string
    diagnosis?: string
    prescriptions?: string
}

// API response type
export interface ClinicalRecordResponse {
    id: string
    appointment_id: string
    patient_id: string
    doctor_id: string
    notes: string
    diagnosis: string
    prescriptions: string
    created_at: string
    updated_at: string
}

// Patient info for doctor view
export interface PatientInfo {
    id: string
    fullName: string
    dateOfBirth: string
    gender: string
    phoneNumber: string
    email: string
}