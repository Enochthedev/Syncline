import React, { memo, useCallback, useMemo, useRef, useState } from 'react';
import {
  FlatList,
  FlatListProps,
  ViewToken,
  ListRenderItem,
  RefreshControl,
  View,
  Text,
  StyleSheet,
  Dimensions,
} from 'react-native';
import FastImage from 'react-native-fast-image';
import MemoryManager from '../services/memoryManager';

const { height: screenHeight } = Dimensions.get('window');

export interface OptimizedFlatListProps<T> extends Omit<FlatListProps<T>, 'renderItem'> {
  data: T[];
  renderItem: ListRenderItem<T>;
  keyExtractor: (item: T, index: number) => string;
  onRefresh?: () => Promise<void>;
  enableVirtualization?: boolean;
  enableImageOptimization?: boolean;
  enableMemoryOptimization?: boolean;
  itemHeight?: number;
  estimatedItemSize?: number;
  windowSize?: number;
  maxToRenderPerBatch?: number;
  updateCellsBatchingPeriod?: number;
  removeClippedSubviews?: boolean;
  loadingComponent?: React.ComponentType;
  emptyComponent?: React.ComponentType;
  errorComponent?: React.ComponentType<{ error: Error; onRetry: () => void }>;
  onEndReachedThreshold?: number;
  onEndReached?: () => void;
  enablePullToRefresh?: boolean;
  enableInfiniteScroll?: boolean;
}

interface ViewabilityConfig {
  itemVisiblePercentThreshold: number;
  minimumViewTime: number;
}

const OptimizedFlatList = <T extends any>({
  data,
  renderItem,
  keyExtractor,
  onRefresh,
  enableVirtualization = true,
  enableImageOptimization = true,
  enableMemoryOptimization = true,
  itemHeight,
  estimatedItemSize = 100,
  windowSize = 10,
  maxToRenderPerBatch = 10,
  updateCellsBatchingPeriod = 50,
  removeClippedSubviews = true,
  loadingComponent: LoadingComponent,
  emptyComponent: EmptyComponent,
  errorComponent: ErrorComponent,
  onEndReachedThreshold = 0.1,
  onEndReached,
  enablePullToRefresh = true,
  enableInfiniteScroll = true,
  ...otherProps
}: OptimizedFlatListProps<T>) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [visibleItems, setVisibleItems] = useState<Set<string>>(new Set());
  
  const flatListRef = useRef<FlatList<T>>(null);
  const memoryManager = useRef(MemoryManager.getInstance());
  const viewabilityConfig = useRef<ViewabilityConfig>({
    itemVisiblePercentThreshold: 50,
    minimumViewTime: 100,
  });

  // Optimized item renderer with memory management
  const optimizedRenderItem = useCallback<ListRenderItem<T>>(
    ({ item, index }) => {
      const itemKey = keyExtractor(item, index);
      
      try {
        return (
          <OptimizedListItem
            key={itemKey}
            item={item}
            index={index}
            renderItem={renderItem}
            isVisible={visibleItems.has(itemKey)}
            enableImageOptimization={enableImageOptimization}
            enableMemoryOptimization={enableMemoryOptimization}
          />
        );
      } catch (error) {
        console.error('Error rendering list item:', error);
        return (
          <View style={styles.errorItem}>
            <Text style={styles.errorText}>Failed to render item</Text>
          </View>
        );
      }
    },
    [renderItem, keyExtractor, visibleItems, enableImageOptimization, enableMemoryOptimization]
  );

  // Handle viewability changes for memory optimization
  const onViewableItemsChanged = useCallback(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      if (!enableMemoryOptimization) return;

      const newVisibleItems = new Set<string>();
      viewableItems.forEach(({ item, index }) => {
        if (item && index !== null) {
          const key = keyExtractor(item, index);
          newVisibleItems.add(key);
        }
      });

      setVisibleItems(newVisibleItems);

      // Cleanup memory for items that are no longer visible
      if (newVisibleItems.size < visibleItems.size) {
        // Trigger memory cleanup when many items become invisible
        memoryManager.current.forceCleanup().catch(error => {
          console.error('Failed to cleanup memory:', error);
        });
      }
    },
    [keyExtractor, enableMemoryOptimization, visibleItems]
  );

  // Handle pull-to-refresh
  const handleRefresh = useCallback(async () => {
    if (!onRefresh || isRefreshing) return;

    setIsRefreshing(true);
    setError(null);

    try {
      await onRefresh();
    } catch (error) {
      console.error('Refresh failed:', error);
      setError(error as Error);
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh, isRefreshing]);

  // Handle infinite scroll
  const handleEndReached = useCallback(() => {
    if (!enableInfiniteScroll || !onEndReached) return;
    
    try {
      onEndReached();
    } catch (error) {
      console.error('End reached handler failed:', error);
      setError(error as Error);
    }
  }, [enableInfiniteScroll, onEndReached]);

  // Retry function for error state
  const handleRetry = useCallback(() => {
    setError(null);
    if (onRefresh) {
      handleRefresh();
    }
  }, [onRefresh, handleRefresh]);

  // Memoized refresh control
  const refreshControl = useMemo(() => {
    if (!enablePullToRefresh) return undefined;
    
    return (
      <RefreshControl
        refreshing={isRefreshing}
        onRefresh={handleRefresh}
        tintColor="#007AFF"
        colors={['#007AFF']}
      />
    );
  }, [enablePullToRefresh, isRefreshing, handleRefresh]);

  // Calculate optimized props based on configuration
  const optimizedProps = useMemo(() => {
    const props: Partial<FlatListProps<T>> = {};

    if (enableVirtualization) {
      props.windowSize = windowSize;
      props.maxToRenderPerBatch = maxToRenderPerBatch;
      props.updateCellsBatchingPeriod = updateCellsBatchingPeriod;
      props.removeClippedSubviews = removeClippedSubviews;
      
      if (itemHeight) {
        props.getItemLayout = (data, index) => ({
          length: itemHeight,
          offset: itemHeight * index,
          index,
        });
      }
    }

    return props;
  }, [
    enableVirtualization,
    windowSize,
    maxToRenderPerBatch,
    updateCellsBatchingPeriod,
    removeClippedSubviews,
    itemHeight,
  ]);

  // Error state
  if (error && ErrorComponent) {
    return <ErrorComponent error={error} onRetry={handleRetry} />;
  }

  // Empty state
  if (data.length === 0 && !isRefreshing && EmptyComponent) {
    return <EmptyComponent />;
  }

  return (
    <FlatList
      ref={flatListRef}
      data={data}
      renderItem={optimizedRenderItem}
      keyExtractor={keyExtractor}
      refreshControl={refreshControl}
      onViewableItemsChanged={onViewableItemsChanged}
      viewabilityConfig={viewabilityConfig.current}
      onEndReached={handleEndReached}
      onEndReachedThreshold={onEndReachedThreshold}
      initialNumToRender={10}
      {...optimizedProps}
      {...otherProps}
    />
  );
};

