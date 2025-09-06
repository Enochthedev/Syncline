import { API_CONFIG, API_ENDPOINTS } from '@/constants/api'
import AsyncStorage from '@react-native-async-storage/async-storage'

class NotificationService {
    private baseURL = API_CONFIG.baseURL

    async registerToken(token: string): Promise<void> {
        try {
            const authToken = await AsyncStorage.getItem('auth_token')
            if (!authToken) return

            await fetch(`${this.baseURL}/api/v1/notifications/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`,
                },
                body: JSON.stringify({ token, platform: 'mobile' }),
            })
        } catch (error) {
            console.error('Error registering notification token:', error)
        }
    }

    async updatePreferences(preferences: any): Promise<void> {
        try {
            const authToken = await AsyncStorage.getItem('auth_token')
            if (!authToken) return

            await fetch(`${this.baseURL}${API_ENDPOINTS.USER.NOTIFICATIONS}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`,
                },
                body: JSON.stringify(preferences),
            })
        } catch (error) {
            console.error('Error updating notification preferences:', error)
        }
    }
}

export const notificationService = new NotificationService()