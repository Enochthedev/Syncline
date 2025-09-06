import React, { useState } from 'react'
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ScrollView,
  Dimensions,
  Alert,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { useTheme } from '@/hooks/useTheme'
import Icon from 'react-native-vector-icons/Ionicons'

const { width } = Dimensions.get('window')

interface OnboardingStep {
  id: string
  title: string
  description: string
  icon: string
  color: string
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to R.E.M.I',
    description: 'Your unified communication platform with intelligent contact-based search across all your platforms.',
    icon: 'home',
    color: '#3b82f6',
  },
  {
    id: 'search',
    title: 'Smart Contact Search',
    description: 'Find conversations and information by simply searching for people. Use natural language like "messages with John" or "files from Sarah".',
    icon: 'search',
    color: '#10b981',
  },
  {
    id: 'insights',
    title: 'AI-Powered Insights',
    description: 'Get proactive notifications about follow-ups, commitments, and relationship opportunities powered by AI.',
    icon: 'bulb',
    color: '#f59e0b',
  },
  {
    id: 'platforms',
    title: 'Connect Your Platforms',
    description: 'Unify Gmail, Slack, Discord, WhatsApp, and more into one searchable interface.',
    icon: 'link',
    color: '#8b5cf6',
  },
]

export function OnboardingScreen() {
  const navigation = useNavigation()
  const { colors } = useTheme()
  const [currentStep, setCurrentStep] = useState(0)
  const [showDemo, setShowDemo] = useState(false)

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleGetStarted()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleGetStarted = () => {
    Alert.alert(
      'Choose Your Experience',
      'How would you like to explore R.E.M.I?',
      [
        {
          text: 'Try Demo Mode',
          onPress: () => setShowDemo(true),
          style: 'default',
        },
        {
          text: 'Sign In',
          onPress: () => navigation.navigate('Login' as never),
          style: 'default',
        },
        {
          text: 'Create Account',
          onPress: () => navigation.navigate('Register' as never),
          style: 'default',
        },
        {
          text: 'Cancel',
          style: 'cancel',
        },
      ]
    )
  }

  const handleDemoMode = () => {
    Alert.alert(
      'Demo Mode',
      'Demo mode lets you explore R.E.M.I with sample data without connecting real accounts.',
      [
        {
          text: 'Continue with Demo',
          onPress: () => {
            // Navigate to main app with demo flag
            // This would be handled by the auth context
            console.log('Starting demo mode')
          },
        },
        {
          text: 'Back',
          style: 'cancel',
        },
      ]
    )
  }

  if (showDemo) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.demoContainer}>
          <Icon name="flask" size={64} color={colors.primary} />
          <Text style={[styles.demoTitle, { color: colors.text }]}>
            Demo Mode
          </Text>
          <Text style={[styles.demoDescription, { color: colors.textSecondary }]}>
            Explore R.E.M.I with sample contacts and conversations. No real data or accounts needed.
          </Text>
          
          <View style={styles.demoFeatures}>
            <View style={styles.demoFeature}>
              <Icon name="people" size={24} color={colors.primary} />
              <Text style={[styles.demoFeatureText, { color: colors.text }]}>
                Sample contacts with realistic data
              </Text>
            </View>
            <View style={styles.demoFeature}>
              <Icon name="search" size={24} color={colors.primary} />
              <Text style={[styles.demoFeatureText, { color: colors.text }]}>
                Try contact-based search features
              </Text>
            </View>
            <View style={styles.demoFeature}>
              <Icon name="chatbubbles" size={24} color={colors.primary} />
              <Text style={[styles.demoFeatureText, { color: colors.text }]}>
                Browse conversation threads
              </Text>
            </View>
            <View style={styles.demoFeature}>
              <Icon name="analytics" size={24} color={colors.primary} />
              <Text style={[styles.demoFeatureText, { color: colors.text }]}>
                View relationship insights
              </Text>
            </View>
          </View>

          <View style={styles.demoButtons}>
            <TouchableOpacity
              style={[styles.primaryButton, { backgroundColor: colors.primary }]}
              onPress={handleDemoMode}
            >
              <Text style={styles.primaryButtonText}>Start Demo</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={() => setShowDemo(false)}
            >
              <Text style={[styles.secondaryButtonText, { color: colors.primary }]}>
                Back to Options
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    )
  }

  const step = onboardingSteps[currentStep]

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Progress Indicator */}
        <View style={styles.progressContainer}>
          {onboardingSteps.map((_, index) => (
            <View
              key={index}
              style={[
                styles.progressDot,
                {
                  backgroundColor: index <= currentStep ? colors.primary : colors.border,
                },
              ]}
            />
          ))}
        </View>

        {/* Step Content */}
        <View style={styles.stepContainer}>
          <View style={[styles.iconContainer, { backgroundColor: `${step.color}20` }]}>
            <Icon name={step.icon} size={48} color={step.color} />
          </View>
          
          <Text style={[styles.stepTitle, { color: colors.text }]}>
            {step.title}
          </Text>
          
          <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
            {step.description}
          </Text>

          {/* Feature highlights for specific steps */}
          {step.id === 'search' && (
            <View style={styles.featureHighlights}>
              <View style={styles.highlight}>
                <Text style={[styles.highlightText, { color: colors.textSecondary }]}>
                  💬 "messages with John Smith"
                </Text>
              </View>
              <View style={styles.highlight}>
                <Text style={[styles.highlightText, { color: colors.textSecondary }]}>
                  📁 "files shared with Sarah"
                </Text>
              </View>
              <View style={styles.highlight}>
                <Text style={[styles.highlightText, { color: colors.textSecondary }]}>
                  ⏰ "what did I promise to Mike"
                </Text>
              </View>
            </View>
          )}

          {step.id === 'platforms' && (
            <View style={styles.platformGrid}>
              {['gmail', 'slack', 'discord', 'whatsapp'].map((platform) => (
                <View key={platform} style={[styles.platformCard, { backgroundColor: colors.surface }]}>
                  <Text style={[styles.platformName, { color: colors.text }]}>
                    {platform.charAt(0).toUpperCase() + platform.slice(1)}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>
      </ScrollView>

      {/* Navigation Buttons */}
      <View style={styles.navigationContainer}>
        <View style={styles.navigationButtons}>
          {currentStep > 0 && (
            <TouchableOpacity
              style={[styles.navButton, { backgroundColor: colors.surface }]}
              onPress={handlePrevious}
            >
              <Icon name="chevron-back" size={20} color={colors.text} />
              <Text style={[styles.navButtonText, { color: colors.text }]}>
                Previous
              </Text>
            </TouchableOpacity>
          )}
          
          <TouchableOpacity
            style={[
              styles.navButton,
              styles.primaryNavButton,
              { backgroundColor: colors.primary },
              currentStep === 0 && styles.fullWidthButton,
            ]}
            onPress={handleNext}
          >
            <Text style={styles.primaryNavButtonText}>
              {currentStep === onboardingSteps.length - 1 ? 'Get Started' : 'Next'}
            </Text>
            {currentStep < onboardingSteps.length - 1 && (
              <Icon name="chevron-forward" size={20} color="white" />
            )}
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={styles.skipButton}
          onPress={handleGetStarted}
        >
          <Text style={[styles.skipButtonText, { color: colors.textSecondary }]}>
            Skip Introduction
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 40,
  },
  progressDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginHorizontal: 4,
  },
  stepContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  iconContainer: {
    width: 96,
    height: 96,
    borderRadius: 48,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 32,
  },
  stepTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 16,
  },
  stepDescription: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  featureHighlights: {
    width: '100%',
    marginBottom: 20,
  },
  highlight: {
    padding: 12,
    marginBottom: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
  },
  highlightText: {
    fontSize: 14,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  platformGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
    marginBottom: 20,
  },
  platformCard: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    minWidth: 80,
    alignItems: 'center',
  },
  platformName: {
    fontSize: 12,
    fontWeight: '600',
  },
  navigationContainer: {
    padding: 20,
    paddingTop: 10,
  },
  navigationButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  navButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    minWidth: 100,
    justifyContent: 'center',
  },
  primaryNavButton: {
    flex: 1,
    marginLeft: 12,
  },
  fullWidthButton: {
    marginLeft: 0,
  },
  navButtonText: {
    fontSize: 16,
    fontWeight: '600',
    marginRight: 4,
  },
  primaryNavButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginRight: 4,
  },
  skipButton: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  skipButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  // Demo mode styles
  demoContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  demoTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 20,
    marginBottom: 16,
  },
  demoDescription: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  demoFeatures: {
    width: '100%',
    marginBottom: 32,
  },
  demoFeature: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  demoFeatureText: {
    fontSize: 16,
    marginLeft: 12,
    flex: 1,
  },
  demoButtons: {
    width: '100%',
  },
  primaryButton: {
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    padding: 16,
    alignItems: 'center',
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
})