import React from 'react'
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { useTheme } from '@/hooks/useTheme'
import { useAuth } from '@/hooks/useAuth'
import Icon from 'react-native-vector-icons/Ionicons'

export function DashboardScreen() {
  const navigation = useNavigation()
  const { colors } = useTheme()
  const { user } = useAuth()

  const quickActions = [
    { 
      id: 'demo', 
      title: 'Try Demo Workflow', 
      icon: 'play-circle', 
      color: colors.primary,
      onPress: () => navigation.navigate('DemoWorkflow' as never),
    },
    { 
      id: 'search', 
      title: 'Search Contacts', 
      icon: 'search', 
      color: '#10b981',
      onPress: () => navigation.navigate('Search' as never),
    },
    { 
      id: 'insights', 
      title: 'View Insights', 
      icon: 'bulb', 
      color: '#f59e0b',
      onPress: () => console.log('View insights'),
    },
    { 
      id: 'settings', 
      title: 'Settings', 
      icon: 'settings', 
      color: '#6b7280',
      onPress: () => navigation.navigate('Settings' as never),
    },
  ]

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.greeting, { color: colors.text }]}>
          Welcome back, {user?.name || 'User'}!
        </Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          Your unified communication hub
        </Text>
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          {quickActions.map((action) => (
            <TouchableOpacity
              key={action.id}
              style={[styles.actionCard, { backgroundColor: colors.surface }]}
              onPress={action.onPress}
            >
              <View style={[styles.actionIcon, { backgroundColor: `${action.color}20` }]}>
                <Icon name={action.icon} size={24} color={action.color} />
              </View>
              <Text style={[styles.actionTitle, { color: colors.text }]}>
                {action.title}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Recent Activity */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>Recent Activity</Text>
        <View style={[styles.activityCard, { backgroundColor: colors.surface }]}>
          <Text style={[styles.activityText, { color: colors.textSecondary }]}>
            No recent activity to show
          </Text>
        </View>
      </View>

      {/* Stats */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>Overview</Text>
        <View style={styles.statsGrid}>
          <View style={[styles.statCard, { backgroundColor: colors.surface }]}>
            <Text style={[styles.statNumber, { color: colors.primary }]}>0</Text>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Contacts</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: colors.surface }]}>
            <Text style={[styles.statNumber, { color: colors.primary }]}>0</Text>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Messages</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: colors.surface }]}>
            <Text style={[styles.statNumber, { color: colors.primary }]}>0</Text>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Platforms</Text>
          </View>
        </View>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    padding: 20,
    paddingTop: 10,
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
  },
  section: {
    padding: 20,
    paddingTop: 0,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  actionCard: {
    width: '48%',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  actionIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  activityCard: {
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  activityText: {
    fontSize: 16,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  statCard: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 14,
  },
})