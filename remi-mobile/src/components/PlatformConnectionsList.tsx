/**
 * Platform Connections List Component
 * 
 * Displays a list of all platform connections with filtering, sorting,
 * and bulk operations.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  RefreshControl,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { PlatformConnection, platformConnectionService } from '../services/platformConnectionService';
import { PlatformConnectionCard } from './PlatformConnectionCard';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorMessage } from './ErrorMessage';

interface PlatformConnectionsListProps {
  onNavigateToSettings: (platform: string) => void;
  onNavigateToTroubleshooting: (platform: string) => void;
  onNavigateToOAuth: (platform: string) => void;
}

type FilterType = 'all' | 'connected' | 'disconnected' | 'issues';
type SortType = 'name' | 'status' | 'lastSync';

export const PlatformConnectionsList: React.FC<PlatformConnectionsListProps> = ({
  onNavigateToSettings,
  onNavigateToTroubleshooting,
  onNavigateToOAuth,
}) => {
  const { theme } = useTheme();
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [sortBy, setSortBy] = useState<SortType>('name');
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      setError(null);
      const allConnections = await platformConnectionService.getAllConnections();
      setConnections(allConnections);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load connections');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadConnections();
    setRefreshing(false);
  };

  const handleConnect = async (platform: string) => {
    try {
      onNavigateToOAuth(platform);
    } catch (err) {
      Alert.alert('Connection Error', err instanceof Error ? err.message : 'Failed to connect platform');
    }
  };

  const handleDisconnect = async (platform: string) => {
    try {
      await platformConnectionService.disconnectPlatform(platform);
      await loadConnections();
    } catch (err) {
      Alert.alert('Disconnect Error', err instanceof Error ? err.message : 'Failed to disconnect platform');
    }
  };

  const handleSync = async (platform: string) => {
    try {
      await platformConnectionService.syncPlatform(platform);
      await loadConnections();
      Alert.alert('Sync Complete', `${platform} has been synchronized successfully.`);
    } catch (err) {
      Alert.alert('Sync Error', err instanceof Error ? err.message : 'Failed to sync platform');
    }
  };

  const handleBulkEnable = async () => {
    if (selectedPlatforms.size === 0) return;

    try {
      const platforms = Array.from(selectedPlatforms);
      const result = await platformConnectionService.bulkEnablePlatforms(platforms);
      
      if (result.failed.length > 0) {
        Alert.alert(
          'Partial Success',
          `Enabled ${result.successful.length} platforms. ${result.failed.length} failed.`
        );
      } else {
        Alert.alert('Success', `Enabled ${result.successful.length} platforms.`);
      }
      
      setSelectedPlatforms(new Set());
      setBulkMode(false);
      await loadConnections();
    } catch (err) {
      Alert.alert('Bulk Operation Error', err instanceof Error ? err.message : 'Failed to enable platforms');
    }
  };

  const handleBulkDisable = async () => {
    if (selectedPlatforms.size === 0) return;

    Alert.alert(
      'Disable Platforms',
      `Are you sure you want to disable ${selectedPlatforms.size} platforms?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disable',
          style: 'destructive',
          onPress: async () => {
            try {
              const platforms = Array.from(selectedPlatforms);
              const result = await platformConnectionService.bulkDisablePlatforms(platforms);
              
              if (result.failed.length > 0) {
                Alert.alert(
                  'Partial Success',
                  `Disabled ${result.successful.length} platforms. ${result.failed.length} failed.`
                );
              } else {
                Alert.alert('Success', `Disabled ${result.successful.length} platforms.`);
              }
              
              setSelectedPlatforms(new Set());
              setBulkMode(false);
              await loadConnections();
            } catch (err) {
              Alert.alert('Bulk Operation Error', err instanceof Error ? err.message : 'Failed to disable platforms');
            }
          }
        }
      ]
    );
  };

  const handleSyncAll = async () => {
    try {
      const result = await platformConnectionService.syncAllPlatforms();
      
      if (result.failed.length > 0) {
        Alert.alert(
          'Partial Success',
          `Synced ${result.successful.length} platforms. ${result.failed.length} failed.`
        );
      } else {
        Alert.alert('Success', `Synced ${result.successful.length} platforms.`);
      }
      
      await loadConnections();
    } catch (err) {
      Alert.alert('Sync Error', err instanceof Error ? err.message : 'Failed to sync platforms');
    }
  };

  const togglePlatformSelection = (platform: string) => {
    const newSelection = new Set(selectedPlatforms);
    if (newSelection.has(platform)) {
      newSelection.delete(platform);
    } else {
      newSelection.add(platform);
    }
    setSelectedPlatforms(newSelection);
  };

  const getFilteredAndSortedConnections = () => {
    let filtered = connections;

    // Apply filter
    switch (filter) {
      case 'connected':
        filtered = connections.filter(conn => conn.isConnected);
        break;
      case 'disconnected':
        filtered = connections.filter(conn => !conn.isConnected);
        break;
      case 'issues':
        filtered = connections.filter(conn => 
          conn.connectionStatus === 'unhealthy' || conn.connectionStatus === 'degraded'
        );
        break;
    }

    // Apply sort
    switch (sortBy) {
      case 'name':
        filtered.sort((a, b) => a.displayName.localeCompare(b.displayName));
        break;
      case 'status':
        const statusOrder = { healthy: 0, degraded: 1, unhealthy: 2, authenticating: 3, disconnected: 4 };
        filtered.sort((a, b) => statusOrder[a.connectionStatus] - statusOrder[b.connectionStatus]);
        break;
      case 'lastSync':
        filtered.sort((a, b) => {
          if (!a.lastSyncTime && !b.lastSyncTime) return 0;
          if (!a.lastSyncTime) return 1;
          if (!b.lastSyncTime) return -1;
          return b.lastSyncTime.getTime() - a.lastSyncTime.getTime();
        });
        break;
    }

    return filtered;
  };

  const renderFilterButton = (filterType: FilterType, label: string) => (
    <TouchableOpacity
      style={[
        styles.filterButton,
        filter === filterType && styles.activeFilterButton
      ]}
      onPress={() => setFilter(filterType)}
    >
      <Text style={[
        styles.filterButtonText,
        filter === filterType && styles.activeFilterButtonText
      ]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  const renderSortButton = (sortType: SortType, label: string) => (
    <TouchableOpacity
      style={[
        styles.sortButton,
        sortBy === sortType && styles.activeSortButton
      ]}
      onPress={() => setSortBy(sortType)}
    >
      <Text style={[
        styles.sortButtonText,
        sortBy === sortType && styles.activeSortButtonText
      ]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  const renderConnectionCard = ({ item }: { item: PlatformConnection }) => (
    <TouchableOpacity
      style={[
        styles.cardContainer,
        bulkMode && selectedPlatforms.has(item.platform) && styles.selectedCard
      ]}
      onLongPress={() => {
        if (!bulkMode) {
          setBulkMode(true);
          setSelectedPlatforms(new Set([item.platform]));
        }
      }}
      onPress={() => {
        if (bulkMode) {
          togglePlatformSelection(item.platform);
        }
      }}
    >
      <PlatformConnectionCard
        connection={item}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        onSettings={onNavigateToSettings}
        onSync={handleSync}
        onTroubleshoot={onNavigateToTroubleshooting}
      />
    </TouchableOpacity>
  );

  const filteredConnections = getFilteredAndSortedConnections();

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    header: {
      padding: 16,
      backgroundColor: theme.colors.surface,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.border,
    },
    title: {
      fontSize: 24,
      fontWeight: 'bold',
      color: theme.colors.text,
      marginBottom: 16,
    },
    controls: {
      marginBottom: 16,
    },
    filtersContainer: {
      flexDirection: 'row',
      marginBottom: 12,
    },
    filterButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 20,
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
      marginRight: 8,
    },
    activeFilterButton: {
      backgroundColor: theme.colors.primary,
      borderColor: theme.colors.primary,
    },
    filterButtonText: {
      fontSize: 14,
      color: theme.colors.text,
    },
    activeFilterButtonText: {
      color: theme.colors.surface,
    },
    sortContainer: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    sortLabel: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      marginRight: 12,
    },
    sortButton: {
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: 16,
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
      marginRight: 8,
    },
    activeSortButton: {
      backgroundColor: theme.colors.secondary,
      borderColor: theme.colors.secondary,
    },
    sortButtonText: {
      fontSize: 12,
      color: theme.colors.text,
    },
    activeSortButtonText: {
      color: theme.colors.surface,
    },
    bulkActions: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: 16,
      backgroundColor: theme.colors.primary,
    },
    bulkActionText: {
      color: theme.colors.surface,
      fontSize: 16,
      fontWeight: '500',
    },
    bulkActionButtons: {
      flexDirection: 'row',
    },
    bulkActionButton: {
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: 16,
      backgroundColor: theme.colors.surface,
      marginLeft: 8,
    },
    bulkActionButtonText: {
      color: theme.colors.primary,
      fontSize: 14,
      fontWeight: '500',
    },
    list: {
      flex: 1,
    },
    cardContainer: {
      marginVertical: 4,
    },
    selectedCard: {
      backgroundColor: theme.colors.primaryLight,
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    emptyText: {
      fontSize: 16,
      color: theme.colors.textSecondary,
      textAlign: 'center',
      marginBottom: 16,
    },
    emptySubtext: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      textAlign: 'center',
    },
    quickActions: {
      flexDirection: 'row',
      justifyContent: 'space-around',
      padding: 16,
      backgroundColor: theme.colors.surface,
      borderTopWidth: 1,
      borderTopColor: theme.colors.border,
    },
    quickActionButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 20,
      backgroundColor: theme.colors.primary,
    },
    quickActionButtonText: {
      color: theme.colors.surface,
      fontSize: 14,
      fontWeight: '500',
    },
  });

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <LoadingSpinner />
        <Text style={{ color: theme.colors.textSecondary, marginTop: 16 }}>
          Loading platform connections...
        </Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <ErrorMessage 
          message={error} 
          onRetry={loadConnections}
        />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Platform Connections</Text>
        
        <View style={styles.controls}>
          <View style={styles.filtersContainer}>
            {renderFilterButton('all', 'All')}
            {renderFilterButton('connected', 'Connected')}
            {renderFilterButton('disconnected', 'Disconnected')}
            {renderFilterButton('issues', 'Issues')}
          </View>
          
          <View style={styles.sortContainer}>
            <Text style={styles.sortLabel}>Sort by:</Text>
            {renderSortButton('name', 'Name')}
            {renderSortButton('status', 'Status')}
            {renderSortButton('lastSync', 'Last Sync')}
          </View>
        </View>
      </View>

      {bulkMode && (
        <View style={styles.bulkActions}>
          <Text style={styles.bulkActionText}>
            {selectedPlatforms.size} selected
          </Text>
          <View style={styles.bulkActionButtons}>
            <TouchableOpacity
              style={styles.bulkActionButton}
              onPress={() => {
                setBulkMode(false);
                setSelectedPlatforms(new Set());
              }}
            >
              <Text style={styles.bulkActionButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.bulkActionButton}
              onPress={handleBulkEnable}
            >
              <Text style={styles.bulkActionButtonText}>Enable</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.bulkActionButton}
              onPress={handleBulkDisable}
            >
              <Text style={styles.bulkActionButtonText}>Disable</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {filteredConnections.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>
            {filter === 'all' 
              ? 'No platform connections found'
              : `No ${filter} platforms found`
            }
          </Text>
          <Text style={styles.emptySubtext}>
            Connect your communication platforms to start syncing your data.
          </Text>
        </View>
      ) : (
        <FlatList
          style={styles.list}
          data={filteredConnections}
          renderItem={renderConnectionCard}
          keyExtractor={(item) => item.platform}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={theme.colors.primary}
            />
          }
        />
      )}

      {!bulkMode && connections.some(conn => conn.isConnected) && (
        <View style={styles.quickActions}>
          <TouchableOpacity
            style={styles.quickActionButton}
            onPress={handleSyncAll}
          >
            <Text style={styles.quickActionButtonText}>Sync All</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};