/**
 * MessageThread Component
 * 
 * Basic message display with search highlighting
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Image,
  TouchableOpacity,
  TextInput,
  RefreshControl,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';
import { Message, ConversationThread, TextHighlight, Attachment } from '../types';

interface MessageThreadProps {
  thread: ConversationThread;
  messages: Message[];
  searchQuery?: string;
  highlights?: TextHighlight[];
  loading?: boolean;
  onRefresh?: () => void;
  onLoadMore?: () => void;
  onMessagePress?: (message: Message) => void;
  onAttachmentPress?: (attachment: Attachment) => void;
  onSearch?: (query: string) => void;
  hasMore?: boolean;
}

export const MessageThread: React.FC<MessageThreadProps> = ({
  thread,
  messages,
  searchQuery = '',
  highlights = [],
  loading = false,
  onRefresh,
  onLoadMore,
  onMessagePress,
  onAttachmentPress,
  onSearch,
  hasMore = false,
}) => {
  const { theme } = useTheme();
  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery);
  const [showSearch, setShowSearch] = useState(false);

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
      return messageDate.toLocaleDateString('en-US', { 
        weekday: 'short',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } else {
      return messageDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    }
  };

  const highlightText = (text: string, highlights: TextHighlight[]) => {
    if (!highlights.length || !searchQuery) return text;

    // Sort highlights by start position
    const sortedHighlights = [...highlights].sort((a, b) => a.start - b.start);
    
    const parts = [];
    let lastIndex = 0;

    sortedHighlights.forEach((highlight, index) => {
      // Add text before highlight
      if (highlight.start > lastIndex) {
        parts.push({
          text: text.substring(lastIndex, highlight.start),
          highlighted: false,
        });
      }

      // Add highlighted text
      parts.push({
        text: text.substring(highlight.start, highlight.end),
        highlighted: true,
      });

      lastIndex = highlight.end;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({
        text: text.substring(lastIndex),
        highlighted: false,
      });
    }

    return parts;
  };

  const renderHighlightedText = (text: string, highlights: TextHighlight[]) => {
    const parts = highlightText(text, highlights);
    
    if (typeof parts === 'string') {
      return <Text style={[styles.messageText, { color: theme.colors.text }]}>{parts}</Text>;
    }

    return (
      <Text style={[styles.messageText, { color: theme.colors.text }]}>
        {parts.map((part, index) => (
          <Text
            key={index}
            style={part.highlighted ? [styles.highlightedText, { backgroundColor: theme.colors.warning + '40' }] : undefined}
          >
            {part.text}
          </Text>
        ))}
      </Text>
    );
  };

  const renderAttachment = (attachment: Attachment) => {
    const isImage = attachment.type.startsWith('image/');
    const isVideo = attachment.type.startsWith('video/');
    const isAudio = attachment.type.startsWith('audio/');

    return (
      <TouchableOpacity
        key={attachment.id}
        style={[styles.attachment, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}
        onPress={() => onAttachmentPress?.(attachment)}
      >
        {isImage && attachment.thumbnailUrl ? (
          <Image source={{ uri: attachment.thumbnailUrl }} style={styles.attachmentThumbnail} />
        ) : (
          <View style={[styles.attachmentIcon, { backgroundColor: theme.colors.primary + '20' }]}>
            <Icon
              name={isImage ? 'image' : isVideo ? 'videocam' : isAudio ? 'musical-notes' : 'document'}
              size={24}
              color={theme.colors.primary}
            />
          </View>
        )}
        
        <View style={styles.attachmentInfo}>
          <Text style={[styles.attachmentName, { color: theme.colors.text }]} numberOfLines={1}>
            {attachment.name}
          </Text>
          <Text style={[styles.attachmentSize, { color: theme.colors.textSecondary }]}>
            {formatFileSize(attachment.size)}
          </Text>
        </View>

        <Icon name="download" size={16} color={theme.colors.primary} />
      </TouchableOpacity>
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const renderMessage = ({ item: message, index }: { item: Message; index: number }) => {
    const isCurrentUser = message.sender.id === 'current-user'; // This should come from auth context
    const showAvatar = index === 0 || messages[index - 1].sender.id !== message.sender.id;
    const messageHighlights = highlights.filter(h => h.text === message.content.text);

    return (
      <TouchableOpacity
        style={[
          styles.messageContainer,
          isCurrentUser ? styles.currentUserMessage : styles.otherUserMessage,
        ]}
        onPress={() => onMessagePress?.(message)}
        disabled={!onMessagePress}
      >
        <View style={styles.messageContent}>
          {!isCurrentUser && showAvatar && (
            <View style={styles.avatarContainer}>
              {message.sender.profilePhoto ? (
                <Image source={{ uri: message.sender.profilePhoto }} style={styles.avatar} />
              ) : (
                <View style={[styles.avatarPlaceholder, { backgroundColor: theme.colors.primary }]}>
                  <Text style={[styles.avatarText, { color: theme.colors.white }]}>
                    {message.sender.primaryName[0].toUpperCase()}
                  </Text>
                </View>
              )}
            </View>
          )}

          <View style={[
            styles.messageBubble,
            {
              backgroundColor: isCurrentUser ? theme.colors.primary : theme.colors.surface,
              marginLeft: !isCurrentUser && !showAvatar ? 48 : 0,
            },
          ]}>
            {!isCurrentUser && showAvatar && (
              <Text style={[styles.senderName, { color: theme.colors.textSecondary }]}>
                {message.sender.primaryName}
              </Text>
            )}

            {message.content.text && renderHighlightedText(message.content.text, messageHighlights)}

            {message.attachments.length > 0 && (
              <View style={styles.attachmentsContainer}>
                {message.attachments.map(renderAttachment)}
              </View>
            )}

            <View style={styles.messageFooter}>
              <Text style={[
                styles.messageTime,
                { color: isCurrentUser ? theme.colors.white + '80' : theme.colors.textSecondary }
              ]}>
                {formatDate(message.timestamp)}
              </Text>

              {message.isImportant && (
                <Icon
                  name="star"
                  size={12}
                  color={isCurrentUser ? theme.colors.white : theme.colors.warning}
                />
              )}

              {message.editedAt && (
                <Text style={[
                  styles.editedIndicator,
                  { color: isCurrentUser ? theme.colors.white + '60' : theme.colors.textSecondary }
                ]}>
                  edited
                </Text>
              )}
            </View>

            {/* Show entities if available */}
            {message.entities.length > 0 && (
              <View style={styles.entitiesContainer}>
                {message.entities.slice(0, 3).map((entity, index) => (
                  <View
                    key={index}
                    style={[styles.entityTag, { backgroundColor: theme.colors.warning + '20' }]}
                  >
                    <Text style={[styles.entityText, { color: theme.colors.warning }]}>
                      {entity.type}: {entity.text}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  const renderSearchBar = () => {
    if (!showSearch) return null;

    return (
      <View style={[styles.searchContainer, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}>
        <Icon name="search" size={20} color={theme.colors.textSecondary} />
        <TextInput
          style={[styles.searchInput, { color: theme.colors.text }]}
          placeholder="Search in conversation..."
          placeholderTextColor={theme.colors.textSecondary}
          value={localSearchQuery}
          onChangeText={setLocalSearchQuery}
          onSubmitEditing={() => onSearch?.(localSearchQuery)}
          autoFocus
        />
        {localSearchQuery.length > 0 && (
          <TouchableOpacity onPress={() => {
            setLocalSearchQuery('');
            onSearch?.('');
          }}>
            <Icon name="close-circle" size={20} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>
    );
  };

  const renderHeader = () => (
    <View style={[styles.header, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}>
      <View style={styles.headerContent}>
        <Text style={[styles.threadTitle, { color: theme.colors.text }]} numberOfLines={1}>
          {thread.title || `Conversation with ${thread.participants.map(p => p.primaryName).join(', ')}`}
        </Text>
        <Text style={[styles.threadSubtitle, { color: theme.colors.textSecondary }]}>
          {thread.messageCount} messages • {thread.platform}
        </Text>
      </View>

      <TouchableOpacity
        style={styles.searchButton}
        onPress={() => setShowSearch(!showSearch)}
      >
        <Icon name="search" size={24} color={theme.colors.primary} />
      </TouchableOpacity>
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
          Load Earlier Messages
        </Text>
      </TouchableOpacity>
    );
  };

  const renderEmptyState = () => (
    <View style={styles.emptyContainer}>
      <Icon name="chatbubbles-outline" size={64} color={theme.colors.textSecondary} />
      <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
        No Messages
      </Text>
      <Text style={[styles.emptySubtitle, { color: theme.colors.textSecondary }]}>
        This conversation doesn't have any messages yet
      </Text>
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      {renderHeader()}
      {renderSearchBar()}
      
      {messages.length === 0 ? (
        renderEmptyState()
      ) : (
        <FlatList
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.messagesContainer}
          inverted
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
          ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  headerContent: {
    flex: 1,
  },
  threadTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 2,
  },
  threadSubtitle: {
    fontSize: 14,
  },
  searchButton: {
    padding: 8,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 24,
    borderWidth: 1,
    gap: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
  },
  messagesContainer: {
    padding: 16,
  },
  messageContainer: {
    marginVertical: 2,
  },
  currentUserMessage: {
    alignItems: 'flex-end',
  },
  otherUserMessage: {
    alignItems: 'flex-start',
  },
  messageContent: {
    flexDirection: 'row',
    maxWidth: '80%',
    alignItems: 'flex-end',
  },
  avatarContainer: {
    marginRight: 8,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  avatarPlaceholder: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  messageBubble: {
    borderRadius: 16,
    padding: 12,
    minWidth: 60,
  },
  senderName: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  highlightedText: {
    fontWeight: '600',
    borderRadius: 2,
    paddingHorizontal: 2,
  },
  attachmentsContainer: {
    marginTop: 8,
    gap: 8,
  },
  attachment: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
  },
  attachmentThumbnail: {
    width: 40,
    height: 40,
    borderRadius: 4,
  },
  attachmentIcon: {
    width: 40,
    height: 40,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  attachmentInfo: {
    flex: 1,
  },
  attachmentName: {
    fontSize: 14,
    fontWeight: '500',
  },
  attachmentSize: {
    fontSize: 12,
  },
  messageFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    gap: 6,
  },
  messageTime: {
    fontSize: 12,
  },
  editedIndicator: {
    fontSize: 10,
    fontStyle: 'italic',
  },
  entitiesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
    gap: 4,
  },
  entityTag: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  entityText: {
    fontSize: 10,
    fontWeight: '500',
  },
  loadMoreButton: {
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
    alignItems: 'center',
    margin: 16,
  },
  loadMoreText: {
    fontSize: 16,
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
});