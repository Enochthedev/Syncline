/**
 * Comprehensive Onboarding Flow Screen
 * Guides users through platform connections and feature introduction
 */

import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  Alert
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import Icon from 'react-native-vector-icons/Ionicons'
import { useTheme } from '@/hooks/useTheme'
import { useAuth } from '@/hooks/useAuth'
import { unifiedBusinessLogic, OnboardingFlowState, PlatformConnection } from '@/services/unifiedBusinessLogic'
import { OAuthFlowModal } from '@/components/OAuthFlowModal'
import { PlatformConnectionCard } from '@/components/PlatformConnectionCard'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorMessage } from '@/components/ErrorMessage'

const { width: screenWidth } = Dimensions.get('window')

interface OnboardingStep {
  id: string
  title: string
  description: string
  icon: string
  component: React.ComponentType<any>
}

export function OnboardingFlowScreen() {
  const navigation = useNavigation()
  const { colors } = useTheme()
  const { user } = useAuth()
  
  const [onboardingState, setOnboardingState] = useState<OnboardingFlowState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [slideAnim] = useState(new Animated.Value(0))

  const onboardingSteps: OnboardingStep[] = [
    {
      id: 'welcome',
      title: 'Welcome to R.E.M.I',
      description: 'Your unified communication hub with intelligent contact-based search',
      icon: 'home',
      component: WelcomeStep
    },
    {
      id: 'permissions',
      title: 'Permissions Setup',
      description: 'Grant necessary permissions for optimal functionality',
      icon: 'shield-checkmark',
      component: PermissionsStep
    },
    {
      id: 'platform-connections',
      title: 'Connect Platforms',
      description: 'Connect your communication platforms to unify your messages',
      icon: 'link',
      component: PlatformConnectionsStep
    },
    {
      id: 'preferences',
      title: 'Customize Preferences',
      description: 'Set up notifications, privacy, and sync preferences',
      icon: 'settings',
      component: PreferencesStep
    },
    {
      id: 'demo',
      title: 'Try the Demo',
      description: 'Experience the power of contact-based search',
      icon: 'play-circle',
      component: DemoStep
    },
    {
      id: 'complete',
      title: 'All Set!',
      description: 'You\'re ready to start using R.E.M.I',
      icon: 'checkmark-circle',
      component: CompleteStep
    }
  ]

  useEffect(() => {
    initializeOnboarding()
  }, [])

  useEffect(() => {
    if (onboardingState) {
      animateToStep(onboardingState.currentStep)
    }
  }, [onboardingState?.currentStep])

  const initializeOnboarding = async () => {
    try {
      setLoading(true)
      const state = await unifiedBusinessLogic.initializeOnboardingFlow()
      setOnboardingState(state)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize onboarding')
    } finally {
      setLoading(false)
    }
  }

  const animateToStep = (stepIndex: number) => {
    Animated.timing(slideAnim, {
      toValue: -stepIndex * screenWidth,
      duration: 300,
      useNativeDriver: true,
    }).start()
  }

  const handleNextStep = async (stepId: string, data?: any) => {
    try {
      setLoading(true)
      const newState = await unifiedBusinessLogic.progressOnboardingStep(stepId, data)
      setOnboardingState(newState)
      
      // If onboarding is complete, navigate to main app
      if (newState.currentStep >= onboardingSteps.length - 1) {
        navigation.navigate('Main' as never)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to progress onboarding')
    } finally {
      setLoading(false)
    }
  }

  const handlePreviousStep = () => {
    if (onboardingState && onboardingState.currentStep > 0) {
      setOnboardingState({
        ...onboardingState,
        currentStep: onboardingState.currentStep - 1
      })
    }
  }

  const handleSkipOnboarding = () => {
    Alert.alert(
      'Skip Onboarding',
      'Are you sure you want to skip the setup? You can always configure these settings later.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Skip', 
          style: 'destructive',
          onPress: () => navigation.navigate('Main' as never)
        }
      ]
    )
  }

  if (loading && !onboardingState) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: colors.background }]}>
        <LoadingSpinner size="large" />
        <Text style={[styles.loadingText, { color: colors.text }]}>
          Initializing onboarding...
        </Text>
      </View>
    )
  }

  if (error) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: colors.background }]}>
        <ErrorMessage 
          message={error}
          onRetry={initializeOnboarding}
        />
      </View>
    )
  }

  if (!onboardingState) {
    return null
  }

  const currentStep = onboardingSteps[onboardingState.currentStep]
  const CurrentStepComponent = currentStep.component

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <View style={styles.headerContent}>
          <TouchableOpacity 
            onPress={handleSkipOnboarding}
            style={styles.skipButton}
          >
            <Text style={[styles.skipText, { color: colors.textSecondary }]}>
              Skip
            </Text>
          </TouchableOpacity>
          
          <View style={styles.progressContainer}>
            <Text style={[styles.progressText, { color: colors.text }]}>
              {onboardingState.currentStep + 1} of {onboardingState.totalSteps}
            </Text>
            <View style={[styles.progressBar, { backgroundColor: colors.border }]}>
              <View 
                style={[
                  styles.progressFill, 
                  { 
                    backgroundColor: colors.primary,
                    width: `${((onboardingState.currentStep + 1) / onboardingState.totalSteps) * 100}%`
                  }
                ]} 
              />
            </View>
          </View>
        </View>
      </View>

      {/* Content */}
      <View style={styles.content}>
        <Animated.View 
          style={[
            styles.stepsContainer,
            { transform: [{ translateX: slideAnim }] }
          ]}
        >
          {onboardingSteps.map((step, index) => (
            <View key={step.id} style={styles.stepContainer}>
              <CurrentStepComponent
                step={step}
                onboardingState={onboardingState}
                onNext={(data?: any) => handleNextStep(step.id, data)}
                onPrevious={handlePreviousStep}
                loading={loading}
                colors={colors}
              />
            </View>
          ))}
        </Animated.View>
      </View>

      {/* Navigation */}
      <View style={[styles.navigation, { backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={handlePreviousStep}
          disabled={onboardingState.currentStep === 0}
          style={[
            styles.navButton,
            { 
              backgroundColor: onboardingState.currentStep === 0 ? colors.border : colors.primary,
              opacity: onboardingState.currentStep === 0 ? 0.5 : 1
            }
          ]}
        >
          <Icon name="chevron-back" size={20} color={colors.surface} />
          <Text style={[styles.navButtonText, { color: colors.surface }]}>
            Previous
          </Text>
        </TouchableOpacity>

        <View style={styles.stepIndicators}>
          {onboardingSteps.map((_, index) => (
            <View
              key={index}
              style={[
                styles.stepIndicator,
                {
                  backgroundColor: index <= onboardingState.currentStep 
                    ? colors.primary 
                    : colors.border
                }
              ]}
            />
          ))}
        </View>

        <TouchableOpacity
          onPress={() => handleNextStep(currentStep.id)}
          disabled={loading}
          style={[styles.navButton, { backgroundColor: colors.primary }]}
        >
          <Text style={[styles.navButtonText, { color: colors.surface }]}>
            {onboardingState.currentStep === onboardingSteps.length - 1 ? 'Finish' : 'Next'}
          </Text>
          <Icon name="chevron-forward" size={20} color={colors.surface} />
        </TouchableOpacity>
      </View>
    </View>
  )
}

// Individual step components

function WelcomeStep({ step, onNext, colors }: any) {
  return (
    <View style={styles.stepContent}>
      <View style={styles.stepIcon}>
        <Icon name={step.icon} size={80} color={colors.primary} />
      </View>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        {step.title}
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        {step.description}
      </Text>
      
      <View style={styles.featureList}>
        <FeatureItem 
          icon="search" 
          title="Contact-Based Search" 
          description="Find conversations by person instantly"
          colors={colors}
        />
        <FeatureItem 
          icon="sync" 
          title="Real-Time Sync" 
          description="Stay updated across all devices"
          colors={colors}
        />
        <FeatureItem 
          icon="bulb" 
          title="AI Insights" 
          description="Get proactive reminders and insights"
          colors={colors}
        />
      </View>
    </View>
  )
}

function PermissionsStep({ step, onNext, colors }: any) {
  const [permissions, setPermissions] = useState({
    notifications: false,
    contacts: false,
    storage: false
  })

  const requestPermissions = async () => {
    // Implementation would request actual permissions
    setPermissions({
      notifications: true,
      contacts: true,
      storage: true
    })
    onNext({ permissions })
  }

  return (
    <View style={styles.stepContent}>
      <View style={styles.stepIcon}>
        <Icon name={step.icon} size={80} color={colors.primary} />
      </View>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        {step.title}
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        {step.description}
      </Text>

      <View style={styles.permissionsList}>
        <PermissionItem
          icon="notifications"
          title="Notifications"
          description="Receive proactive insights and reminders"
          granted={permissions.notifications}
          colors={colors}
        />
        <PermissionItem
          icon="people"
          title="Contacts"
          description="Access contacts for better search results"
          granted={permissions.contacts}
          colors={colors}
        />
        <PermissionItem
          icon="folder"
          title="Storage"
          description="Store data locally for offline access"
          granted={permissions.storage}
          colors={colors}
        />
      </View>

      <TouchableOpacity
        onPress={requestPermissions}
        style={[styles.primaryButton, { backgroundColor: colors.primary }]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.surface }]}>
          Grant Permissions
        </Text>
      </TouchableOpacity>
    </View>
  )
}

