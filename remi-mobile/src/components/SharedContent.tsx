/**
 * SharedContent Component
 * 
 * Displays files, links, and media shared with contacts
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  Linking,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';
import { SharedFile, SharedLink, UnifiedContact } from '../types';

interface SharedContentProps {
  contact: UnifiedContact;
  files: SharedFile[];
  links: SharedLink[];
  onFilePress?: (file: SharedFile) => void;
  onLinkPress?: (link: SharedLink) => void;
  onRefresh?: () => void;
  loading?: boolean;
}

type ContentType = 'all' | 'files' | 'links';
type SortBy = 'date' | 'name' | 'platform';

interface ContentItem {
  id: string;
  type: 'file' | 'link';
  title: string;
  subtitle: string;
  date: Date;
  platform: string;
  data: SharedFile | SharedLink;
}

export const SharedContent: React.FC<SharedContentProps> = ({
  contact,
  files,
  links,
  onFilePress,
  onLinkPress,
  onRefresh,
  loading = false,
}) => {
  const { theme } = useTheme();
  const [contentType, setContentType] = useState<ContentType>('all');
  const [sortBy, setSortBy] = useState<SortBy>('date');

  // Combine and transform files and links into a unified format
  const allContent: ContentItem[] = [
    ...files.map(file => ({
      id: file.id,
      type: 'file' as const,
      title: file.name,
      subtitle: `${formatFileSize(file.size)} • ${file.type}`,
      date: file.sharedAt,
      platform: file.platform,
      data: file,
    })),
    ...links.map(link => ({
      id: link.id,
      type: 'link' as const,
      title: link.title,
      subtitle: link.description || new URL(link.url).hostname,
      date: link.sharedAt,
      platform: link.platform,
      data: link,
    })),
  ];

  // Filter content based on type
  const filteredContent = allContent.filter(item => {
    if (contentType === 'all') return true;
    if (contentType === 'files') return item.type === 'file';
    if (contentType === 'links') return item.type === 'link';
    return true;
  });

  // Sort content
  const sortedContent = [...filteredContent].sort((a, b) => {
    switch (sortBy) {
      case 'date':
        return new Date(b.date).getTime() - new Date(a.date).getTime();
      case 'name':
        return a.title.localeCompare(b.title);
      case 'platform':
        return a.platform.localeCompare(b.platform);
      default:
        return 0;
    }
  });

  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  const formatDate = (date: Date) => {
    const now = new Date();
    const itemDate = new Date(date);
    const diffInDays = Math.floor((now.getTime() - itemDate.getTime()) / (1000 * 60 * 60 * 24));

    if (diffInDays === 0) return 'Today';
    if (diffInDays === 1) return 'Yesterday';
    if (diffInDays < 7) return `${diffInDays} days ago`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
    if (diffInDays < 365) return `${Math.floor(diffInDays / 30)} months ago`;
    return `${Math.floor(diffInDays / 365)} years ago`;
  };

  const getFileIcon = (fileType: string) => {
    const type = fileType.toLowerCase();
    if (type.includes('image')) return 'image';
    if (type.includes('video')) return 'videocam';
    if (type.includes('audio')) return 'musical-notes';
    if (type.includes('pdf')) return 'document-text';
    if (type.includes('word') || type.includes('doc')) return 'document-text';
    if (type.includes('excel') || type.includes('sheet')) return 'grid';
    if (type.includes('powerpoint') || type.includes('presentation')) return 'easel';
    if (type.includes('zip') || type.includes('rar')) return 'archive';
    return 'document';
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

  const handleItemPress = (item: ContentItem) => {
    if (item.type === 'file') {
      if (onFilePress) {
        onFilePress(item.data as SharedFile);
      } else {
        // Default behavior: try to open the file URL
        const file = item.data as SharedFile;
        Linking.openURL(file.url).catch(() => {
          Alert.alert('Error', 'Unable to open file');
        });
      }
    } else {
      if (onLinkPress) {
        onLinkPress(item.data as SharedLink);
      } else {
        // Default behavior: open the link
        const link = item.data as SharedLink;
        Linking.openURL(link.url).catch(() => {
          Alert.alert('Error', 'Unable to open link');
        });
      }
    }
  };

  const renderFilterTabs = () => (
    <View style={styles.filterContainer}>
      <View style={styles.filterTabs}>
        {(['all', 'files', 'links'] as ContentType[]).map((type) => (
          <TouchableOpacity
            key={type}
            style={[
              styles.filterTab,
              {
                backgroundColor: contentType === type ? theme.colors.primary : 'transparent',
                borderColor: theme.colors.border,
              },
            ]}
            onPress={() => setContentType(type)}
          >
            <Text
              style={[
                styles.filterTabText,
                {
                  color: contentType === type ? theme.colors.white : theme.colors.text,
                },
              ]}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity
        style={[styles.sortButton, { borderColor: theme.colors.border }]}
        onPress={() => {
          // Cycle through sort options
          const sortOptions: SortBy[] = ['date', 'name', 'platform'];
          const currentIndex = sortOptions.indexOf(sortBy);
          const nextIndex = (currentIndex + 1) % sortOptions.length;
          setSortBy(sortOptions[nextIndex]);
        }}
      >
        <Icon name="funnel" size={16} color={theme.colors.primary} />
        <Text style={[styles.sortButtonText, { color: theme.colors.primary }]}>
          {sortBy.charAt(0).toUpperCase() + sortBy.slice(1)}
        </Text>
      </TouchableOpacity>
    </View>
  );

  const renderContentItem = ({ item }: { item: ContentItem }) => (
    <TouchableOpacity
      style={[styles.contentItem, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}
      onPress={() => handleItemPress(item)}
    >
      <View style={styles.contentIcon}>
        {item.type === 'file' ? (
          <Icon
            name={getFileIcon((item.data as SharedFile).type)}
            size={24}
            color={theme.colors.primary}
          />
        ) : (
          <Icon name="link" size={24} color={theme.colors.primary} />
        )}
      </View>

      <View style={styles.contentInfo}>
        <Text style={[styles.contentTitle, { color: theme.colors.text }]} numberOfLines={2}>
          {item.title}
        </Text>
        <Text style={[styles.contentSubtitle, { color: theme.colors.textSecondary }]} numberOfLines={1}>
          {item.subtitle}
        </Text>
        <View style={styles.contentMeta}>
          <Icon
            name={getPlatformIcon(item.platform)}
            size={12}
            color={theme.colors.textSecondary}
          />
          <Text style={[styles.contentMetaText, { color: theme.colors.textSecondary }]}>
            {item.platform} • {formatDate(item.date)}
          </Text>
        </View>
      </View>

      <Icon name="chevron-forward" size={16} color={theme.colors.textSecondary} />
    </TouchableOpacity>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyContainer}>
      <Icon
        name={contentType === 'files' ? 'folder-outline' : contentType === 'links' ? 'link-outline' : 'albums-outline'}
        size={64}
        color={theme.colors.textSecondary}
      />
      <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
        No {contentType === 'all' ? 'Content' : contentType.charAt(0).toUpperCase() + contentType.slice(1)} Found
      </Text>
      <Text style={[styles.emptySubtitle, { color: theme.colors.textSecondary }]}>
        No {contentType === 'all' ? 'shared content' : contentType} found with {contact.primaryName}
      </Text>
    </View>
  );

  const renderHeader = () => (
    <View style={[styles.header, { backgroundColor: theme.colors.surface }]}>
      <Text style={[styles.headerTitle, { color: theme.colors.text }]}>
        Shared Content with {contact.primaryName}
      </Text>
      <Text style={[styles.headerSubtitle, { color: theme.colors.textSecondary }]}>
        {files.length} files • {links.length} links
      </Text>
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      {renderHeader()}
      {renderFilterTabs()}
      
      {sortedContent.length === 0 ? (
        renderEmptyState()
      ) : (
        <FlatList
          data={sortedContent}
          renderItem={renderContentItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContainer}
          ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
          onRefresh={onRefresh}
          refreshing={loading}
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
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
  },
  filterContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingBottom: 8,
  },
  filterTabs: {
    flexDirection: 'row',
    gap: 8,
  },
  filterTab: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
  },
  filterTabText: {
    fontSize: 14,
    fontWeight: '500',
  },
  sortButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
  },
  sortButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  listContainer: {
    padding: 16,
  },
  contentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  contentIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  contentInfo: {
    flex: 1,
  },
  contentTitle: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 4,
  },
  contentSubtitle: {
    fontSize: 14,
    marginBottom: 4,
  },
  contentMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  contentMetaText: {
    fontSize: 12,
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