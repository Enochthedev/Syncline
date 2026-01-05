
import { apiClient } from '../client';
import { User } from '../../types';

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
}

export const authAPI = {
    login: async (username: string, password: string): Promise<TokenResponse> => {
        const { data } = await apiClient.post('/auth/login', { username, password });
        return data;
    },

    register: async (email: string, username: string, password: string, fullName?: string): Promise<User> => {
        const { data } = await apiClient.post('/auth/register', {
            email,
            username,
            password,
            full_name: fullName
        });
        return data;
    },

    refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
        const { data } = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
        return data;
    },
};