function PlatformConnectionsStep({ step, onNext, onboardingState, colors }: any) {
  const [connections, setConnections] = useState<PlatformConnection[]>(
    onboardingState?.platformConnections || []
  )
  const [showOAuthModal, setShowOAuthModal] = useState(false)
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)

  const availablePlatforms = [
    { id: 'gmail', name: 'Gmail', icon: 'mail', color: '#EA4335' },
    { id: 'slack', name: 'Slack', icon: 'chatbubbles', color: '#4A154B' },
    { id: 'discord', name: 'Discord', icon: 'game-controller', color: '#5865F2' },
    { id: 'whatsapp', name: 'WhatsApp', icon: 'logo-whatsapp', color: '#25D366' }
  ]

  const handleConnectPlatform = (platformId: string) => {
    setSelectedPlatform(platformId)
    setShowOAuthModal(true)
  }

  const handleConnectionComplete = async (credentials: any) => {
    if (!selectedPlatform) return

    try {
      const connection = await unifiedBusinessLogic.connectPlatform(selectedPlatform, credentials)
      setConnections(prev => [...prev.filter(c => c.platform !== selectedPlatform), connection])
      setShowOAuthModal(false)
      setSelectedPlatform(null)
    } catch (error) {
      console.error('Failed to connect platform:', error)
    }
  }

  const handleContinue = () => {
    onNext({ connections })
  }

  return (
    <View style={styles.stepContent}>
      <View style={styles.stepIcon}>
        <Icon name={step.icon} size={80} color={colors.primary} />
      </View>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        {step.title}
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        {step.description}
      </Text>

      <ScrollView style={styles.platformsList}>
        {availablePlatforms.map(platform => {
          const connection = connections.find(c => c.platform === platform.id)
          return (
            <PlatformConnectionCard
              key={platform.id}
              platform={platform}
              connection={connection}
              onConnect={() => handleConnectPlatform(platform.id)}
              colors={colors}
            />
          )
        })}
      </ScrollView>

      <TouchableOpacity
        onPress={handleContinue}
        style={[styles.primaryButton, { backgroundColor: colors.primary }]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.surface }]}>
          Continue
        </Text>
      </TouchableOpacity>

      <OAuthFlowModal
        visible={showOAuthModal}
        platform={selectedPlatform}
        onComplete={handleConnectionComplete}
        onCancel={() => {
          setShowOAuthModal(false)
          setSelectedPlatform(null)
        }}
      />
    </View>
  )
}

