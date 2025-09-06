/**
 * RelationshipInsights Component
 * 
 * Displays AI-generated relationship insights with sentiment analysis and communication patterns
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';
import { UnifiedContact, RelationshipInsight, SentimentData } from '../types';

interface RelationshipInsightsProps {
  contact: UnifiedContact;
  insights: RelationshipInsight[];
  sentimentData?: SentimentData;
  loading?: boolean;
  onRefreshInsights?: () => void;
  onInsightFeedback?: (insightId: string, feedback: 'helpful' | 'not_helpful' | 'incorrect') => void;
  onActionPress?: (action: string, insightId: string) => void;
}

interface InsightCardProps {
  insight: RelationshipInsight;
  onFeedback: (feedback: 'helpful' | 'not_helpful' | 'incorrect') => void;
  onActionPress: (action: string) => void;
}

const InsightCard: React.FC<InsightCardProps> = ({ insight, onFeedback, onActionPress }) => {
  const { theme } = useTheme();
  const [showActions, setShowActions] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);

  const getInsightIcon = (type: string) => {
    const icons: Record<string, string> = {
      communication_frequency: 'chatbubbles',
      sentiment_analysis: 'happy',
      network_analysis: 'people',
      response_pattern: 'time',
      relationship_strength: 'heart',
      communication_pattern: 'analytics',
      platform_preference: 'apps',
      relationship_opportunity: 'trending-up',
    };
    return icons[type] || 'information-circle';
  };

  const getInsightColor = (type: string) => {
    const colors: Record<string, string> = {
      communication_frequency: theme.colors.primary,
      sentiment_analysis: theme.colors.success,
      network_analysis: theme.colors.warning,
      response_pattern: theme.colors.info,
      relationship_strength: theme.colors.error,
      communication_pattern: theme.colors.primary,
      platform_preference: theme.colors.secondary,
      relationship_opportunity: theme.colors.success,
    };
    return colors[type] || theme.colors.primary;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return theme.colors.success;
    if (confidence >= 0.6) return theme.colors.warning;
    return theme.colors.error;
  };

  const handleFeedback = (feedback: 'helpful' | 'not_helpful' | 'incorrect') => {
    onFeedback(feedback);
    setFeedbackGiven(true);
  };

  const handleActionPress = (action: string) => {
    Alert.alert(
      'Suggested Action',
      action,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Take Action', onPress: () => onActionPress(action) },
      ]
    );
  };

  return (
    <View style={[styles.insightCard, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}>
      <View style={styles.insightHeader}>
        <View style={styles.insightTitleContainer}>
          <View style={[styles.insightIcon, { backgroundColor: getInsightColor(insight.type) + '20' }]}>
            <Icon
              name={getInsightIcon(insight.type)}
              size={20}
              color={getInsightColor(insight.type)}
            />
          </View>
          <View style={styles.insightTitleText}>
            <Text style={[styles.insightTitle, { color: theme.colors.text }]}>
              {insight.title}
            </Text>
            <View style={styles.confidenceContainer}>
              <View style={[styles.confidenceBadge, { backgroundColor: getConfidenceColor(insight.confidence) }]}>
                <Text style={[styles.confidenceText, { color: theme.colors.white }]}>
                  {Math.round(insight.confidence * 100)}% confident
                </Text>
              </View>
            </View>
          </View>
        </View>
        
        <TouchableOpacity
          style={styles.expandButton}
          onPress={() => setShowActions(!showActions)}
        >
          <Icon
            name={showActions ? 'chevron-up' : 'chevron-down'}
            size={20}
            color={theme.colors.textSecondary}
          />
        </TouchableOpacity>
      </View>

      <Text style={[styles.insightDescription, { color: theme.colors.textSecondary }]}>
        {insight.description}
      </Text>

      {showActions && (
        <View style={styles.actionsContainer}>
          {insight.suggested_actions && insight.suggested_actions.length > 0 && (
            <View style={styles.suggestedActions}>
              <Text style={[styles.actionsTitle, { color: theme.colors.text }]}>
                Suggested Actions:
              </Text>
              {insight.suggested_actions.map((action, index) => (
                <TouchableOpacity
                  key={index}
                  style={[styles.actionItem, { borderColor: theme.colors.border }]}
                  onPress={() => handleActionPress(action)}
                >
                  <Icon name="arrow-forward" size={16} color={theme.colors.primary} />
                  <Text style={[styles.actionText, { color: theme.colors.text }]}>
                    {action}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {!feedbackGiven && (
            <View style={styles.feedbackContainer}>
              <Text style={[styles.feedbackTitle, { color: theme.colors.text }]}>
                Was this insight helpful?
              </Text>
              <View style={styles.feedbackButtons}>
                <TouchableOpacity
                  style={[styles.feedbackButton, { backgroundColor: theme.colors.success + '20' }]}
                  onPress={() => handleFeedback('helpful')}
                >
                  <Icon name="thumbs-up" size={16} color={theme.colors.success} />
                  <Text style={[styles.feedbackButtonText, { color: theme.colors.success }]}>
                    Helpful
                  </Text>
                </TouchableOpacity>
                
                <TouchableOpacity
                  style={[styles.feedbackButton, { backgroundColor: theme.colors.warning + '20' }]}
                  onPress={() => handleFeedback('not_helpful')}
                >
                  <Icon name="thumbs-down" size={16} color={theme.colors.warning} />
                  <Text style={[styles.feedbackButtonText, { color: theme.colors.warning }]}>
                    Not Helpful
                  </Text>
                </TouchableOpacity>
                
                <TouchableOpacity
                  style={[styles.feedbackButton, { backgroundColor: theme.colors.error + '20' }]}
                  onPress={() => handleFeedback('incorrect')}
                >
                  <Icon name="close" size={16} color={theme.colors.error} />
                  <Text style={[styles.feedbackButtonText, { color: theme.colors.error }]}>
                    Incorrect
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {feedbackGiven && (
            <View style={styles.thankYouContainer}>
              <Icon name="checkmark-circle" size={20} color={theme.colors.success} />
              <Text style={[styles.thankYouText, { color: theme.colors.success }]}>
                Thank you for your feedback!
              </Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
};

export const RelationshipInsights: React.FC<RelationshipInsightsProps> = ({
  contact,
  insights,
  sentimentData,
  loading = false,
  onRefreshInsights,
  onInsightFeedback,
  onActionPress,
}) => {
  const { theme } = useTheme();

  const handleInsightFeedback = (insightId: string, feedback: 'helpful' | 'not_helpful' | 'incorrect') => {
    if (onInsightFeedback) {
      onInsightFeedback(insightId, feedback);
    }
  };

  const handleActionPress = (action: string, insightId: string) => {
    if (onActionPress) {
      onActionPress(action, insightId);
    }
  };

  const renderSentimentOverview = () => {
    if (!sentimentData) return null;

    const getSentimentIcon = (category: string) => {
      switch (category) {
        case 'positive': return 'happy';
        case 'negative': return 'sad';
        default: return 'remove';
      }
    };

    const getSentimentColor = (category: string) => {
      switch (category) {
        case 'positive': return theme.colors.success;
        case 'negative': return theme.colors.error;
        default: return theme.colors.warning;
      }
    };

    return (
      <View style={[styles.sentimentContainer, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.sentimentHeader}>
          <Icon
            name={getSentimentIcon(sentimentData.sentiment_category)}
            size={24}
            color={getSentimentColor(sentimentData.sentiment_category)}
          />
          <Text style={[styles.sentimentTitle, { color: theme.colors.text }]}>
            Overall Sentiment
          </Text>
        </View>
        
        <Text style={[styles.sentimentCategory, { color: getSentimentColor(sentimentData.sentiment_category) }]}>
          {sentimentData.sentiment_category.charAt(0).toUpperCase() + sentimentData.sentiment_category.slice(1)}
        </Text>
        
        <Text style={[styles.sentimentScore, { color: theme.colors.textSecondary }]}>
          Score: {sentimentData.overall_sentiment.toFixed(2)}
        </Text>

        {sentimentData.sentiment_distribution && (
          <View style={styles.sentimentDistribution}>
            <View style={styles.sentimentBar}>
              <View
                style={[
                  styles.sentimentSegment,
                  {
                    backgroundColor: theme.colors.success,
                    flex: sentimentData.sentiment_distribution.positive_avg,
                  },
                ]}
              />
              <View
                style={[
                  styles.sentimentSegment,
                  {
                    backgroundColor: theme.colors.warning,
                    flex: sentimentData.sentiment_distribution.neutral_avg,
                  },
                ]}
              />
              <View
                style={[
                  styles.sentimentSegment,
                  {
                    backgroundColor: theme.colors.error,
                    flex: sentimentData.sentiment_distribution.negative_avg,
                  },
                ]}
              />
            </View>
            
            <View style={styles.sentimentLegend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendColor, { backgroundColor: theme.colors.success }]} />
                <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>
                  Positive ({Math.round(sentimentData.sentiment_distribution.positive_avg * 100)}%)
                </Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendColor, { backgroundColor: theme.colors.warning }]} />
                <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>
                  Neutral ({Math.round(sentimentData.sentiment_distribution.neutral_avg * 100)}%)
                </Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendColor, { backgroundColor: theme.colors.error }]} />
                <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>
                  Negative ({Math.round(sentimentData.sentiment_distribution.negative_avg * 100)}%)
                </Text>
              </View>
            </View>
          </View>
        )}
      </View>
    );
  };

  const renderInsightsList = () => {
    if (insights.length === 0) {
      return (
        <View style={styles.emptyContainer}>
          <Icon name="bulb-outline" size={64} color={theme.colors.textSecondary} />
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
            No Insights Available
          </Text>
          <Text style={[styles.emptySubtitle, { color: theme.colors.textSecondary }]}>
            We're analyzing your communication patterns with {contact.primaryName}. Check back soon for insights!
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.insightsList}>
        {insights.map((insight) => (
          <InsightCard
            key={insight.id}
            insight={insight}
            onFeedback={(feedback) => handleInsightFeedback(insight.id, feedback)}
            onActionPress={(action) => handleActionPress(action, insight.id)}
          />
        ))}
      </View>
    );
  };

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: theme.colors.background }]}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
        <Text style={[styles.loadingText, { color: theme.colors.textSecondary }]}>
          Generating relationship insights...
        </Text>
      </View>
    );
  }

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.headerContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Relationship Insights
          </Text>
          <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
            AI-powered analysis of your relationship with {contact.primaryName}
          </Text>
        </View>
        
        {onRefreshInsights && (
          <TouchableOpacity
            style={[styles.refreshButton, { borderColor: theme.colors.border }]}
            onPress={onRefreshInsights}
          >
            <Icon name="refresh" size={20} color={theme.colors.primary} />
          </TouchableOpacity>
        )}
      </View>

      {renderSentimentOverview()}
      {renderInsightsList()}
    </ScrollView>
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    marginBottom: 8,
  },
  headerContent: {
    flex: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
  },
  refreshButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sentimentContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  sentimentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  sentimentTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  sentimentCategory: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  sentimentScore: {
    fontSize: 14,
    marginBottom: 16,
  },
  sentimentDistribution: {
    marginTop: 8,
  },
  sentimentBar: {
    flexDirection: 'row',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 12,
  },
  sentimentSegment: {
    height: '100%',
  },
  sentimentLegend: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  legendText: {
    fontSize: 12,
  },
  insightsList: {
    padding: 16,
    gap: 12,
  },
  insightCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  insightHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  insightTitleContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    flex: 1,
    gap: 12,
  },
  insightIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  insightTitleText: {
    flex: 1,
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 6,
  },
  confidenceContainer: {
    flexDirection: 'row',
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  confidenceText: {
    fontSize: 12,
    fontWeight: '500',
  },
  expandButton: {
    padding: 4,
  },
  insightDescription: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  actionsContainer: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 12,
    gap: 16,
  },
  suggestedActions: {
    gap: 8,
  },
  actionsTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
  },
  actionText: {
    fontSize: 14,
    flex: 1,
  },
  feedbackContainer: {
    gap: 8,
  },
  feedbackTitle: {
    fontSize: 14,
    fontWeight: '500',
  },
  feedbackButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  feedbackButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    gap: 4,
  },
  feedbackButtonText: {
    fontSize: 12,
    fontWeight: '500',
  },
  thankYouContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  thankYouText: {
    fontSize: 14,
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