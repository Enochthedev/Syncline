import axios from 'axios';
import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Helper to get the local IP address for development
// In Expo Go, localhost points to the device itself, not the computer
const getBaseUrl = () => {
    if (!__DEV__) {
        return 'https://api.syncline.com/api/v1'; // Production URL
    }

    // For Android Emulator
    if (Platform.OS === 'android') {
        return 'http://10.0.2.2:8000/api/v1';
    }

    // For iOS Simulator or physical device via LAN
    // You might need to replace this with your actual machine IP if localhost doesn't work
    // e.g., 'http://192.168.1.X:8000/api/v1'
    const debuggerHost = Constants.expoConfig?.hostUri;
    const localhost = debuggerHost?.split(':')[0] || 'localhost';
    return `http://${localhost}:8000/api/v1`;
};

export const API_BASE_URL = getBaseUrl();
// Toggle this to true to force mock data, or it will fallback on error
export const MOCK_MODE = true;

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 5000, // Shorter timeout for faster fallback
});

// Mock data store
const MOCK_DATA = {
    '/connections': {
        connections: [
            { id: '1', platform: 'gmail', status: 'active', connected_at: new Date().toISOString() },
            { id: '2', platform: 'slack', status: 'pending' },
            { id: '3', platform: 'discord', status: 'disconnected' },
        ]
    },
    '/messages': {
        messages: [
            { id: '1', platform: 'slack', content: 'Hey team, checking in on the Q4 roadmap.', sender: 'Alice', timestamp: new Date().toISOString() },
            { id: '2', platform: 'gmail', content: 'Attached is the invoice for last month.', sender: 'Bob', timestamp: new Date(Date.now() - 3600000).toISOString(), has_attachments: true },
            { id: '3', platform: 'discord', content: 'Server is down!', sender: 'Charlie', timestamp: new Date(Date.now() - 7200000).toISOString() },
        ]
    },
    '/ai/search': {
        results: [
            { id: '1', platform: 'slack', content: 'Budget meeting notes', sender: 'Alice', timestamp: new Date().toISOString(), sentiment_score: 0.8 },
        ]
    }
};

// TODO: Add auth interceptor here
apiClient.interceptors.request.use(async (config) => {
    if (MOCK_MODE) {
        // Return a promise that resolves to mock data adapter
        config.adapter = async (config) => {
            const path = config.url?.split('?')[0] || '';
            // Simple mock matching
            const mockResponse = Object.entries(MOCK_DATA).find(([key]) => path.includes(key))?.[1];

            return {
                data: mockResponse || {},
                status: 200,
                statusText: 'OK',
                headers: {},
                config,
            };
        };
    }
    // const token = await AsyncStorage.getItem('token');
    // if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});
