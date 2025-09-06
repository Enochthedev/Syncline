/**
 * CommunicationTimeline Component
 * 
 * Displays communication timeline with interaction frequency analysis and trend visualization
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Dimensions,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { LineChart, AreaChart, BarChart } from 'react-native-chart-kit';
import { useTheme } from '../hooks/useTheme';
import { UnifiedContact, TimelineData, TrendAnalysis } from '../types';

interface CommunicationTimelineProps {
  contact: UnifiedContact;
  timelineData?: TimelineData;
  loading?: boolean;
  onRefresh?: () => void;
  onTimeRangeChange?: (range: TimeRange) => void;
}

type TimeRange = '7d' | '30d' | '90d' | '365d';
type ChartType = 'line' | 'area' | 'bar';

interface TimelinePoint {
  date: string;
  message_count: number;
  platform_count: number;
  avg_message_length: number;
  platforms: string[];
  platform_breakdown: Record<string, number>;
}

interface TimelineVisualizationData {
  timeline: TimelinePoint[];
  trend_analysis: TrendAnalysis;
  summary: {
    total_days: number;
    active_days: number;
    total_messages: number;
    avg_daily_messages: number;
    peak_day: TimelinePoint | null;
  };
}

export const CommunicationTimeline: React.FC<CommunicationTimelineProps> = ({
  contact,
  timelineData,
  loading = false,
  onRefresh,
  onTimeRangeChange,
}) => {
  const { theme } = useTheme();
  const [selectedRange, setSelectedRange] = useState<TimeRange>('30d');
  const [chartType, setChartType] = useState<ChartType>('line');
  const [selectedMetric, setSelectedMetric] = useState<'messages' | 'platforms' | 'length'>('messages');

  const screenWidth = Dimensions.get('window').width;
  const chartWidth = screenWidth - 32;

  const timeRanges: { key: TimeRange; label: string }[] = [
    { key: '7d', label: '7 Days' },
    { key: '30d', label: '30 Days' },
    { key: '90d', label: '3 Months' },
    { key: '365d', label: '1 Year' },
  ];

  const chartTypes: { key: ChartType; icon: string; label: string }[] = [
    { key: 'line', icon: 'trending-up', label: 'Line' },
    { key: 'area', icon: 'analytics', label: 'Area' },
    { key: 'bar', icon: 'bar-chart', label: 'Bar' },
  ];

  const metrics = [
    { key: 'messages' as const, label: 'Messages', icon: 'chatbubble' },
    { key: 'platforms' as const, label: 'Platforms', icon: 'apps' },
    { key: 'length' as const, label: 'Length', icon: 'text' },
  ];

  useEffect(() => {
    if (onTimeRangeChange) {
      onTimeRangeChange(selectedRange);
    }
  }, [selectedRange, onTimeRangeChange]);

  const formatChartData = () => {
    if (!timelineData?.timeline) {
      return null;
    }

    const timeline = timelineData.timeline;
    const labels = timeline.map(point => {
      const date = new Date(point.date);
      if (selectedRange === '7d') {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
      } else if (selectedRange === '30d') {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      } else {
        return date.toLocaleDateString('en-US', { month: 'short' });
      }
    });

    let dataValues: number[];
    switch (selectedMetric) {
      case 'messages':
        dataValues = timeline.map(point => point.message_count);
        break;
      case 'platforms':
        dataValues = timeline.map(point => point.platform_count);
        break;
      case 'length':
        dataValues = timeline.map(point => point.avg_message_length);
        break;
      default:
        dataValues = timeline.map(point => point.message_count);
    }

    return {
      labels: labels.slice(-20), // Show last 20 data points
      datasets: [{
        data: dataValues.slice(-20),
        color: (opacity = 1) => `rgba(${theme.colors.primaryRgb}, ${opacity})`,
        strokeWidth: 2,
      }],
    };
  };

  const chartConfig = {
    backgroundColor: theme.colors.surface,
    backgroundGradientFrom: theme.colors.surface,
    backgroundGradientTo: theme.colors.surface,
    decimalPlaces: selectedMetric === 'length' ? 1 : 0,
    color: (opacity = 1) => `rgba(${theme.colors.primaryRgb}, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(${theme.colors.textRgb}, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: theme.colors.primary,
    },
  };

  const renderTimeRangeSelector = () => (
    <View style={styles.selectorContainer}>
      <Text style={[styles.selectorLabel, { color: theme.colors.text }]}>Time Range</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.selectorScroll}>
        {timeRanges.map((range) => (
          <TouchableOpacity
            key={range.key}
            style={[
              styles.selectorButton,
              {
                backgroundColor: selectedRange === range.key ? theme.colors.primary : 'transparent',
                borderColor: theme.colors.border,
              },
            ]}
            onPress={() => setSelectedRange(range.key)}
          >
            <Text
              style={[
                styles.selectorButtonText,
                {
                  color: selectedRange === range.key ? theme.colors.white : theme.colors.text,
                },
              ]}
            >
              {range.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderMetricSelector = () => (
    <View style={styles.selectorContainer}>
      <Text style={[styles.selectorLabel, { color: theme.colors.text }]}>Metric</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.selectorScroll}>
        {metrics.map((metric) => (
          <TouchableOpacity
            key={metric.key}
            style={[
              styles.metricButton,
              {
                backgroundColor: selectedMetric === metric.key ? theme.colors.primary : 'transparent',
                borderColor: theme.colors.border,
              },
            ]}
            onPress={() => setSelectedMetric(metric.key)}
          >
            <Icon
              name={metric.icon}
              size={16}
              color={selectedMetric === metric.key ? theme.colors.white : theme.colors.primary}
            />
            <Text
              style={[
                styles.metricButtonText,
                {
                  color: selectedMetric === metric.key ? theme.colors.white : theme.colors.text,
                },
              ]}
            >
              {metric.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderChartTypeSelector = () => (
    <View style={styles.chartTypeContainer}>
      {chartTypes.map((type) => (
        <TouchableOpacity
          key={type.key}
          style={[
            styles.chartTypeButton,
            {
              backgroundColor: chartType === type.key ? theme.colors.primary : 'transparent',
              borderColor: theme.colors.border,
            },
          ]}
          onPress={() => setChartType(type.key)}
        >
          <Icon
            name={type.icon}
            size={20}
            color={chartType === type.key ? theme.colors.white : theme.colors.primary}
          />
        </TouchableOpacity>
      ))}
    </View>
  );

  const renderChart = () => {
    const chartData = formatChartData();
    if (!chartData) {
      return (
        <View style={[styles.emptyChart, { backgroundColor: theme.colors.surface }]}>
          <Icon name="analytics-outline" size={48} color={theme.colors.textSecondary} />
          <Text style={[styles.emptyChartText, { color: theme.colors.textSecondary }]}>
            No data available
          </Text>
        </View>
      );
    }

    const commonProps = {
      data: chartData,
      width: chartWidth,
      height: 220,
      chartConfig,
      bezier: true,
      style: styles.chart,
    };

    switch (chartType) {
      case 'area':
        return <AreaChart {...commonProps} />;
      case 'bar':
        return <BarChart {...commonProps} />;
      default:
        return <LineChart {...commonProps} />;
    }
  };

  const renderTrendAnalysis = () => {
    if (!timelineData?.trend_analysis) return null;

    const trend = timelineData.trend_analysis;
    const trendIcon = trend.trend === 'increasing' ? 'trending-up' : 
                     trend.trend === 'decreasing' ? 'trending-down' : 'remove';
    const trendColor = trend.trend === 'increasing' ? theme.colors.success :
                      trend.trend === 'decreasing' ? theme.colors.error : theme.colors.warning;

    return (
      <View style={[styles.trendContainer, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.trendHeader}>
          <Icon name={trendIcon} size={20} color={trendColor} />
          <Text style={[styles.trendTitle, { color: theme.colors.text }]}>
            Trend Analysis
          </Text>
        </View>
        
        <Text style={[styles.trendDescription, { color: theme.colors.textSecondary }]}>
          Communication is {trend.trend} with a correlation of {(trend.correlation * 100).toFixed(1)}%
        </Text>
        
        <View style={styles.trendMetrics}>
          <View style={styles.trendMetric}>
            <Text style={[styles.trendMetricLabel, { color: theme.colors.textSecondary }]}>
              Slope
            </Text>
            <Text style={[styles.trendMetricValue, { color: theme.colors.text }]}>
              {trend.slope.toFixed(3)}
            </Text>
          </View>
          
          <View style={styles.trendMetric}>
            <Text style={[styles.trendMetricLabel, { color: theme.colors.textSecondary }]}>
              Strength
            </Text>
            <Text style={[styles.trendMetricValue, { color: theme.colors.text }]}>
              {(trend.strength * 100).toFixed(1)}%
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const renderSummaryStats = () => {
    if (!timelineData?.summary) return null;

    const summary = timelineData.summary;

    return (
      <View style={[styles.summaryContainer, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.summaryTitle, { color: theme.colors.text }]}>
          Summary Statistics
        </Text>
        
        <View style={styles.summaryGrid}>
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryValue, { color: theme.colors.primary }]}>
              {summary.total_messages}
            </Text>
            <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
              Total Messages
            </Text>
          </View>
          
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryValue, { color: theme.colors.primary }]}>
              {summary.active_days}
            </Text>
            <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
              Active Days
            </Text>
          </View>
          
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryValue, { color: theme.colors.primary }]}>
              {summary.avg_daily_messages.toFixed(1)}
            </Text>
            <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
              Avg Daily
            </Text>
          </View>
          
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryValue, { color: theme.colors.primary }]}>
              {summary.peak_day ? new Date(summary.peak_day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'N/A'}
            </Text>
            <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
              Peak Day
            </Text>
          </View>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: theme.colors.background }]}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
        <Text style={[styles.loadingText, { color: theme.colors.textSecondary }]}>
          Analyzing communication timeline...
        </Text>
      </View>
    );
  }

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.headerContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Communication Timeline
          </Text>
          <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
            with {contact.primaryName}
          </Text>
        </View>
        
        {onRefresh && (
          <TouchableOpacity
            style={[styles.refreshButton, { borderColor: theme.colors.border }]}
            onPress={onRefresh}
          >
            <Icon name="refresh" size={20} color={theme.colors.primary} />
          </TouchableOpacity>
        )}
      </View>

      {renderTimeRangeSelector()}
      {renderMetricSelector()}
      
      <View style={[styles.chartContainer, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.chartHeader}>
          <Text style={[styles.chartTitle, { color: theme.colors.text }]}>
            {metrics.find(m => m.key === selectedMetric)?.label} Over Time
          </Text>
          {renderChartTypeSelector()}
        </View>
        
        {renderChart()}
      </View>

      {renderTrendAnalysis()}
      {renderSummaryStats()}
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
  },
  refreshButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectorContainer: {
    marginBottom: 8,
    paddingHorizontal: 16,
  },
  selectorLabel: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
  },
  selectorScroll: {
    flexDirection: 'row',
  },
  selectorButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    marginRight: 8,
  },
  selectorButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  metricButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    borderWidth: 1,
    marginRight: 8,
    gap: 6,
  },
  metricButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  chartContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  chartHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  chartTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  chartTypeContainer: {
    flexDirection: 'row',
    gap: 4,
  },
  chartTypeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  emptyChart: {
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
  },
  emptyChartText: {
    marginTop: 8,
    fontSize: 16,
  },
  trendContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  trendHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  trendTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  trendDescription: {
    fontSize: 14,
    marginBottom: 12,
  },
  trendMetrics: {
    flexDirection: 'row',
    gap: 24,
  },
  trendMetric: {
    alignItems: 'center',
  },
  trendMetricLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  trendMetricValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  summaryContainer: {
    margin: 16,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  summaryTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
  },
  summaryItem: {
    flex: 1,
    minWidth: '45%',
    alignItems: 'center',
  },
  summaryValue: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  summaryLabel: {
    fontSize: 12,
    textAlign: 'center',
  },
});