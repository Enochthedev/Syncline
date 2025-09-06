/**
 * Network Status Hook
 * 
 * Monitors network connectivity and provides network state information
 */

import { useState, useEffect, useCallback } from 'react';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';

export interface NetworkStatus {
    isConnected: boolean;
    isInternetReachable: boolean | null;
    type: string | null;
    isWifi: boolean;
    isCellular: boolean;
    isSlowConnection: boolean;
}

export const useNetworkStatus = () => {
    const [networkStatus, setNetworkStatus] = useState<NetworkStatus>({
        isConnected: true,
        isInternetReachable: null,
        type: null,
        isWifi: false,
        isCellular: false,
        isSlowConnection: false,
    });

    const [isOnline, setIsOnline] = useState(true);

    const updateNetworkStatus = useCallback((state: NetInfoState) => {
        const isConnected = state.isConnected ?? false;
        const isInternetReachable = state.isInternetReachable;
        const type = state.type;
        const isWifi = type === 'wifi';
        const isCellular = type === 'cellular';

        // Consider connection slow if it's cellular with poor details
        const isSlowConnection = isCellular && (
            (state.details as any)?.cellularGeneration === '2g' ||
            (state.details as any)?.strength === 'poor'
        );

        const newStatus: NetworkStatus = {
            isConnected,
            isInternetReachable,
            type,
            isWifi,
            isCellular,
            isSlowConnection,
        };

        setNetworkStatus(newStatus);
        setIsOnline(isConnected && (isInternetReachable !== false));
    }, []);

    useEffect(() => {
        // Get initial network state
        NetInfo.fetch().then(updateNetworkStatus);

        // Subscribe to network state changes
        const unsubscribe = NetInfo.addEventListener(updateNetworkStatus);

        return unsubscribe;
    }, [updateNetworkStatus]);

    const checkConnection = useCallback(async (): Promise<boolean> => {
        try {
            const state = await NetInfo.fetch();
            updateNetworkStatus(state);
            return state.isConnected ?? false;
        } catch (error) {
            console.error('Failed to check network connection:', error);
            return false;
        }
    }, [updateNetworkStatus]);

    return {
        ...networkStatus,
        isOnline,
        checkConnection,
    };
};

// Hook for network-aware API calls
export const useNetworkAwareQuery = () => {
    const { isOnline, isSlowConnection } = useNetworkStatus();

    const getQueryOptions = useCallback(() => {
        if (!isOnline) {
            return {
                enabled: false,
                retry: false,
            };
        }

        if (isSlowConnection) {
            return {
                staleTime: 5 * 60 * 1000, // 5 minutes for slow connections
                cacheTime: 10 * 60 * 1000, // 10 minutes
                retry: 1, // Fewer retries on slow connections
            };
        }

        return {
            staleTime: 2 * 60 * 1000, // 2 minutes for normal connections
            cacheTime: 5 * 60 * 1000, // 5 minutes
            retry: 3,
        };
    }, [isOnline, isSlowConnection]);

    return {
        isOnline,
        isSlowConnection,
        getQueryOptions,
    };
};