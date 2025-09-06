/**
 * Search Results Filter Component
 * 
 * Provides filtering controls for search results based on detected intent
 * and extracted entities from natural language queries.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '@/hooks/useTheme';
import { SearchResult } from '@/types';

export interface FilterOptions {
  intent?: string;
  resultTypes: string[];
  platforms: string[];
  timeRange: string;
  contacts: string[];
  hasAttachments?: boolean;
}

export interface SearchResultsFilterProps {
  results: SearchResult[];
  onFilteredResultsChange: (filteredResults: SearchResult[]) => void;
  detectedIntent?: string;
  extractedEntities?: any[];
  initialFilters?: Partial<FilterOptions>;
}

export function SearchResultsFilter({
  results,
  onFilteredResultsChange,
  detectedIntent,
  extractedEntities = [],
  initialFilters = {},
}: SearchResultsFilterProps) {
  const { colors } = useTheme();
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [filters, setFilters] = useState<FilterOptions>({
    intent: detectedIntent,
    resultTypes: initialFilters.resultTypes || [],
    platforms: initialFilters.platforms || [],
    timeRange: initialFilters.timeRange || 'all',
    contacts: initialFilters.contacts || [],
    hasAttachments: initialFilters.hasAttachments,
  });

  // Get available filter options from results
  const getAvailableOptions = useCallback(() => {
    const types = new Set<string>();
    const platforms = new Set<string>();
    const contacts = new Set<string>();

    results.forEach(result => {
      types.add(result.type);
      if (result.platform) platforms.add(result.platform);
      if (result.contact?.displayName) contacts.add(result.contact.displayName);
    });

    return {
      types: Array.from(types),
      platforms: Array.from(platforms),
      contacts: Array.from(contacts),
    };
  }, [results]);

  // Apply filters to results
  const applyFilters = useCallback((currentFilters: FilterOptions) => {
    let filteredResults = [...results];

    // Filter by result type
    if (currentFilters.resultTypes.length > 0) {
      filteredResults = filteredResults.filter(result =>
        currentFilters.resultTypes.includes(result.type)
      );
    }

    // Filter by platform
    if (currentFilters.platforms.length > 0) {
      filteredResults = filteredResults.filter(result =>
        result.platform && currentFilters.platforms.includes(result.platform)
      );
    }

    // Filter by contact
    if (currentFilters.contacts.length > 0) {
      filteredResults = filteredResults.filter(result =>
        result.contact?.displayName && 
        currentFilters.contacts.includes(result.contact.displayName)
      );
    }

    // Filter by time range
    if (currentFilters.timeRange !== 'all') {
      const now = new Date();
      const cutoffDate = new Date();

      switch (currentFilters.timeRange) {
        case 'today':
          cutoffDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          cutoffDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          cutoffDate.setMonth(now.getMonth() - 1);
          break;
        case 'year':
          cutoffDate.setFullYear(now.getFullYear() - 1);
          break;
      }

      if (currentFilters.timeRange !== 'all') {
        filteredResults = filteredResults.filter(result =>
          result.timestamp >= cutoffDate
        );
      }
    }

    // Filter by attachments
    if (currentFilters.hasAttachments !== undefined) {
      filteredResults = filteredResults.filter(result => {
        const hasAttachments = result.type === 'file' || 
          (result as any).attachments?.length > 0;
        return currentFilters.hasAttachments ? hasAttachments : !hasAttachments;
      });
    }

    onFilteredResultsChange(filteredResults);
  }, [results, onFilteredResultsChange]);

  // Handle filter change
  const handleFilterChange = useCallback((newFilters: Partial<FilterOptions>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    applyFilters(updatedFilters);
  }, [filters, applyFilters]);

  // Toggle filter value in array
  const toggleArrayFilter = useCallback((
    filterKey: keyof FilterOptions,
    value: string
  ) => {
    const currentArray = (filters[filterKey] as string[]) || [];
    const newArray = currentArray.includes(value)
      ? currentArray.filter(item => item !== value)
      : [...currentArray, value];
    
    handleFilterChange({ [filterKey]: newArray });
  }, [filters, handleFilterChange]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    const clearedFilters: FilterOptions = {
      intent: detectedIntent,
      resultTypes: [],
      platforms: [],
      timeRange: 'all',
      contacts: [],
      hasAttachments: undefined,
    };
    setFilters(clearedFilters);
    applyFilters(clearedFilters);
  }, [detectedIntent, applyFilters]);

  // Get active filter count
  const getActiveFilterCount = useCallback(() => {
    let count = 0;
    if (filters.resultTypes.length > 0) count++;
    if (filters.platforms.length > 0) count++;
    if (filters.timeRange !== 'all') count++;
    if (filters.contacts.length > 0) count++;
    if (filters.hasAttachments !== undefined) count++;
    return count;
  }, [filters]);

  const availableOptions = getAvailableOptions();
  const activeFilterCount = getActiveFilterCount();

  // Get intent-based quick filters
  const getIntentQuickFilters = useCallback(() => {
    const quickFilters: Array<{ label: string; action: () => void }> = [];

    switch (detectedIntent) {
      case 'person_messages':
      case 'person_search':
        quickFilters.push({
          label: 'Messages Only',
          action: () => handleFilterChange({ resultTypes: ['message'] }),
        });
        break;
      
      case 'file_search':
        quickFilters.push({
          label: 'Files Only',
          action: () => handleFilterChange({ resultTypes: ['file'] }),
        });
        break;
      
      case 'commitment_search':
        quickFilters.push({
          label: 'Commitments Only',
          action: () => handleFilterChange({ resultTypes: ['commitment'] }),
        });
        break;
    }

    // Add entity-based filters
    extractedEntities.forEach(entity => {
      if (entity.type === 'PERSON' && availableOptions.contacts.includes(entity.text)) {
        quickFilters.push({
          label: `From ${entity.text}`,
          action: () => handleFilterChange({ contacts: [entity.text] }),
        });
      }
    });

    return quickFilters;
  }, [detectedIntent, extractedEntities, availableOptions.contacts, handleFilterChange]);

  const intentQuickFilters = getIntentQuickFilters();

  return (
    <View style={styles.container}>
      {/* Filter Header */}
      <View style={styles.filterHeader}>
        <TouchableOpacity
          style={[styles.filterButton, { backgroundColor: colors.surface, borderColor: colors.border }]}
          onPress={() => setShowFilterModal(true)}
        >
          <Icon name="filter" size={16} color={colors.text} />
          <Text style={[styles.filterButtonText, { color: colors.text }]}>
            Filter
          </Text>
          {activeFilterCount > 0 && (
            <View style={[styles.filterBadge, { backgroundColor: colors.primary }]}>
              <Text style={[styles.filterBadgeText, { color: colors.onPrimary }]}>
                {activeFilterCount}
              </Text>
            </View>
          )}
        </TouchableOpacity>

        {/* Quick Filters */}
        {intentQuickFilters.length > 0 && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.quickFiltersContainer}
          >
            {intentQuickFilters.map((filter, index) => (
              <TouchableOpacity
                key={index}
                style={[styles.quickFilterChip, { backgroundColor: colors.primaryLight }]}
                onPress={filter.action}
              >
                <Text style={[styles.quickFilterText, { color: colors.primary }]}>
                  {filter.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}
      </View>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <View style={styles.activeFiltersContainer}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {filters.resultTypes.map(type => (
              <View key={type} style={[styles.activeFilterChip, { backgroundColor: colors.surface }]}>
                <Text style={[styles.activeFilterText, { color: colors.text }]}>
                  {formatFilterLabel('type', type)}
                </Text>
                <TouchableOpacity onPress={() => toggleArrayFilter('resultTypes', type)}>
                  <Icon name="close" size={14} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
            ))}
            
            {filters.platforms.map(platform => (
              <View key={platform} style={[styles.activeFilterChip, { backgroundColor: colors.surface }]}>
                <Text style={[styles.activeFilterText, { color: colors.text }]}>
                  {platform}
                </Text>
                <TouchableOpacity onPress={() => toggleArrayFilter('platforms', platform)}>
                  <Icon name="close" size={14} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
            ))}

            {filters.timeRange !== 'all' && (
              <View style={[styles.activeFilterChip, { backgroundColor: colors.surface }]}>
                <Text style={[styles.activeFilterText, { color: colors.text }]}>
                  {formatFilterLabel('time', filters.timeRange)}
                </Text>
                <TouchableOpacity onPress={() => handleFilterChange({ timeRange: 'all' })}>
                  <Icon name="close" size={14} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
            )}

            <TouchableOpacity
              style={[styles.clearFiltersButton, { borderColor: colors.border }]}
              onPress={clearFilters}
            >
              <Text style={[styles.clearFiltersText, { color: colors.textSecondary }]}>
                Clear All
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      )}

      {/* Filter Modal */}
      <Modal
        visible={showFilterModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowFilterModal(false)}
      >
        <View style={[styles.modalContainer, { backgroundColor: colors.background }]}>
          <View style={[styles.modalHeader, { borderBottomColor: colors.border }]}>
            <Text style={[styles.modalTitle, { color: colors.text }]}>Filter Results</Text>
            <TouchableOpacity onPress={() => setShowFilterModal(false)}>
              <Icon name="close" size={24} color={colors.text} />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalContent}>
            {/* Result Types */}
            {availableOptions.types.length > 1 && (
              <FilterSection
                title="Result Types"
                options={availableOptions.types}
                selectedOptions={filters.resultTypes}
                onToggle={(value) => toggleArrayFilter('resultTypes', value)}
                colors={colors}
                formatLabel={(value) => formatFilterLabel('type', value)}
              />
            )}

            {/* Platforms */}
            {availableOptions.platforms.length > 1 && (
              <FilterSection
                title="Platforms"
                options={availableOptions.platforms}
                selectedOptions={filters.platforms}
                onToggle={(value) => toggleArrayFilter('platforms', value)}
                colors={colors}
              />
            )}

            {/* Time Range */}
            <FilterSection
              title="Time Range"
              options={['all', 'today', 'week', 'month', 'year']}
              selectedOptions={[filters.timeRange]}
              onToggle={(value) => handleFilterChange({ timeRange: value })}
              colors={colors}
              singleSelect
              formatLabel={(value) => formatFilterLabel('time', value)}
            />

            {/* Contacts */}
            {availableOptions.contacts.length > 1 && (
              <FilterSection
                title="Contacts"
                options={availableOptions.contacts}
                selectedOptions={filters.contacts}
                onToggle={(value) => toggleArrayFilter('contacts', value)}
                colors={colors}
              />
            )}
          </ScrollView>

          <View style={[styles.modalFooter, { borderTopColor: colors.border }]}>
            <TouchableOpacity
              style={[styles.clearButton, { borderColor: colors.border }]}
              onPress={clearFilters}
            >
              <Text style={[styles.clearButtonText, { color: colors.textSecondary }]}>
                Clear All
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.applyButton, { backgroundColor: colors.primary }]}
              onPress={() => setShowFilterModal(false)}
            >
              <Text style={[styles.applyButtonText, { color: colors.onPrimary }]}>
                Apply Filters
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// Filter Section Component
interface FilterSectionProps {
  title: string;
  options: string[];
  selectedOptions: string[];
  onToggle: (value: string) => void;
  colors: any;
  singleSelect?: boolean;
  formatLabel?: (value: string) => string;
}

