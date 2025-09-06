/**
 * EnhancedContactProfileScreen
 * 
 * Enhanced contact profile with relationship insights, timeline analysis, and network visualization
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';

// Components
import { ContactProfile } from '../components/ContactProfile';
import { CommunicationTimeline } from '../components/CommunicationTimeline';
import { RelationshipInsights } from '../components/RelationshipInsights';
import { NetworkVisualization } from '../components/NetworkVisualization';
import { ContactMessages } from '../components/ContactMessages';
import { SharedContent } from '../components/SharedContent';

// Services
import { contactService } from '../services/contactService';
import { insightsService } from '../services/insightsService';

// Types
import { 
  UnifiedContact, 
  RelationshipInsight, 
  TimelineData, 
  SentimentData, 
  NetworkData,
  ConversationThread,
  SharedFile,
  SharedLink
} from '../types';

type RootStackParamList = {
  EnhancedContactProfile: { contactId: string };
  MessageThread: { threadId: string; contactId: string };
  ContactSearch: undefined;
};

type EnhancedContactProfileScreenRouteProp = RouteProp<RootStackParamList, 'EnhancedContactProfile'>;
type EnhancedContactProfileScreenNavigationProp = StackNavigationProp<RootStackParamList, 'EnhancedContactProfile'>;

type TabType = 'overview' | 'timeline' | 'insights' | 'network' | 'messages' | 'content';

interface TabConfig {
  key: TabType;
  title: string;
  icon: string;
}

export const EnhancedContactProfileScreen: React.FC = () => {
  const { theme } = useTheme();
  const navigation = useNavigation<EnhancedContactProfileScreenNavigationProp>();
  const route = useRoute<EnhancedContactProfileScreenRouteProp>();
  
  const { contactId } = route.params;

  // State
  const [contact, setContact] = useState<UnifiedContact | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Data state
  const [insights, setInsights] = useState<RelationshipInsight[]>([]);
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null);
  const [networkData, setNetworkData] = useState<NetworkData | null>(null);
  const [threads, setThreads] = useState<ConversationThread[]>([]);
  const [sharedFiles, setSharedFiles] = useState<SharedFile[]>([]);
  const [sharedLinks, setSharedLinks] = useState<SharedLink[]>([]);

  // Loading states
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [networkLoading, setNetworkLoading] = useState(false);

  const tabs: TabConfig[] = [
    { key: 'overview', title: 'Overview', icon: 'person' },
    { key: 'timeline', title: 'Timeline', icon: 'analytics' },
    { key: 'insights', title: 'Insights', icon: 'bulb' },
    { key: 'network', title: 'Network', icon: 'people' },
    { key: 'messages', title: 'Messages', icon: 'chatbubbles' },
    { key: 'content', title: 'Content', icon: 'folder' },
  ];

  // Load initial data
  useEffect(() => {
    loadContactData();
  }, [contactId]);

  const loadContactData = async () => {
    try {
      setLoading(true);
      
      // Load basic contact info
      const contactData = await contactService.getContact(contactId);
      if (!contactData) {
        Alert.alert('Error', 'Contact not found');
        navigation.goBack();
        return;
      }
      
      setContact(contactData);
      
      // Load additional data based on active tab
      await loadTabData('overview');
      
    } catch (error) {
      console.error('Error loading contact data:', error);
      Alert.alert('Error', 'Failed to load contact data');
    } finally {
      setLoading(false);
    }
  };

  const loadTabData = async (tab: TabType) => {
    if (!contact) return;

    try {
      switch (tab) {
        case 'timeline':
          if (!timelineData) {
            setTimelineLoading(true);
            const timeline = await insightsService.getCommunicationTimeline(contactId);
            setTimelineData(timeline);
            setTimelineLoading(false);
          }
          break;

        case 'insights':
          if (insights.length === 0) {
            setInsightsLoading(true);
            const [insightsData, sentiment] = await Promise.all([
              insightsService.getRelationshipInsights(contactId),
              insightsService.getSentimentAnalysis(contactId)
            ]);
            setInsights(insightsData);
            setSentimentData(sentiment);
            setInsightsLoading(false);
          }
          break;

        case 'network':
          if (!networkData) {
            setNetworkLoading(true);
            const network = await insightsService.getNetworkAnalysis(contactId);
            setNetworkData(network);
            setNetworkLoading(false);
          }
          break;

        case 'messages':
          if (threads.length === 0) {
            const threadsData = await contactService.getConversationThreads(contactId);
            setThreads(threadsData);
          }
          break;

        case 'content':
          if (sharedFiles.length === 0 && sharedLinks.length === 0) {
            const [files, links] = await Promise.all([
              contactService.getSharedFiles(contactId),
              contactService.getSharedLinks(contactId)
            ]);
            setSharedFiles(files);
            setSharedLinks(links);
          }
          break;
      }
    } catch (error) {
      console.error(`Error loading ${tab} data:`, error);
    }
  };

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    loadTabData(tab);
  };

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    
    // Clear cached data for current tab
    switch (activeTab) {
      case 'timeline':
        setTimelineData(null);
        break;
      case 'insights':
        setInsights([]);
        setSentimentData(null);
        break;
      case 'network':
        setNetworkData(null);
        break;
      case 'messages':
        setThreads([]);
        break;
      case 'content':
        setSharedFiles([]);
        setSharedLinks([]);
        break;
    }
    
    // Reload data
    await loadTabData(activeTab);
    setRefreshing(false);
  }, [activeTab, contactId]);

  const handleInsightFeedback = async (insightId: string, feedback: 'helpful' | 'not_helpful' | 'incorrect') => {
    try {
      await insightsService.submitInsightFeedback(insightId, feedback);
      // Update local state to reflect feedback
      setInsights(prev => prev.map(insight => 
        insight.id === insightId 
          ? { ...insight, user_feedback: feedback }
          : insight
      ));
    } catch (error) {
      console.error('Error submitting feedback:', error);
      Alert.alert('Error', 'Failed to submit feedback');
    }
  };

  const handleActionPress = (action: string, insightId: string) => {
    // Handle suggested actions
    console.log('Action pressed:', action, insightId);
    // This could trigger various actions like setting reminders, opening specific platforms, etc.
  };

  const handleContactPress = (contactId: string) => {
    navigation.push('EnhancedContactProfile', { contactId });
  };

  const handleThreadPress = (thread: ConversationThread) => {
    navigation.navigate('MessageThread', { 
      threadId: thread.id, 
      contactId: contact?.id || '' 
    });
  };

  const renderTabBar = () => (
    <View style={[styles.tabBar, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabBarContent}>
        {tabs.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              {
                backgroundColor: activeTab === tab.key ? theme.colors.primary : 'transparent',
                borderColor: theme.colors.border,
              },
            ]}
            onPress={() => handleTabChange(tab.key)}
          >
            <Icon
              name={tab.icon}
              size={16}
              color={activeTab === tab.key ? theme.colors.white : theme.colors.textSecondary}
            />
            <Text
              style={[
                styles.tabText,
                {
                  color: activeTab === tab.key ? theme.colors.white : theme.colors.textSecondary,
                },
              ]}
            >
              {tab.title}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderTabContent = () => {
    if (!contact) return null;

    switch (activeTab) {
      case 'overview':
        return (
          <ContactProfile
            contact={contact}
            onViewMessagesPress={() => handleTabChange('messages')}
            onViewSharedContentPress={() => handleTabChange('content')}
          />
        );

      case 'timeline':
        return (
          <CommunicationTimeline
            contact={contact}
            timelineData={timelineData}
            loading={timelineLoading}
            onRefresh={handleRefresh}
          />
        );

      case 'insights':
        return (
          <RelationshipInsights
            contact={contact}
            insights={insights}
            sentimentData={sentimentData}
            loading={insightsLoading}
            onRefreshInsights={handleRefresh}
            onInsightFeedback={handleInsightFeedback}
            onActionPress={handleActionPress}
          />
        );

      case 'network':
        return (
          <NetworkVisualization
            contact={contact}
            networkData={networkData || { network_graph: { nodes: [], edges: [] }, network_stats: null, mutual_contacts_list: [] }}
            onContactPress={handleContactPress}
            onRefresh={handleRefresh}
          />
        );

      case 'messages':
        return (
          <ContactMessages
            contact={contact}
            threads={threads}
            loading={false}
            onRefresh={handleRefresh}
            onThreadPress={handleThreadPress}
          />
        );

      case 'content':
        return (
          <SharedContent
            contact={contact}
            files={sharedFiles}
            links={sharedLinks}
            onRefresh={handleRefresh}
          />
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: theme.colors.background }]}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
        <Text style={[styles.loadingText, { color: theme.colors.textSecondary }]}>
          Loading contact profile...
        </Text>
      </View>
    );
  }

  if (!contact) {
    return (
      <View style={[styles.errorContainer, { backgroundColor: theme.colors.background }]}>
        <Icon name="person-remove" size={64} color={theme.colors.textSecondary} />
        <Text style={[styles.errorTitle, { color: theme.colors.text }]}>
          Contact Not Found
        </Text>
        <Text style={[styles.errorSubtitle, { color: theme.colors.textSecondary }]}>
          The contact you're looking for could not be found.
        </Text>
        <TouchableOpacity
          style={[styles.backButton, { backgroundColor: theme.colors.primary }]}
          onPress={() => navigation.goBack()}
        >
          <Text style={[styles.backButtonText, { color: theme.colors.white }]}>
            Go Back
          </Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Icon name="arrow-back" size={24} color={theme.colors.text} />
        </TouchableOpacity>
        
        <View style={styles.headerTitle}>
          <Text style={[styles.headerTitleText, { color: theme.colors.text }]}>
            {contact.primaryName}
          </Text>
          <Text style={[styles.headerSubtitle, { color: theme.colors.textSecondary }]}>
            Contact Profile
          </Text>
        </View>
        
        <TouchableOpacity
          style={styles.moreButton}
          onPress={() => {
            // Show more options menu
          }}
        >
          <Icon name="ellipsis-vertical" size={24} color={theme.colors.text} />
        </TouchableOpacity>
      </View>

      {renderTabBar()}

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.colors.primary}
          />
        }
      >
        {renderTabContent()}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
  },
  errorSubtitle: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    flex: 1,
    marginLeft: 8,
  },
  headerTitleText: {
    fontSize: 18,
    fontWeight: '600',
  },
  headerSubtitle: {
    fontSize: 14,
  },
  moreButton: {
    padding: 8,
  },
  tabBar: {
    borderBottomWidth: 1,
  },
  tabBarContent: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    borderWidth: 1,
    marginRight: 8,
    gap: 6,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
  },
  content: {
    flex: 1,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: '500',
  },
});