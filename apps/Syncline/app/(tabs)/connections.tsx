import React, { useEffect, useState } from 'react';
import { StyleSheet, View, ScrollView, Alert, Linking } from 'react-native';
import { PlatformCard } from '../../components/connections/PlatformCard';
import { connectionsAPI } from '../../src/api/endpoints/connections';
import { Platform, Connection } from '../../src/types';

import { ConnectionModal } from '../../components/ConnectionModal/ConnectionModal';

const PLATFORMS: Platform[] = ['gmail', 'slack', 'discord', 'telegram', 'twitter', 'whatsapp'];

export default function ConnectionsScreen() {
    const [connections, setConnections] = useState<Connection[]>([]);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);

    // TODO: Replace with actual user ID from auth context
    const USER_ID = 'test-user-123';

    useEffect(() => {
        loadConnections();
    }, []);

    const loadConnections = async () => {
        try {
            const data = await connectionsAPI.listConnections(USER_ID);
            // API returns { connections: [...], total: number }
            // Cast string platform to Platform type
            const formattedConnections = (data.connections || []).map(conn => ({
                ...conn,
                platform: conn.platform as Platform,
                status: conn.status as Connection['status'] // Ensure status matches
            }));
            setConnections(formattedConnections);
        } catch (error) {
            console.error('Failed to load connections:', error);
            // Set empty array on error to prevent crash
            setConnections([]);
        }
    };

    const handleConnectPress = (platform: Platform) => {
        setSelectedPlatform(platform);
        setModalVisible(true);
    };

    const handleConnectionComplete = (connectionId: string) => {
        console.log('Connected:', connectionId);
        loadConnections();
        setModalVisible(false);
        setSelectedPlatform(null);
    };

    const handleDisconnect = async (connectionId: string) => {
        try {
            await connectionsAPI.disconnect(connectionId);
            loadConnections();
        } catch (error) {
            Alert.alert('Error', 'Failed to disconnect');
        }
    };

    return (
        <ScrollView style={styles.container}>
            <View style={styles.content}>
                {PLATFORMS.map((platform) => {
                    const connection = connections.find(c => c.platform === platform);

                    return (
                        <PlatformCard
                            key={platform}
                            platform={platform}
                            connection={connection}
                            onConnect={() => handleConnectPress(platform)}
                            onDisconnect={() => connection && handleDisconnect(connection.id)}
                        />
                    );
                })}
            </View>

            {selectedPlatform && (
                <ConnectionModal
                    visible={modalVisible}
                    platform={selectedPlatform}
                    userId={USER_ID}
                    onClose={() => {
                        setModalVisible(false);
                        setSelectedPlatform(null);
                    }}
                    onConnect={handleConnectionComplete}
                />
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    content: {
        padding: 16,
    },
});