// Optimized list item component
interface OptimizedListItemProps<T> {
  item: T;
  index: number;
  renderItem: ListRenderItem<T>;
  isVisible: boolean;
  enableImageOptimization: boolean;
  enableMemoryOptimization: boolean;
}

const OptimizedListItem = memo(<T extends any>({
  item,
  index,
  renderItem,
  isVisible,
  enableImageOptimization,
  enableMemoryOptimization,
}: OptimizedListItemProps<T>) => {
  // Don't render complex content for invisible items if memory optimization is enabled
  if (enableMemoryOptimization && !isVisible) {
    return (
      <View style={[styles.placeholder, { height: 100 }]}>
        <View style={styles.placeholderContent} />
      </View>
    );
  }

  return renderItem({ item, index, separators: {} as any });
});

// Optimized image component for lists
export const OptimizedListImage: React.FC<{
  source: { uri: string } | number;
  style?: any;
  placeholder?: React.ComponentType;
  fallback?: React.ComponentType;
}> = memo(({ source, style, placeholder: Placeholder, fallback: Fallback }) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  const handleLoadStart = useCallback(() => {
    setImageLoading(true);
    setImageError(false);
  }, []);

  const handleLoad = useCallback(() => {
    setImageLoading(false);
  }, []);

  const handleError = useCallback(() => {
    setImageLoading(false);
    setImageError(true);
  }, []);

  if (imageError && Fallback) {
    return <Fallback />;
  }

  return (
    <View style={style}>
      <FastImage
        source={source}
        style={StyleSheet.absoluteFillObject}
        onLoadStart={handleLoadStart}
        onLoad={handleLoad}
        onError={handleError}
        resizeMode={FastImage.resizeMode.cover}
        priority={FastImage.priority.normal}
      />
      {imageLoading && Placeholder && (
        <View style={StyleSheet.absoluteFillObject}>
          <Placeholder />
        </View>
      )}
    </View>
  );
});

const styles = StyleSheet.create({
  errorItem: {
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffebee',
    marginVertical: 2,
    marginHorizontal: 16,
    borderRadius: 8,
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
  },
  placeholder: {
    backgroundColor: '#f5f5f5',
    marginVertical: 2,
    marginHorizontal: 16,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderContent: {
    width: '80%',
    height: 20,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
  },
});

export default OptimizedFlatList;