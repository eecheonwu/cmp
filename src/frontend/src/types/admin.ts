/**
 * CMP Admin Types.
 *
 * Implements Task 5.4 — Admin Console:
 * - Branch management types
 * - User management types
 * - Availability management types
 */

// ── Branch Types ───────────────────────────────────────────────────────────────

export interface Branch {
    id: string
    name: string
    address: string
    phone: string
    email: string
    createdAt: string
    updatedAt: string
}

export interface CreateBranchRequest {
    name: string
    address: string
    phone: string
    email: string
}

export interface UpdateBranchRequest {
    name?: string
    address?: string
    phone?: string
    email?: string
}

// ── User Types ───────────────────────────────────────────────────────────────

export type UserRole = 'patient' | 'receptionist' | 'doctor' | 'manager' | 'admin' | 'executive'

export interface User {
    id: string
    phoneNumber: string
    email: string | null
    role: UserRole
    isVerified: boolean
    createdAt: string
    updatedAt: string
}

export interface StaffUser extends User {
    fullName?: string
    specialization?: string
}

export interface UpdateUserRoleRequest {
    role: UserRole
}

// ── Availability Types ───────────────────────────────────────────────────────

export interface DoctorAvailability {
    id: string
    doctorId: string
    branchId: string
    startDatetime: string
    endDatetime: string
    isCancelled: boolean
    createdAt: string
    updatedAt: string
}

export interface CreateAvailabilityRequest {
    doctorId: string
    branchId: string
    startDatetime: string
    endDatetime: string
}

export interface UpdateAvailabilityRequest {
    startDatetime?: string
    endDatetime?: string
    isCancelled?: boolean
}

// ── System Settings Types ─────────────────────────────────────────────────

export interface SystemSettings {
    id: string
    key: string
    value: string
    description: string
    updatedAt: string
}

export interface UpdateSettingsRequest {
    settings: Record<string, string>
}