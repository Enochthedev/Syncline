import Voice, { SpeechRecognizedEvent, SpeechResultsEvent, SpeechErrorEvent } from '@react-native-voice/voice';
import { Platform, PermissionsAndroid } from 'react-native';
import { accessibilityService } from './accessibilityService';
import { i18nService } from './internationalizationService';

export interface VoiceCommand {
    command: string;
    action: string;
    parameters?: Record<string, any>;
    confidence: number;
}

export interface VoiceControlSettings {
    enabled: boolean;
    language: string;
    sensitivity: 'low' | 'medium' | 'high';
    continuousListening: boolean;
    wakeWord?: string;
}

class VoiceControlService {
    private isListening: boolean = false;
    private isAvailable: boolean = false;
    private settings: VoiceControlSettings = {
        enabled: false,
        language: 'en-US',
        sensitivity: 'medium',
        continuousListening: false,
    };

    private commandPatterns: Map<RegExp, (matches: string[]) => VoiceCommand> = new Map();
    private listeners: Array<(command: VoiceCommand) => void> = [];

    async initialize(): Promise<void> {
        try {
            // Check if voice recognition is available
            this.isAvailable = await Voice.isAvailable();

            if (!this.isAvailable) {
                console.warn('Voice recognition not available on this device');
                return;
            }

            // Request permissions
            await this.requestPermissions();

            // Set up voice event listeners
            this.setupVoiceListeners();

            // Register default commands
            this.registerDefaultCommands();

            // Load settings
            await this.loadSettings();
        } catch (error) {
            console.error('Failed to initialize voice control:', error);
        }
    }

    private async requestPermissions(): Promise<boolean> {
        try {
            if (Platform.OS === 'android') {
                const granted = await PermissionsAndroid.request(
                    PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
                    {
                        title: 'Microphone Permission',
                        message: 'This app needs access to your microphone for voice commands.',
                        buttonNeutral: 'Ask Me Later',
                        buttonNegative: 'Cancel',
                        buttonPositive: 'OK',
                    }
                );
                return granted === PermissionsAndroid.RESULTS.GRANTED;
            }
            return true; // iOS handles permissions automatically
        } catch (error) {
            console.error('Failed to request microphone permission:', error);
            return false;
        }
    }

    private setupVoiceListeners(): void {
        Voice.onSpeechStart = this.onSpeechStart.bind(this);
        Voice.onSpeechRecognized = this.onSpeechRecognized.bind(this);
        Voice.onSpeechEnd = this.onSpeechEnd.bind(this);
        Voice.onSpeechError = this.onSpeechError.bind(this);
        Voice.onSpeechResults = this.onSpeechResults.bind(this);
        Voice.onSpeechPartialResults = this.onSpeechPartialResults.bind(this);
    }

    private registerDefaultCommands(): void {
        // Navigation commands
        this.registerCommand(
            /^(go to|open|navigate to) (contacts?|messages?|search|settings?)$/i,
            (matches) => ({
                command: matches[0],
                action: 'navigate',
                parameters: { screen: matches[2].toLowerCase() },
                confidence: 0.9,
            })
        );

        // Search commands
        this.registerCommand(
            /^(search for|find|look for) (.+)$/i,
            (matches) => ({
                command: matches[0],
                action: 'search',
                parameters: { query: matches[2] },
                confidence: 0.8,
            })
        );

        // Contact commands
        this.registerCommand(
            /^(call|message|contact) (.+)$/i,
            (matches) => ({
                command: matches[0],
                action: 'contact',
                parameters: {
                    action: matches[1].toLowerCase(),
                    contact: matches[2]
                },
                confidence: 0.8,
            })
        );

        // App control commands
        this.registerCommand(
            /^(go back|back|return)$/i,
            (matches) => ({
                command: matches[0],
                action: 'navigation',
                parameters: { direction: 'back' },
                confidence: 0.9,
            })
        );

        this.registerCommand(
            /^(refresh|reload|update)$/i,
            (matches) => ({
                command: matches[0],
                action: 'refresh',
                parameters: {},
                confidence: 0.9,
            })
        );

        // Accessibility commands
        this.registerCommand(
            /^(read|speak|announce) (.+)$/i,
            (matches) => ({
                command: matches[0],
                action: 'announce',
                parameters: { text: matches[2] },
                confidence: 0.7,
            })
        );

        this.registerCommand(
            /^(increase|decrease) (text size|font size)$/i,
            (matches) => ({
                command: matches[0],
                action: 'adjust_text_size',
                parameters: { direction: matches[1].toLowerCase() },
                confidence: 0.8,
            })
        );
    }

