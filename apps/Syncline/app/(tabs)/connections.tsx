import React, { useEffect, useState } from 'react';
import { StyleSheet, View, ScrollView, Alert, Linking } from 'react-native';
import { PlatformCard } from '../../components/connections/PlatformCard';
import { connectionsAPI } from '../../src/api/endpoints/connections';
import { Platform, Connection } from '../../src/types';

const PLATFORMS: Platform[] = ['gmail', 'slack', 'discord', 'telegram', 'twitter', 'whatsapp'];

export default function ConnectionsScreen() {
    const [connections, setConnections] = useState<Connection[]>([]);
    const [loading, setLoading] = useState(false);

    // TODO: Replace with actual user ID from auth context
    const USER_ID = 'test-user-123';

    useEffect(() => {
        loadConnections();
    }, []);

    const loadConnections = async () => {
        try {
            const data = await connectionsAPI.listConnections(USER_ID);
            setConnections(data);
        } catch (error) {
            console.error('Failed to load connections:', error);
        }
    };

    const handleConnect = async (platform: Platform) => {
        try {
            setLoading(true);
            const response = await connectionsAPI.initiateConnection(platform, USER_ID);

            if (response.authorization_url) {
                // Open OAuth URL
                await Linking.openURL(response.authorization_url);
            } else {
                Alert.alert('Success', 'Connection initiated!');
                loadConnections();
            }
        } catch (error) {
            Alert.alert('Error', 'Failed to initiate connection');
        } finally {
            setLoading(false);
        }
    };

    const handleDisconnect = async (connectionId: string) => {
        try {
            await connectionsAPI.disconnectPlatform(connectionId);
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
                            onConnect={() => handleConnect(platform)}
                            onDisconnect={() => connection && handleDisconnect(connection.id)}
                        />
                    );
                })}
            </View>
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