function PreferencesStep({ step, onNext, onboardingState, colors }: any) {
  const [preferences, setPreferences] = useState(onboardingState?.userPreferences || {})

  const handleSavePreferences = () => {
    onNext({ preferences })
  }

  return (
    <View style={styles.stepContent}>
      <View style={styles.stepIcon}>
        <Icon name={step.icon} size={80} color={colors.primary} />
      </View>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        {step.title}
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        {step.description}
      </Text>

      <ScrollView style={styles.preferencesList}>
        {/* Notification preferences */}
        <PreferenceSection
          title="Notifications"
          icon="notifications"
          preferences={preferences.notifications}
          onUpdate={(notifications) => setPreferences(prev => ({ ...prev, notifications }))}
          colors={colors}
        />

        {/* Privacy preferences */}
        <PreferenceSection
          title="Privacy"
          icon="shield"
          preferences={preferences.privacy}
          onUpdate={(privacy) => setPreferences(prev => ({ ...prev, privacy }))}
          colors={colors}
        />

        {/* Sync preferences */}
        <PreferenceSection
          title="Sync"
          icon="sync"
          preferences={preferences.sync}
          onUpdate={(sync) => setPreferences(prev => ({ ...prev, sync }))}
          colors={colors}
        />
      </ScrollView>

      <TouchableOpacity
        onPress={handleSavePreferences}
        style={[styles.primaryButton, { backgroundColor: colors.primary }]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.surface }]}>
          Save Preferences
        </Text>
      </TouchableOpacity>
    </View>
  )
}

function DemoStep({ step, onNext, colors }: any) {
  const navigation = useNavigation()

  const handleTryDemo = () => {
    navigation.navigate('DemoWorkflow' as never)
  }

  const handleSkipDemo = () => {
    onNext()
  }

  return (
    <View style={styles.stepContent}>
      <View style={styles.stepIcon}>
        <Icon name={step.icon} size={80} color={colors.primary} />
      </View>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        {step.title}
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        {step.description}
      </Text>

      <View style={styles.demoActions}>
        <TouchableOpacity
          onPress={handleTryDemo}
          style={[styles.primaryButton, { backgroundColor: colors.primary }]}
        >
          <Text style={[styles.primaryButtonText, { color: colors.surface }]}>
            Try Demo
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={handleSkipDemo}
          style={[styles.secondaryButton, { borderColor: colors.border }]}
        >
          <Text style={[styles.secondaryButtonText, { color: colors.text }]}>
            Skip Demo
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  )
}

