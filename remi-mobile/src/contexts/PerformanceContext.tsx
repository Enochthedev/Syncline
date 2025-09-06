import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import PerformanceManager from '../services/performanceManager';
import MemoryManager from '../services/memoryManager';
import BatteryOptimizer from '../services/batteryOptimizer';
import NetworkOptimizer from '../services/networkOptimizer';
import PerformanceConfig, { PerformanceProfile, DeviceCapabilities } from '../utils/performanceConfig';
import type { PerformanceMetrics, MemoryStats } from '../services/performanceManager';
import type { BatteryStats, PowerSavingMode } from '../services/batteryOptimizer';

interface PerformanceContextType {
  // Performance data
  metrics: PerformanceMetrics | null;
  memoryStats: MemoryStats | null;
  batteryStats: BatteryStats | null;
  powerSavingMode: PowerSavingMode | null;
  deviceCapabilities: DeviceCapabilities | null;
  currentProfile: PerformanceProfile | null;
  
  // Performance controls
  isMonitoring: boolean;
  startMonitoring: () => void;
  stopMonitoring: () => void;
  
  // Memory management
  forceMemoryCleanup: () => Promise<void>;
  getMemoryStats: () => Promise<MemoryStats>;
  
  // Battery optimization
  setBatteryOptimization: (enabled: boolean) => void;
  forcePowerSavingMode: (level: PowerSavingMode['level']) => void;
  
  // Performance measurement
  recordScreenTransition: (duration: number) => void;
  recordSearchResponse: (duration: number) => void;
  measureAsync: <T>(operation: () => Promise<T>, type?: string) => Promise<T>;
  
  // Configuration
  updatePerformanceProfile: (profile: Partial<PerformanceProfile>) => void;
  getAdaptiveConfig: () => Promise<any>;
  
  // Export and diagnostics
  exportPerformanceData: () => Promise<string>;
  getPerformanceRecommendations: () => string[];
}

const PerformanceContext = createContext<PerformanceContextType | undefined>(undefined);

interface PerformanceProviderProps {
  children: ReactNode;
}