    registerCommand(
        pattern: RegExp,
        handler: (matches: string[]) => VoiceCommand
    ): void {
        this.commandPatterns.set(pattern, handler);
    }

    async startListening(): Promise<void> {
        if (!this.isAvailable || !this.settings.enabled) {
            throw new Error('Voice control not available or disabled');
        }

        if (this.isListening) {
            return;
        }

        try {
            await Voice.start(this.settings.language);
            this.isListening = true;

            // Announce start of listening
            accessibilityService.announceForAccessibility({
                message: i18nService.translate('accessibility.voice.listening'),
                priority: 'medium',
            });
        } catch (error) {
            console.error('Failed to start voice recognition:', error);
            throw error;
        }
    }

    async stopListening(): Promise<void> {
        if (!this.isListening) {
            return;
        }

        try {
            await Voice.stop();
            this.isListening = false;

            // Announce stop of listening
            accessibilityService.announceForAccessibility({
                message: i18nService.translate('accessibility.voice.stopped'),
                priority: 'low',
            });
        } catch (error) {
            console.error('Failed to stop voice recognition:', error);
        }
    }

    async cancelListening(): Promise<void> {
        if (!this.isListening) {
            return;
        }

        try {
            await Voice.cancel();
            this.isListening = false;
        } catch (error) {
            console.error('Failed to cancel voice recognition:', error);
        }
    }

    private onSpeechStart(): void {
        console.log('Voice recognition started');
    }

    private onSpeechRecognized(): void {
        console.log('Speech recognized');
    }

    private onSpeechEnd(): void {
        console.log('Voice recognition ended');
        this.isListening = false;
    }

    private onSpeechError(error: SpeechErrorEvent): void {
        console.error('Voice recognition error:', error);
        this.isListening = false;

        // Announce error
        accessibilityService.announceForAccessibility({
            message: i18nService.translate('accessibility.voice.error'),
            priority: 'high',
        });
    }

    private onSpeechResults(event: SpeechResultsEvent): void {
        const results = event.value || [];

        if (results.length === 0) {
            return;
        }

        // Process the most confident result
        const bestResult = results[0];
        const command = this.parseCommand(bestResult);

        if (command) {
            this.notifyListeners(command);

            // Announce command recognition
            accessibilityService.announceForAccessibility({
                message: i18nService.translate('accessibility.voice.commandRecognized', {
                    command: command.action,
                }),
                priority: 'medium',
            });
        } else {
            // Announce unrecognized command
            accessibilityService.announceForAccessibility({
                message: i18nService.translate('accessibility.voice.commandNotRecognized'),
                priority: 'medium',
            });
        }
    }

    private onSpeechPartialResults(event: SpeechResultsEvent): void {
        // Handle partial results for real-time feedback
        const results = event.value || [];
        if (results.length > 0) {
            console.log('Partial result:', results[0]);
        }
    }

    private parseCommand(text: string): VoiceCommand | null {
        const normalizedText = text.toLowerCase().trim();

        for (const [pattern, handler] of this.commandPatterns) {
            const matches = normalizedText.match(pattern);
            if (matches) {
                try {
                    return handler(matches);
                } catch (error) {
                    console.error('Error parsing voice command:', error);
                }
            }
        }

        return null;
    }

    subscribeToCommands(callback: (command: VoiceCommand) => void): () => void {
        this.listeners.push(callback);

        return () => {
            const index = this.listeners.indexOf(callback);
            if (index > -1) {
                this.listeners.splice(index, 1);
            }
        };
    }

    private notifyListeners(command: VoiceCommand): void {
        this.listeners.forEach(listener => listener(command));
    }

    getSettings(): VoiceControlSettings {
        return { ...this.settings };
    }

    async updateSettings(updates: Partial<VoiceControlSettings>): Promise<void> {
        this.settings = { ...this.settings, ...updates };
        await this.saveSettings();
    }

    private async loadSettings(): Promise<void> {
        // Implementation would load from AsyncStorage
        // For now, use defaults
    }

    private async saveSettings(): Promise<void> {
        // Implementation would save to AsyncStorage
        // For now, just update in memory
    }

    isListeningActive(): boolean {
        return this.isListening;
    }

    isServiceAvailable(): boolean {
        return this.isAvailable;
    }

    async destroy(): Promise<void> {
        try {
            if (this.isListening) {
                await this.stopListening();
            }

            Voice.destroy();
            this.listeners = [];
        } catch (error) {
            console.error('Failed to destroy voice control service:', error);
        }
    }
}

export const voiceControlService = new VoiceControlService();