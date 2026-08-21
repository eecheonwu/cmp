import { useState, useEffect } from 'react'

export function OfflineBanner() {
    const [isOnline, setIsOnline] = useState(navigator.onLine)

    useEffect(() => {
        const handleOnline = () => setIsOnline(true)
        const handleOffline = () => setIsOnline(false)

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    if (isOnline) {
        return null
    }

    return (
        <div className="offline-banner">
            Offline Mode — Read Only. Your data is cached locally. Reconnect to sync changes.
        </div>
    )
}