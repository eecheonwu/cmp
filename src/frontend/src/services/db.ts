import Dexie, { type Table } from 'dexie'

// Appointment type for offline cache
export interface OfflineAppointment {
    id: string
    doctorId: string
    patientId: string
    branchId: string
    startDatetime: string
    endDatetime: string
    status: 'booked' | 'cancelled' | 'completed' | 'no-show'
    paymentState: 'pending' | 'deposit_paid' | 'fully_paid' | 'waived' | 'refunded'
    bookingSource: 'patient' | 'receptionist' | 'admin_override'
    createdAt: string
    updatedAt: string
}

// Doctor availability type for offline cache
export interface OfflineDoctorAvailability {
    id: string
    doctorId: string
    branchId: string
    startDatetime: string
    endDatetime: string
    isCancelled: boolean
    createdAt: string
}

// User type for offline cache
export interface OfflineUser {
    id: string
    phoneNumber: string
    email: string
    role: 'patient' | 'receptionist' | 'doctor' | 'manager' | 'admin' | 'executive'
}

// Dexie database class
export class CMPDatabase extends Dexie {
    appointments!: Table<OfflineAppointment, string>
    doctorAvailability!: Table<OfflineDoctorAvailability, string>
    user!: Table<OfflineUser, string>

    constructor() {
        super('CMPDatabase')
        this.version(1).stores({
            appointments: 'id, doctorId, patientId, branchId, startDatetime, status',
            doctorAvailability: 'id, doctorId, branchId, startDatetime',
            user: 'id, phoneNumber, email, role',
        })
    }
}

// Database instance
export const db = new CMPDatabase()

// Offline cache operations
export const cacheAppointments = async (appointments: OfflineAppointment[]): Promise<void> => {
    await db.appointments.clear()
    await db.appointments.bulkPut(appointments)
}

export const getCachedAppointments = async (): Promise<OfflineAppointment[]> => {
    return await db.appointments.toArray()
}

export const cacheDoctorAvailability = async (availability: OfflineDoctorAvailability[]): Promise<void> => {
    await db.doctorAvailability.clear()
    await db.doctorAvailability.bulkPut(availability)
}

export const getCachedDoctorAvailability = async (): Promise<OfflineDoctorAvailability[]> => {
    return await db.doctorAvailability.toArray()
}

export const cacheUser = async (user: OfflineUser): Promise<void> => {
    await db.user.put(user)
}

export const getCachedUser = async (): Promise<OfflineUser | undefined> => {
    return await db.user.toArray().then(users => users[0])
}

// Clear all data (used on logout)
export const clearOfflineCache = async (): Promise<void> => {
    await db.appointments.clear()
    await db.doctorAvailability.clear()
    await db.user.clear()
}