export const PerformanceProvider: React.FC<PerformanceProviderProps> = ({ children }) => {
  // State
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [batteryStats, setBatteryStats] = useState<BatteryStats | null>(null);
  const [powerSavingMode, setPowerSavingMode] = useState<PowerSavingMode | null>(null);
  const [deviceCapabilities, setDeviceCapabilities] = useState<DeviceCapabilities | null>(null);
  const [currentProfile, setCurrentProfile] = useState<PerformanceProfile | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);

  // Service instances
  const performanceManager = PerformanceManager.getInstance();
  const memoryManager = MemoryManager.getInstance();
  const batteryOptimizer = BatteryOptimizer.getInstance();
  const performanceConfig = PerformanceConfig.getInstance();

  // Initialize performance monitoring
  useEffect(() => {
    const initializePerformance = async () => {
      try {
        // Get device capabilities and profile
        const capabilities = performanceConfig.getDeviceCapabilities();
        const profile = performanceConfig.getCurrentProfile();
        
        setDeviceCapabilities(capabilities);
        setCurrentProfile(profile);

        // Start monitoring
        startMonitoring();

        // Setup battery monitoring
        const batteryUnsubscribe = batteryOptimizer.onBatteryChange((stats) => {
          setBatteryStats(stats);
        });

        const powerModeUnsubscribe = batteryOptimizer.onPowerModeChange((mode) => {
          setPowerSavingMode(mode);
        });

        // Setup memory monitoring
        const memoryUnsubscribe = memoryManager.onMemoryWarning((stats) => {
          setMemoryStats(stats);
          console.warn('Memory warning received in context:', stats);
        });

        // Cleanup function
        return () => {
          batteryUnsubscribe();
          powerModeUnsubscribe();
          memoryUnsubscribe();
        };
      } catch (error) {
        console.error('Failed to initialize performance monitoring:', error);
      }
    };

    initializePerformance();
  }, []);

  // Update metrics periodically
  useEffect(() => {
    if (!isMonitoring) return;

    const updateMetrics = async () => {
      try {
        const latestMetrics = performanceManager.getLatestMetrics();
        const latestMemoryStats = await memoryManager.getMemoryStats();
        const latestBatteryStats = batteryOptimizer.getCurrentStats();
        const latestPowerMode = batteryOptimizer.getPowerSavingMode();

        setMetrics(latestMetrics);
        setMemoryStats(latestMemoryStats);
        setBatteryStats(latestBatteryStats);
        setPowerSavingMode(latestPowerMode);
      } catch (error) {
        console.error('Failed to update performance metrics:', error);
      }
    };

    // Initial update
    updateMetrics();

    // Set up periodic updates
    const interval = setInterval(updateMetrics, 60000); // Every minute

    return () => clearInterval(interval);
  }, [isMonitoring]);

  // Performance controls
  const startMonitoring = () => {
    if (isMonitoring) return;
    
    performanceManager.startMonitoring();
    setIsMonitoring(true);
    console.log('Performance monitoring started');
  };

  const stopMonitoring = () => {
    if (!isMonitoring) return;
    
    performanceManager.stopMonitoring();
    setIsMonitoring(false);
    console.log('Performance monitoring stopped');
  };

  // Memory management
  const forceMemoryCleanup = async (): Promise<void> => {
    try {
      await memoryManager.forceCleanup();
      const updatedStats = await memoryManager.getMemoryStats();
      setMemoryStats(updatedStats);
      console.log('Memory cleanup completed');
    } catch (error) {
      console.error('Memory cleanup failed:', error);
      throw error;
    }
  };

  const getMemoryStats = async (): Promise<MemoryStats> => {
    try {
      const stats = await memoryManager.getMemoryStats();
      setMemoryStats(stats);
      return stats;
    } catch (error) {
      console.error('Failed to get memory stats:', error);
      throw error;
    }
  };

  // Battery optimization
  const setBatteryOptimization = (enabled: boolean): void => {
    try {
      const config = batteryOptimizer.getConfig();
      batteryOptimizer.updateConfig({
        ...config,
        enableBatteryMonitoring: enabled,
        aggressiveOptimizationEnabled: enabled,
      });
      console.log('Battery optimization', enabled ? 'enabled' : 'disabled');
    } catch (error) {
      console.error('Failed to update battery optimization:', error);
    }
  };

  const forcePowerSavingMode = (level: PowerSavingMode['level']): void => {
    try {
      batteryOptimizer.forcePowerSavingMode(level);
      console.log('Power saving mode set to:', level);
    } catch (error) {
      console.error('Failed to set power saving mode:', error);
    }
  };

  // Performance measurement
  const recordScreenTransition = (duration: number): void => {
    performanceManager.recordScreenTransition(duration);
  };

  const recordSearchResponse = (duration: number): void => {
    performanceManager.recordSearchResponse(duration);
  };

  const measureAsync = async <T>(
    operation: () => Promise<T>,
    type: string = 'operation'
  ): Promise<T> => {
    const startTime = Date.now();
    
    try {
      const result = await operation();
      const duration = Date.now() - startTime;
      
      // Record based on operation type
      if (type === 'search') {
        recordSearchResponse(duration);
      } else if (type === 'navigation') {
        recordScreenTransition(duration);
      }
      
      // Log slow operations
      if (duration > 1000) {
        console.warn(`Slow ${type} operation: ${duration}ms`);
      }
      
      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`Failed ${type} operation after ${duration}ms:`, error);
      throw error;
    }
  };

  // Configuration
  const updatePerformanceProfile = (profileUpdates: Partial<PerformanceProfile>): void => {
    try {
      if (!currentProfile) {
        console.error('No current profile to update');
        return;
      }

      const updatedProfile = performanceConfig.getCustomProfile(profileUpdates);
      performanceConfig.setProfile(updatedProfile);
      setCurrentProfile(updatedProfile);
      
      console.log('Performance profile updated:', updatedProfile.name);
    } catch (error) {
      console.error('Failed to update performance profile:', error);
    }
  };

  const getAdaptiveConfig = async () => {
    try {
      return await performanceConfig.getAdaptiveConfig();
    } catch (error) {
      console.error('Failed to get adaptive config:', error);
      throw error;
    }
  };

  // Export and diagnostics
  const exportPerformanceData = async (): Promise<string> => {
    try {
      const performanceData = await performanceManager.exportMetrics();
      const memoryData = memoryManager.getCacheStats();
      const batteryData = batteryOptimizer.getCurrentStats();
      const configData = performanceConfig.getCurrentProfile();

      const exportData = {
        timestamp: Date.now(),
        performance: JSON.parse(performanceData),
        memory: memoryData,
        battery: batteryData,
        config: configData,
        deviceCapabilities: deviceCapabilities,
      };

      return JSON.stringify(exportData, null, 2);
    } catch (error) {
      console.error('Failed to export performance data:', error);
      throw error;
    }
  };

  const getPerformanceRecommendations = (): string[] => {
    try {
      const recommendations = performanceConfig.getPerformanceRecommendations();
      
      // Add dynamic recommendations based on current state
      if (memoryStats && memoryStats.memoryUsagePercentage > 0.8) {
        recommendations.push('High memory usage detected - consider clearing cache');
      }
      
      if (batteryStats && batteryStats.batteryLevel < 0.2 && !batteryStats.isCharging) {
        recommendations.push('Low battery - enable power saving mode');
      }
      
      if (powerSavingMode && powerSavingMode.level === 'none' && batteryStats?.batteryLevel && batteryStats.batteryLevel < 0.3) {
        recommendations.push('Consider enabling battery optimization');
      }

      return recommendations;
    } catch (error) {
      console.error('Failed to get performance recommendations:', error);
      return ['Unable to generate recommendations'];
    }
  };

  const contextValue: PerformanceContextType = {
    // Performance data
    metrics,
    memoryStats,
    batteryStats,
    powerSavingMode,
    deviceCapabilities,
    currentProfile,
    
    // Performance controls
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    
    // Memory management
    forceMemoryCleanup,
    getMemoryStats,
    
    // Battery optimization
    setBatteryOptimization,
    forcePowerSavingMode,
    
    // Performance measurement
    recordScreenTransition,
    recordSearchResponse,
    measureAsync,
    
    // Configuration
    updatePerformanceProfile,
    getAdaptiveConfig,
    
    // Export and diagnostics
    exportPerformanceData,
    getPerformanceRecommendations,
  };

  return (
    <PerformanceContext.Provider value={contextValue}>
      {children}
    </PerformanceContext.Provider>
  );
};

export const usePerformance = (): PerformanceContextType => {
  const context = useContext(PerformanceContext);
  if (context === undefined) {
    throw new Error('usePerformance must be used within a PerformanceProvider');
  }
  return context;
};

export default PerformanceContext;