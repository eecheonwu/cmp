import apiClient from './api'
import type {
    ClinicalRecord,
    ClinicalRecordResponse,
    CreateClinicalRecordRequest,
    UpdateClinicalRecordRequest,
} from '../types/clinical'

// Get clinical record by ID
export const getClinicalRecord = async (recordId: string): Promise<ClinicalRecord> => {
    const response = await apiClient.get<ClinicalRecordResponse>(`/clinical-records/${recordId}`)
    return {
        id: response.data.id,
        appointmentId: response.data.appointment_id,
        patientId: response.data.patient_id,
        doctorId: response.data.doctor_id,
        notes: response.data.notes,
        diagnosis: response.data.diagnosis,
        prescriptions: response.data.prescriptions,
        createdAt: response.data.created_at,
        updatedAt: response.data.updated_at,
    }
}

// Get clinical records by patient ID
export const getClinicalRecordsByPatient = async (patientId: string): Promise<ClinicalRecord[]> => {
    const response = await apiClient.get<ClinicalRecordResponse[]>(
        `/clinical-records/by-patient/${patientId}`
    )
    return response.data.map((r) => ({
        id: r.id,
        appointmentId: r.appointment_id,
        patientId: r.patient_id,
        doctorId: r.doctor_id,
        notes: r.notes,
        diagnosis: r.diagnosis,
        prescriptions: r.prescriptions,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
    }))
}

// Create a new clinical record
export const createClinicalRecord = async (
    data: CreateClinicalRecordRequest
): Promise<ClinicalRecord> => {
    const response = await apiClient.post<ClinicalRecordResponse>('/clinical-records', data)
    return {
        id: response.data.id,
        appointmentId: response.data.appointment_id,
        patientId: response.data.patient_id,
        doctorId: response.data.doctor_id,
        notes: response.data.notes,
        diagnosis: response.data.diagnosis,
        prescriptions: response.data.prescriptions,
        createdAt: response.data.created_at,
        updatedAt: response.data.updated_at,
    }
}

// Update a clinical record
export const updateClinicalRecord = async (
    recordId: string,
    data: UpdateClinicalRecordRequest
): Promise<ClinicalRecord> => {
    const response = await apiClient.patch<ClinicalRecordResponse>(
        `/clinical-records/${recordId}`,
        data
    )
    return {
        id: response.data.id,
        appointmentId: response.data.appointment_id,
        patientId: response.data.patient_id,
        doctorId: response.data.doctor_id,
        notes: response.data.notes,
        diagnosis: response.data.diagnosis,
        prescriptions: response.data.prescriptions,
        createdAt: response.data.created_at,
        updatedAt: response.data.updated_at,
    }
}

// Release lab results (FR-008)
export const releaseLabResults = async (
    recordId: string,
    labResults: string
): Promise<ClinicalRecord> => {
    const response = await apiClient.patch<ClinicalRecordResponse>(
        `/clinical-records/${recordId}/release-lab-results`,
        { lab_results: labResults, released: true }
    )
    return {
        id: response.data.id,
        appointmentId: response.data.appointment_id,
        patientId: response.data.patient_id,
        doctorId: response.data.doctor_id,
        notes: response.data.notes,
        diagnosis: response.data.diagnosis,
        prescriptions: response.data.prescriptions,
        labResultsReleased: true,
        createdAt: response.data.created_at,
        updatedAt: response.data.updated_at,
    }
}