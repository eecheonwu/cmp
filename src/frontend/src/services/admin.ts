/**
 * CMP Admin Service.
 *
 * Implements Task 5.4 — Admin Console:
 * - Branch CRUD operations
 * - User role management
 * - Availability management
 * - System settings
 */

import apiClient from './api'
import type {
    Branch,
    CreateBranchRequest,
    UpdateBranchRequest,
    User,
    UpdateUserRoleRequest,
    DoctorAvailability,
    CreateAvailabilityRequest,
    UpdateAvailabilityRequest,
    SystemSettings,
    UpdateSettingsRequest,
} from '../types/admin'

// ── Branch API Functions ─────────────────────────────────────────────────────

export const getBranches = async (): Promise<Branch[]> => {
    const response = await apiClient.get<Branch[]>('/admin/branches')
    return response.data
}

export const getBranch = async (branchId: string): Promise<Branch> => {
    const response = await apiClient.get<Branch>(`/admin/branches/${branchId}`)
    return response.data
}

export const createBranch = async (data: CreateBranchRequest): Promise<Branch> => {
    const response = await apiClient.post<Branch>('/admin/branches', data)
    return response.data
}

export const updateBranch = async (
    branchId: string,
    data: UpdateBranchRequest
): Promise<Branch> => {
    const response = await apiClient.patch<Branch>(`/admin/branches/${branchId}`, data)
    return response.data
}

export const deleteBranch = async (branchId: string): Promise<void> => {
    await apiClient.delete(`/admin/branches/${branchId}`)
}

// ── User API Functions ─────────────────────────────────────────────────────

export const getUsers = async (role?: string): Promise<User[]> => {
    const url = role ? `/admin/users?role=${role}` : '/admin/users'
    const response = await apiClient.get<User[]>(url)
    return response.data
}

export const getUser = async (userId: string): Promise<User> => {
    const response = await apiClient.get<User>(`/admin/users/${userId}`)
    return response.data
}

export const updateUserRole = async (
    userId: string,
    data: UpdateUserRoleRequest
): Promise<User> => {
    const response = await apiClient.patch<User>(`/admin/users/${userId}/role`, data)
    return response.data
}

// ── Availability API Functions ─────────────────────────────────────────────

export const getDoctorAvailability = async (
    branchId?: string,
    doctorId?: string
): Promise<DoctorAvailability[]> => {
    const params = new URLSearchParams()
    if (branchId) params.append('branch_id', branchId)
    if (doctorId) params.append('doctor_id', doctorId)
    const response = await apiClient.get<DoctorAvailability[]>(
        `/admin/availability?${params.toString()}`
    )
    return response.data
}

export const createAvailability = async (
    data: CreateAvailabilityRequest
): Promise<DoctorAvailability> => {
    const response = await apiClient.post<DoctorAvailability>('/admin/availability', data)
    return response.data
}

export const updateAvailability = async (
    availabilityId: string,
    data: UpdateAvailabilityRequest
): Promise<DoctorAvailability> => {
    const response = await apiClient.patch<DoctorAvailability>(
        `/admin/availability/${availabilityId}`,
        data
    )
    return response.data
}

export const deleteAvailability = async (availabilityId: string): Promise<void> => {
    await apiClient.delete(`/admin/availability/${availabilityId}`)
}

// ── System Settings API Functions ───────────────────────────────────────────

export const getSystemSettings = async (): Promise<SystemSettings[]> => {
    const response = await apiClient.get<SystemSettings[]>('/admin/settings')
    return response.data
}

export const updateSystemSettings = async (
    data: UpdateSettingsRequest
): Promise<SystemSettings[]> => {
    const response = await apiClient.patch<SystemSettings[]>('/admin/settings', data)
    return response.data
}