/**
 * ContactMessages Component
 * 
 * Shows conversation threads grouped by platform for a specific contact
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';
import { ConversationThread, UnifiedContact } from '../types';

interface ContactMessagesProps {
  contact: UnifiedContact;
  threads: ConversationThread[];
  loading?: boolean;
  onRefresh?: () => void;
  onThreadPress: (thread: ConversationThread) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

interface GroupedThreads {
  [platform: string]: ConversationThread[];
}

export const ContactMessages: React.FC<ContactMessagesProps> = ({
  contact,
  threads,
  loading = false,
  onRefresh,
  onThreadPress,
  onLoadMore,
  hasMore = false,
}) => {
  const { theme } = useTheme();

  // Group threads by platform
  const groupedThreads: GroupedThreads = threads.reduce((acc, thread) => {
    if (!acc[thread.platform]) {
      acc[thread.platform] = [];
    }
    acc[thread.platform].push(thread);
    return acc;
  }, {} as GroupedThreads);

  const platforms = Object.keys(groupedThreads).sort();

  const formatDate = (date: Date) => {
    const now = new Date();
    const messageDate = new Date(date);
    const diffInHours = (now.getTime() - messageDate.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return messageDate.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } else if (diffInHours < 168) { // 7 days
      return messageDate.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
      return messageDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
    }
  };

  const getPlatformIcon = (platform: string) => {
    const platformIcons: Record<string, string> = {
      gmail: 'mail',
      slack: 'chatbubbles',
      discord: 'game-controller',
      whatsapp: 'logo-whatsapp',
      twitter: 'logo-twitter',
      linkedin: 'logo-linkedin',
      telegram: 'paper-plane',
    };
    return platformIcons[platform.toLowerCase()] || 'globe';
  };

  const getPlatformColor = (platform: string) => {
    const platformColors: Record<string, string> = {
      gmail: '#EA4335',
      slack: '#4A154B',
      discord: '#5865F2',
      whatsapp: '#25D366',
      twitter: '#1DA1F2',
      linkedin: '#0077B5',
      telegram: '#0088CC',
    };
    return platformColors[platform.toLowerCase()] || theme.colors.primary;
  };

  const getMessagePreview = (thread: ConversationThread) => {
    if (thread.recentMessages && thread.recentMessages.length > 0) {
      const lastMessage = thread.recentMessages[0];
      return lastMessage.content.text || 'Media message';
    }
    return thread.summary?.shortSummary || 'No recent messages';
  };

  const renderThreadItem = ({ item: thread }: { item: ConversationThread }) => (
    <TouchableOpacity
      style={[styles.threadItem, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}
      onPress={() => onThreadPress(thread)}
    >
      <View style={styles.threadHeader}>
        <View style={styles.threadInfo}>
          <Text style={[styles.threadTitle, { color: theme.colors.text }]} numberOfLines={1}>
            {thread.title || `Conversation with ${contact.primaryName}`}
          </Text>
          <Text style={[styles.threadDate, { color: theme.colors.textSecondary }]}>
            {formatDate(thread.lastMessageAt)}
          </Text>
        </View>
        
        <View style={styles.threadMeta}>
          <Text style={[styles.messageCount, { color: theme.colors.textSecondary }]}>
            {thread.messageCount} messages
          </Text>
          {thread.isMuted && (
            <Icon name="volume-mute" size={16} color={theme.colors.textSecondary} />
          )}
          {thread.isArchived && (
            <Icon name="archive" size={16} color={theme.colors.textSecondary} />
          )}
        </View>
      </View>

      <Text style={[styles.threadPreview, { color: theme.colors.textSecondary }]} numberOfLines={2}>
        {getMessagePreview(thread)}
      </Text>

      {thread.keyTopics && thread.keyTopics.length > 0 && (
        <View style={styles.topicsContainer}>
          {thread.keyTopics.slice(0, 3).map((topic, index) => (
            <View
              key={index}
              style={[styles.topicTag, { backgroundColor: theme.colors.primary + '20' }]}
            >
              <Text style={[styles.topicText, { color: theme.colors.primary }]}>
                {topic}
              </Text>
            </View>
          ))}
          {thread.keyTopics.length > 3 && (
            <Text style={[styles.moreTopics, { color: theme.colors.textSecondary }]}>
              +{thread.keyTopics.length - 3} more
            </Text>
          )}
        </View>
      )}

      {thread.summary && thread.summary.actionItems.length > 0 && (
        <View style={styles.actionItemsContainer}>
          <Icon name="checkmark-circle-outline" size={16} color={theme.colors.warning} />
          <Text style={[styles.actionItemsText, { color: theme.colors.warning }]}>
            {thread.summary.actionItems.length} action item{thread.summary.actionItems.length > 1 ? 's' : ''}
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );

  const renderPlatformSection = (platform: string) => {
    const platformThreads = groupedThreads[platform];
    const platformColor = getPlatformColor(platform);

    return (
      <View key={platform} style={styles.platformSection}>
        <View style={[styles.platformHeader, { borderBottomColor: theme.colors.border }]}>
          <View style={styles.platformTitleContainer}>
            <Icon 
              name={getPlatformIcon(platform)} 
              size={24} 
              color={platformColor} 
            />
            <Text style={[styles.platformTitle, { color: theme.colors.text }]}>
              {platform.charAt(0).toUpperCase() + platform.slice(1)}
            </Text>
          </View>
          <Text style={[styles.platformCount, { color: theme.colors.textSecondary }]}>
            {platformThreads.length} conversation{platformThreads.length > 1 ? 's' : ''}
          </Text>
        </View>

        <FlatList
          data={platformThreads}
          renderItem={renderThreadItem}
          keyExtractor={(item) => item.id}
          scrollEnabled={false}
          ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
        />
      </View>
    );
  };

  const renderEmptyState = () => (
    <View style={styles.emptyContainer}>
      <Icon name="chatbubbles-outline" size={64} color={theme.colors.textSecondary} />
      <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
        No Messages Found
      </Text>
      <Text style={[styles.emptySubtitle, { color: theme.colors.textSecondary }]}>
        No conversation threads found with {contact.primaryName}
      </Text>
    </View>
  );

  const renderLoadMoreButton = () => {
    if (!hasMore) return null;

    return (
      <TouchableOpacity
        style={[styles.loadMoreButton, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}
        onPress={onLoadMore}
      >
        <Text style={[styles.loadMoreText, { color: theme.colors.primary }]}>
          Load More Conversations
        </Text>
      </TouchableOpacity>
    );
  };

  if (threads.length === 0 && !loading) {
    return renderEmptyState();
  }

  return (
    <FlatList
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      data={platforms}
      renderItem={({ item: platform }) => renderPlatformSection(platform)}
      keyExtractor={(platform) => platform}
      refreshControl={
        onRefresh ? (
          <RefreshControl
            refreshing={loading}
            onRefresh={onRefresh}
            tintColor={theme.colors.primary}
          />
        ) : undefined
      }
      ListFooterComponent={renderLoadMoreButton}
      ItemSeparatorComponent={() => <View style={{ height: 16 }} />}
      contentContainerStyle={styles.contentContainer}
    />
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
  },
  platformSection: {
    marginBottom: 16,
  },
  platformHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: 12,
    marginBottom: 12,
    borderBottomWidth: 1,
  },
  platformTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  platformTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  platformCount: {
    fontSize: 14,
  },
  threadItem: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  threadHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  threadInfo: {
    flex: 1,
    marginRight: 12,
  },
  threadTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  threadDate: {
    fontSize: 12,
  },
  threadMeta: {
    alignItems: 'flex-end',
    gap: 4,
  },
  messageCount: {
    fontSize: 12,
  },
  threadPreview: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  topicsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  topicTag: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  topicText: {
    fontSize: 12,
    fontWeight: '500',
  },
  moreTopics: {
    fontSize: 12,
  },
  actionItemsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 4,
  },
  actionItemsText: {
    fontSize: 12,
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
  },
  loadMoreButton: {
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
    alignItems: 'center',
    marginTop: 16,
  },
  loadMoreText: {
    fontSize: 16,
    fontWeight: '500',
  },
});