function CompleteStep({ step, onNext, colors }: any) {
  const navigation = useNavigation()

  const handleGetStarted = () => {
    navigation.navigate('Main' as never)
  }

  return (
    <View style={styles.stepContent}>
      <View style={styles.stepIcon}>
        <Icon name={step.icon} size={80} color={colors.success || colors.primary} />
      </View>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        {step.title}
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        {step.description}
      </Text>

      <View style={styles.completionSummary}>
        <Text style={[styles.summaryTitle, { color: colors.text }]}>
          What's Next?
        </Text>
        <Text style={[styles.summaryText, { color: colors.textSecondary }]}>
          • Start searching for contacts and messages{'\n'}
          • Explore AI-powered insights{'\n'}
          • Connect more platforms anytime{'\n'}
          • Customize your experience in settings
        </Text>
      </View>

      <TouchableOpacity
        onPress={handleGetStarted}
        style={[styles.primaryButton, { backgroundColor: colors.primary }]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.surface }]}>
          Get Started
        </Text>
      </TouchableOpacity>
    </View>
  )
}

// Helper components

function FeatureItem({ icon, title, description, colors }: any) {
  return (
    <View style={styles.featureItem}>
      <Icon name={icon} size={24} color={colors.primary} />
      <View style={styles.featureContent}>
        <Text style={[styles.featureTitle, { color: colors.text }]}>
          {title}
        </Text>
        <Text style={[styles.featureDescription, { color: colors.textSecondary }]}>
          {description}
        </Text>
      </View>
    </View>
  )
}

function PermissionItem({ icon, title, description, granted, colors }: any) {
  return (
    <View style={styles.permissionItem}>
      <Icon name={icon} size={24} color={colors.primary} />
      <View style={styles.permissionContent}>
        <Text style={[styles.permissionTitle, { color: colors.text }]}>
          {title}
        </Text>
        <Text style={[styles.permissionDescription, { color: colors.textSecondary }]}>
          {description}
        </Text>
      </View>
      <Icon 
        name={granted ? "checkmark-circle" : "ellipse-outline"} 
        size={24} 
        color={granted ? colors.success || colors.primary : colors.border} 
      />
    </View>
  )
}

function PreferenceSection({ title, icon, preferences, onUpdate, colors }: any) {
  return (
    <View style={styles.preferenceSection}>
      <View style={styles.preferenceSectionHeader}>
        <Icon name={icon} size={20} color={colors.primary} />
        <Text style={[styles.preferenceSectionTitle, { color: colors.text }]}>
          {title}
        </Text>
      </View>
      {/* Preference controls would go here */}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  skipButton: {
    padding: 8,
  },
  skipText: {
    fontSize: 16,
  },
  progressContainer: {
    flex: 1,
    alignItems: 'center',
    marginLeft: 20,
  },
  progressText: {
    fontSize: 14,
    marginBottom: 8,
  },
  progressBar: {
    width: '100%',
    height: 4,
    borderRadius: 2,
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
  },
  content: {
    flex: 1,
  },
  stepsContainer: {
    flexDirection: 'row',
    width: screenWidth * 6, // 6 steps
  },
  stepContainer: {
    width: screenWidth,
  },
  stepContent: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
  },
  stepIcon: {
    marginBottom: 20,
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 12,
  },
  stepDescription: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 32,
    lineHeight: 24,
  },
  featureList: {
    width: '100%',
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  featureContent: {
    marginLeft: 16,
    flex: 1,
  },
  featureTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  featureDescription: {
    fontSize: 14,
  },
  permissionsList: {
    width: '100%',
    marginBottom: 32,
  },
  permissionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    paddingVertical: 12,
  },
  permissionContent: {
    marginLeft: 16,
    flex: 1,
  },
  permissionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  permissionDescription: {
    fontSize: 14,
  },
  platformsList: {
    width: '100%',
    maxHeight: 300,
    marginBottom: 32,
  },
  preferencesList: {
    width: '100%',
    maxHeight: 300,
    marginBottom: 32,
  },
  preferenceSection: {
    marginBottom: 24,
  },
  preferenceSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  preferenceSectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  demoActions: {
    width: '100%',
    gap: 16,
  },
  completionSummary: {
    width: '100%',
    marginBottom: 32,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  summaryText: {
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    width: '100%',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    width: '100%',
    paddingVertical: 16,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  navigation: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
  },
  navButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    gap: 8,
  },
  navButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  stepIndicators: {
    flexDirection: 'row',
    gap: 8,
  },
  stepIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
})

export default OnboardingFlowScreen