function FilterSection({
  title,
  options,
  selectedOptions,
  onToggle,
  colors,
  singleSelect = false,
  formatLabel = (value) => value,
}: FilterSectionProps) {
  return (
    <View style={styles.filterSection}>
      <Text style={[styles.sectionTitle, { color: colors.text }]}>{title}</Text>
      <View style={styles.optionsContainer}>
        {options.map(option => {
          const isSelected = selectedOptions.includes(option);
          return (
            <TouchableOpacity
              key={option}
              style={[
                styles.optionChip,
                {
                  backgroundColor: isSelected ? colors.primary : colors.surface,
                  borderColor: colors.border,
                },
              ]}
              onPress={() => onToggle(option)}
            >
              <Text
                style={[
                  styles.optionText,
                  { color: isSelected ? colors.onPrimary : colors.text },
                ]}
              >
                {formatLabel(option)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

// Helper function to format filter labels
function formatFilterLabel(category: string, value: string): string {
  switch (category) {
    case 'type':
      const typeMap: Record<string, string> = {
        message: 'Messages',
        file: 'Files',
        contact: 'Contacts',
        commitment: 'Commitments',
        thread: 'Conversations',
      };
      return typeMap[value] || value;
    
    case 'time':
      const timeMap: Record<string, string> = {
        all: 'All Time',
        today: 'Today',
        week: 'This Week',
        month: 'This Month',
        year: 'This Year',
      };
      return timeMap[value] || value;
    
    default:
      return value;
  }
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  filterHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    marginRight: 12,
  },
  filterButtonText: {
    fontSize: 14,
    marginLeft: 6,
  },
  filterBadge: {
    marginLeft: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    minWidth: 20,
    alignItems: 'center',
  },
  filterBadgeText: {
    fontSize: 12,
    fontWeight: '600',
  },
  quickFiltersContainer: {
    flex: 1,
  },
  quickFilterChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  quickFilterText: {
    fontSize: 12,
    fontWeight: '500',
  },
  activeFiltersContainer: {
    marginBottom: 8,
  },
  activeFilterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 8,
  },
  activeFilterText: {
    fontSize: 12,
    marginRight: 4,
  },
  clearFiltersButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
  },
  clearFiltersText: {
    fontSize: 12,
  },
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  filterSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  optionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  optionChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    borderWidth: 1,
  },
  optionText: {
    fontSize: 14,
  },
  modalFooter: {
    flexDirection: 'row',
    padding: 16,
    borderTopWidth: 1,
    gap: 12,
  },
  clearButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  clearButtonText: {
    fontSize: 16,
  },
  applyButton: {
    flex: 2,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  applyButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
});