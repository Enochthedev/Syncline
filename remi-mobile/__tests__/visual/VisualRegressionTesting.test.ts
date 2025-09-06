/**
 * Visual Regression Testing with Screenshot Comparison
 * Automated UI testing for React Native components
 */

import { render, screen } from '@testing-library/react-native';
import { VisualTester } from '@/utils/VisualTester';
import { ScreenshotComparator } from '@/utils/ScreenshotComparator';
import { ContactSearchInput } from '@/components/ContactSearchInput';
import { ContactProfile } from '@/components/ContactProfile';
import { MessageThread } from '@/components/MessageThread';
import { ContactSearchResults } from '@/components/ContactSearchResults';

// Mock react-native-screenshot-tests
jest.mock('react-native-screenshot-tests', () => ({
    captureScreen: jest.fn(() => Promise.resolve('mock-screenshot-path')),
    compareScreenshots: jest.fn(() => Promise.resolve({
        passed: true,
        difference: 0.001,
        diffImage: null
    })),
}));

// Mock image comparison utilities
const mockImageComparison = {
    compare: jest.fn(),
    generateDiffImage: jest.fn(),
    calculateSimilarity: jest.fn(),
};

jest.mock('pixelmatch', () => mockImageComparison.compare);

describe('Visual Regression Testing', () => {
    let visualTester: VisualTester;
    let screenshotComparator: ScreenshotComparator;

    beforeEach(() => {
        jest.clearAllMocks();

        visualTester = new VisualTester({
            threshold: 0.1, // 10% difference threshold
            includeAA: false, // Ignore anti-aliasing
            diffColor: [255, 0, 0], // Red for differences
        });

        screenshotComparator = new ScreenshotComparator({
            baselineDir: '__tests__/visual/baselines',
            outputDir: '__tests__/visual/output',
            diffDir: '__tests__/visual/diffs',
        });
    });

    describe('Component Visual Testing', () => {
        it('should match ContactSearchInput visual baseline', async () => {
            const mockProps = {
                value: '',
                onChangeText: jest.fn(),
                onSubmit: jest.fn(),
                placeholder: 'Search contacts...',
                loading: false,
            };

            const { toJSON } = render(<ContactSearchInput { ...mockProps } />);

            // Capture component screenshot
            const screenshot = await visualTester.captureComponent(
                'ContactSearchInput_default',
                <ContactSearchInput { ...mockProps } />
      );

            // Compare with baseline
            const comparison = await screenshotComparator.compare(
                'ContactSearchInput_default',
                screenshot
            );

            expect(comparison.passed).toBe(true);
            expect(comparison.difference).toBeLessThan(0.1);

            // Verify component structure hasn't changed
            expect(toJSON()).toMatchSnapshot();
        });

        it('should detect visual changes in ContactSearchInput states', async () => {
            const states = [
                { name: 'empty', props: { value: '', loading: false } },
                { name: 'typing', props: { value: 'John', loading: false } },
                { name: 'loading', props: { value: 'John', loading: true } },
                { name: 'error', props: { value: 'John', error: 'Search failed' } },
            ];

            for (const state of states) {
                const mockProps = {
                    onChangeText: jest.fn(),
                    onSubmit: jest.fn(),
                    placeholder: 'Search contacts...',
                    ...state.props,
                };

                const screenshot = await visualTester.captureComponent(
                    `ContactSearchInput_${state.name}`,
                    <ContactSearchInput { ...mockProps } />
        );

                const comparison = await screenshotComparator.compare(
                    `ContactSearchInput_${state.name}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.1);
            }
        });

        it('should match ContactProfile visual baseline', async () => {
            const mockContact = global.testUtils.createMockContact({
                name: 'John Doe',
                email: 'john@example.com',
                platforms: ['email', 'slack'],
                profilePhoto: 'https://example.com/photo.jpg',
            });

            const mockProps = {
                contact: mockContact,
                onMessagePress: jest.fn(),
                onCallPress: jest.fn(),
                onEditPress: jest.fn(),
            };

            const screenshot = await visualTester.captureComponent(
                'ContactProfile_default',
                <ContactProfile { ...mockProps } />
      );

            const comparison = await screenshotComparator.compare(
                'ContactProfile_default',
                screenshot
            );

            expect(comparison.passed).toBe(true);
            expect(comparison.difference).toBeLessThan(0.1);
        });

        it('should test ContactProfile responsive layouts', async () => {
            const mockContact = global.testUtils.createMockContact();

            const viewports = [
                { name: 'phone', width: 375, height: 812 },
                { name: 'tablet', width: 768, height: 1024 },
                { name: 'large_tablet', width: 1024, height: 1366 },
            ];

            for (const viewport of viewports) {
                // Set viewport dimensions
                visualTester.setViewport(viewport.width, viewport.height);

                const screenshot = await visualTester.captureComponent(
                    `ContactProfile_${viewport.name}`,
                    <ContactProfile 
            contact={ mockContact }
            onMessagePress = { jest.fn() }
            onCallPress = { jest.fn() }
            onEditPress = { jest.fn() }
                    />
        );

                const comparison = await screenshotComparator.compare(
                    `ContactProfile_${viewport.name}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.15); // Slightly higher threshold for responsive layouts
            }
        });

        it('should test MessageThread visual consistency', async () => {
            const mockMessages = Array.from({ length: 5 }, (_, i) =>
                global.testUtils.createMockMessage({
                    id: `message-${i}`,
                    content: `Test message ${i + 1}`,
                    sender: i % 2 === 0 ? 'John Doe' : 'Jane Smith',
                    timestamp: new Date(Date.now() - i * 3600000).toISOString(),
                })
            );

            const mockProps = {
                messages: mockMessages,
                onMessagePress: jest.fn(),
                onLoadMore: jest.fn(),
                loading: false,
            };

            const screenshot = await visualTester.captureComponent(
                'MessageThread_default',
                <MessageThread { ...mockProps } />
      );

            const comparison = await screenshotComparator.compare(
                'MessageThread_default',
                screenshot
            );

            expect(comparison.passed).toBe(true);
            expect(comparison.difference).toBeLessThan(0.1);
        });

        it('should test ContactSearchResults grid layout', async () => {
            const mockContacts = Array.from({ length: 10 }, (_, i) =>
                global.testUtils.createMockContact({
                    id: `contact-${i}`,
                    name: `Contact ${i + 1}`,
                    email: `contact${i + 1}@example.com`,
                })
            );

            const mockProps = {
                contacts: mockContacts,
                onContactPress: jest.fn(),
                loading: false,
                hasMore: true,
                onLoadMore: jest.fn(),
            };

            const screenshot = await visualTester.captureComponent(
                'ContactSearchResults_grid',
                <ContactSearchResults { ...mockProps } />
      );

            const comparison = await screenshotComparator.compare(
                'ContactSearchResults_grid',
                screenshot
            );

            expect(comparison.passed).toBe(true);
            expect(comparison.difference).toBeLessThan(0.1);
        });
    });

    describe('Theme and Styling Testing', () => {
        it('should test dark theme consistency', async () => {
            const components = [
                { name: 'ContactSearchInput', component: ContactSearchInput },
                { name: 'ContactProfile', component: ContactProfile },
                { name: 'MessageThread', component: MessageThread },
            ];

            // Set dark theme
            visualTester.setTheme('dark');

            for (const { name, component: Component } of components) {
                const mockProps = getMockPropsForComponent(name);

                const screenshot = await visualTester.captureComponent(
                    `${name}_dark_theme`,
                    <Component { ...mockProps } />
        );

                const comparison = await screenshotComparator.compare(
                    `${name}_dark_theme`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.1);
            }
        });

        it('should test high contrast theme', async () => {
            visualTester.setTheme('high-contrast');

            const mockContact = global.testUtils.createMockContact();

            const screenshot = await visualTester.captureComponent(
                'ContactProfile_high_contrast',
                <ContactProfile 
          contact={ mockContact }
          onMessagePress = { jest.fn() }
          onCallPress = { jest.fn() }
          onEditPress = { jest.fn() }
                />
      );

            const comparison = await screenshotComparator.compare(
                'ContactProfile_high_contrast',
                screenshot
            );

            expect(comparison.passed).toBe(true);
            expect(comparison.difference).toBeLessThan(0.1);
        });

        it('should test font scaling', async () => {
            const fontScales = [0.85, 1.0, 1.15, 1.3];

            for (const scale of fontScales) {
                visualTester.setFontScale(scale);

                const mockContact = global.testUtils.createMockContact({
                    name: 'John Doe with a very long name that might wrap',
                });

                const screenshot = await visualTester.captureComponent(
                    `ContactProfile_font_scale_${scale}`,
                    <ContactProfile 
            contact={ mockContact }
            onMessagePress = { jest.fn() }
            onCallPress = { jest.fn() }
            onEditPress = { jest.fn() }
                    />
        );

                const comparison = await screenshotComparator.compare(
                    `ContactProfile_font_scale_${scale}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.15); // Higher threshold for font scaling
            }
        });
    });

    describe('Animation and Interaction Testing', () => {
        it('should test loading state animations', async () => {
            const animationFrames = [];

            // Capture animation frames
            for (let frame = 0; frame < 10; frame++) {
                visualTester.setAnimationFrame(frame * 100); // 100ms intervals

                const screenshot = await visualTester.captureComponent(
                    `ContactSearchInput_loading_frame_${frame}`,
                    <ContactSearchInput 
            value="Searching..."
            loading = { true}
            onChangeText = { jest.fn() }
            onSubmit = { jest.fn() }
                    />
        );

                animationFrames.push(screenshot);
            }

            // Verify animation consistency
            const animationAnalysis = await visualTester.analyzeAnimation(animationFrames);

            expect(animationAnalysis.isSmooth).toBe(true);
            expect(animationAnalysis.frameDrops).toBe(0);
            expect(animationAnalysis.averageFrameTime).toBeLessThan(16.67); // 60fps
        });

        it('should test touch state visual feedback', async () => {
            const touchStates = ['normal', 'pressed', 'disabled'];

            for (const state of touchStates) {
                const mockProps = {
                    contact: global.testUtils.createMockContact(),
                    onPress: jest.fn(),
                    disabled: state === 'disabled',
                    pressed: state === 'pressed',
                };

                const screenshot = await visualTester.captureComponent(
                    `ContactCard_${state}`,
                    <ContactCard { ...mockProps } />
        );

                const comparison = await screenshotComparator.compare(
                    `ContactCard_${state}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.1);
            }
        });
    });

    describe('Cross-Platform Visual Consistency', () => {
        it('should maintain consistency across iOS and Android', async () => {
            const platforms = ['ios', 'android'];

            for (const platform of platforms) {
                visualTester.setPlatform(platform);

                const mockContact = global.testUtils.createMockContact();

                const screenshot = await visualTester.captureComponent(
                    `ContactProfile_${platform}`,
                    <ContactProfile 
            contact={ mockContact }
            onMessagePress = { jest.fn() }
            onCallPress = { jest.fn() }
            onEditPress = { jest.fn() }
                    />
        );

                const comparison = await screenshotComparator.compare(
                    `ContactProfile_${platform}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.2); // Higher threshold for cross-platform
            }
        });

        it('should test platform-specific components', async () => {
            // Test iOS-specific styling
            visualTester.setPlatform('ios');

            const iosScreenshot = await visualTester.captureComponent(
                'SearchBar_ios',
                <SearchBar 
          placeholder="Search"
          value = ""
          onChangeText = { jest.fn() }
                />
      );

            // Test Android-specific styling
            visualTester.setPlatform('android');

            const androidScreenshot = await visualTester.captureComponent(
                'SearchBar_android',
                <SearchBar 
          placeholder="Search"
          value = ""
          onChangeText = { jest.fn() }
                />
      );

            // Both should pass their respective baselines
            const iosComparison = await screenshotComparator.compare('SearchBar_ios', iosScreenshot);
            const androidComparison = await screenshotComparator.compare('SearchBar_android', androidScreenshot);

            expect(iosComparison.passed).toBe(true);
            expect(androidComparison.passed).toBe(true);
        });
    });

    describe('Error State Visual Testing', () => {
        it('should test error message display', async () => {
            const errorStates = [
                { type: 'network', message: 'Network connection failed' },
                { type: 'validation', message: 'Please enter a valid search term' },
                { type: 'server', message: 'Server error occurred' },
                { type: 'timeout', message: 'Request timed out' },
            ];

            for (const error of errorStates) {
                const screenshot = await visualTester.captureComponent(
                    `ErrorMessage_${error.type}`,
                    <ErrorMessage 
            type={ error.type }
            message = { error.message }
            onRetry = { jest.fn() }
                    />
        );

                const comparison = await screenshotComparator.compare(
                    `ErrorMessage_${error.type}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.1);
            }
        });

        it('should test empty state visuals', async () => {
            const emptyStates = [
                { type: 'no_contacts', title: 'No contacts found' },
                { type: 'no_messages', title: 'No messages yet' },
                { type: 'no_search_results', title: 'No search results' },
            ];

            for (const state of emptyStates) {
                const screenshot = await visualTester.captureComponent(
                    `EmptyState_${state.type}`,
                    <EmptyState 
            type={ state.type }
            title = { state.title }
            onAction = { jest.fn() }
                    />
        );

                const comparison = await screenshotComparator.compare(
                    `EmptyState_${state.type}`,
                    screenshot
                );

                expect(comparison.passed).toBe(true);
                expect(comparison.difference).toBeLessThan(0.1);
            }
        });
    });

    describe('Visual Regression Detection', () => {
        it('should detect unintended visual changes', async () => {
            // Simulate a component with a visual regression
            const ComponentWithRegression = () => (
                <ContactProfile 
          contact= { global.testUtils.createMockContact() }
            onMessagePress = { jest.fn() }
            onCallPress = { jest.fn() }
            onEditPress = { jest.fn() }
            // Simulate regression: wrong color
            style = {{ backgroundColor: '#ff0000' }
        }
        />
        );

        const screenshot = await visualTester.captureComponent(
            'ContactProfile_regression_test',
            <ComponentWithRegression />
        );

        // Mock comparison to show difference
        mockImageComparison.compare.mockReturnValue(1500); // High difference

        const comparison = await screenshotComparator.compare(
            'ContactProfile_default', // Compare against original baseline
            screenshot
        );

        expect(comparison.passed).toBe(false);
        expect(comparison.difference).toBeGreaterThan(0.1);
        expect(comparison.diffImage).toBeDefined();
    });

    it('should generate detailed diff reports', async () => {
        const screenshot = await visualTester.captureComponent(
            'test_component',
            <ContactSearchInput value="test" onChangeText = { jest.fn() } onSubmit = { jest.fn() } />
      );

        // Mock a comparison with differences
        mockImageComparison.compare.mockReturnValue(500);
        mockImageComparison.generateDiffImage.mockReturnValue('diff-image-path');

        const comparison = await screenshotComparator.compare('test_component', screenshot);
        const diffReport = await screenshotComparator.generateDiffReport(comparison);

        expect(diffReport).toEqual({
            testName: 'test_component',
            passed: false,
            difference: expect.any(Number),
            diffImage: 'diff-image-path',
            baseline: expect.any(String),
            actual: expect.any(String),
            metadata: {
                timestamp: expect.any(String),
                platform: expect.any(String),
                viewport: expect.any(Object),
                theme: expect.any(String),
            },
        });
    });

    it('should update baselines when approved', async () => {
        const screenshot = await visualTester.captureComponent(
            'new_component',
            <ContactSearchInput value="new" onChangeText = { jest.fn() } onSubmit = { jest.fn() } />
      );

        // First comparison should fail (no baseline)
        const initialComparison = await screenshotComparator.compare('new_component', screenshot);
        expect(initialComparison.passed).toBe(false);

        // Approve new baseline
        await screenshotComparator.approveBaseline('new_component', screenshot);

        // Second comparison should pass
        const updatedComparison = await screenshotComparator.compare('new_component', screenshot);
        expect(updatedComparison.passed).toBe(true);
    });
});
});

// Helper function to get mock props for different components
function getMockPropsForComponent(componentName: string) {
    switch (componentName) {
        case 'ContactSearchInput':
            return {
                value: '',
                onChangeText: jest.fn(),
                onSubmit: jest.fn(),
                placeholder: 'Search contacts...',
            };
        case 'ContactProfile':
            return {
                contact: global.testUtils.createMockContact(),
                onMessagePress: jest.fn(),
                onCallPress: jest.fn(),
                onEditPress: jest.fn(),
            };
        case 'MessageThread':
            return {
                messages: [global.testUtils.createMockMessage()],
                onMessagePress: jest.fn(),
                onLoadMore: jest.fn(),
            };
        default:
            return {};
    }
}