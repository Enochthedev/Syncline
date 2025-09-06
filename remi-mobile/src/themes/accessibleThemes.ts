import { ColorSchemeName } from 'react-native';

export interface AccessibleTheme {
    name: string;
    colors: {
        // Primary colors
        primary: string;
        primaryDark: string;
        primaryLight: string;
        secondary: string;
        secondaryDark: string;
        secondaryLight: string;

        // Background colors
        background: string;
        surface: string;
        card: string;

        // Text colors
        text: string;
        textSecondary: string;
        textDisabled: string;
        textInverse: string;

        // Border and divider colors
        border: string;
        divider: string;

        // Status colors
        error: string;
        errorLight: string;
        warning: string;
        warningLight: string;
        success: string;
        successLight: string;
        info: string;
        infoLight: string;

        // Interactive colors
        link: string;
        linkVisited: string;
        focus: string;
        selection: string;

        // Overlay colors
        overlay: string;
        backdrop: string;

        // Platform-specific colors
        notification: string;
        tabBar: string;
        statusBar: string;
    };

    // Accessibility properties
    accessibility: {
        contrastRatio: number;
        wcagLevel: 'AA' | 'AAA';
        highContrast: boolean;
    };

    // Typography scale
    typography: {
        fontSizes: {
            xs: number;
            sm: number;
            md: number;
            lg: number;
            xl: number;
            xxl: number;
        };
        lineHeights: {
            xs: number;
            sm: number;
            md: number;
            lg: number;
            xl: number;
            xxl: number;
        };
        fontWeights: {
            light: string;
            normal: string;
            medium: string;
            semibold: string;
            bold: string;
        };
    };

    // Spacing scale
    spacing: {
        xs: number;
        sm: number;
        md: number;
        lg: number;
        xl: number;
        xxl: number;
    };

    // Border radius scale
    borderRadius: {
        none: number;
        sm: number;
        md: number;
        lg: number;
        xl: number;
        full: number;
    };
}

// Standard theme (WCAG AA compliant)
export const standardTheme: AccessibleTheme = {
    name: 'Standard',
    colors: {
        primary: '#2196F3',
        primaryDark: '#1976D2',
        primaryLight: '#BBDEFB',
        secondary: '#03DAC6',
        secondaryDark: '#00BCD4',
        secondaryLight: '#B2EBF2',

        background: '#FFFFFF',
        surface: '#F5F5F5',
        card: '#FFFFFF',

        text: '#212121',
        textSecondary: '#757575',
        textDisabled: '#BDBDBD',
        textInverse: '#FFFFFF',

        border: '#E0E0E0',
        divider: '#EEEEEE',

        error: '#F44336',
        errorLight: '#FFEBEE',
        warning: '#FF9800',
        warningLight: '#FFF3E0',
        success: '#4CAF50',
        successLight: '#E8F5E8',
        info: '#2196F3',
        infoLight: '#E3F2FD',

        link: '#1976D2',
        linkVisited: '#7B1FA2',
        focus: '#2196F3',
        selection: '#BBDEFB',

        overlay: 'rgba(0, 0, 0, 0.5)',
        backdrop: 'rgba(0, 0, 0, 0.3)',

        notification: '#F44336',
        tabBar: '#FFFFFF',
        statusBar: '#1976D2',
    },

    accessibility: {
        contrastRatio: 4.5,
        wcagLevel: 'AA',
        highContrast: false,
    },

    typography: {
        fontSizes: {
            xs: 12,
            sm: 14,
            md: 16,
            lg: 18,
            xl: 20,
            xxl: 24,
        },
        lineHeights: {
            xs: 16,
            sm: 20,
            md: 24,
            lg: 28,
            xl: 32,
            xxl: 36,
        },
        fontWeights: {
            light: '300',
            normal: '400',
            medium: '500',
            semibold: '600',
            bold: '700',
        },
    },

    spacing: {
        xs: 4,
        sm: 8,
        md: 16,
        lg: 24,
        xl: 32,
        xxl: 48,
    },

    borderRadius: {
        none: 0,
        sm: 4,
        md: 8,
        lg: 12,
        xl: 16,
        full: 9999,
    },
};

// High contrast theme (WCAG AAA compliant)
export const highContrastTheme: AccessibleTheme = {
    name: 'High Contrast',
    colors: {
        primary: '#000000',
        primaryDark: '#000000',
        primaryLight: '#666666',
        secondary: '#000000',
        secondaryDark: '#000000',
        secondaryLight: '#666666',

        background: '#FFFFFF',
        surface: '#FFFFFF',
        card: '#FFFFFF',

        text: '#000000',
        textSecondary: '#000000',
        textDisabled: '#666666',
        textInverse: '#FFFFFF',

        border: '#000000',
        divider: '#000000',

        error: '#CC0000',
        errorLight: '#FFEEEE',
        warning: '#CC6600',
        warningLight: '#FFF5E6',
        success: '#006600',
        successLight: '#EEFFEE',
        info: '#0066CC',
        infoLight: '#EEF5FF',

        link: '#0000EE',
        linkVisited: '#551A8B',
        focus: '#000000',
        selection: '#000000',

        overlay: 'rgba(0, 0, 0, 0.8)',
        backdrop: 'rgba(0, 0, 0, 0.6)',

        notification: '#CC0000',
        tabBar: '#FFFFFF',
        statusBar: '#000000',
    },

    accessibility: {
        contrastRatio: 7.0,
        wcagLevel: 'AAA',
        highContrast: true,
    },

    typography: {
        fontSizes: {
            xs: 14,
            sm: 16,
            md: 18,
            lg: 20,
            xl: 22,
            xxl: 26,
        },
        lineHeights: {
            xs: 18,
            sm: 22,
            md: 26,
            lg: 30,
            xl: 34,
            xxl: 38,
        },
        fontWeights: {
            light: '400',
            normal: '500',
            medium: '600',
            semibold: '700',
            bold: '800',
        },
    },

    spacing: {
        xs: 6,
        sm: 12,
        md: 20,
        lg: 28,
        xl: 36,
        xxl: 52,
    },

    borderRadius: {
        none: 0,
        sm: 2,
        md: 4,
        lg: 6,
        xl: 8,
        full: 9999,
    },
};

// Dark theme (WCAG AA compliant)
export const darkTheme: AccessibleTheme = {
    name: 'Dark',
    colors: {
        primary: '#90CAF9',
        primaryDark: '#42A5F5',
        primaryLight: '#E3F2FD',
        secondary: '#80CBC4',
        secondaryDark: '#4DB6AC',
        secondaryLight: '#E0F2F1',

        background: '#121212',
        surface: '#1E1E1E',
        card: '#2D2D2D',

        text: '#FFFFFF',
        textSecondary: '#B3B3B3',
        textDisabled: '#666666',
        textInverse: '#000000',

        border: '#404040',
        divider: '#333333',

        error: '#FF6B6B',
        errorLight: '#2D1B1B',
        warning: '#FFB74D',
        warningLight: '#2D2419',
        success: '#81C784',
        successLight: '#1B2D1B',
        info: '#64B5F6',
        infoLight: '#1B252D',

        link: '#90CAF9',
        linkVisited: '#CE93D8',
        focus: '#90CAF9',
        selection: '#1976D2',

        overlay: 'rgba(0, 0, 0, 0.7)',
        backdrop: 'rgba(0, 0, 0, 0.5)',

        notification: '#FF6B6B',
        tabBar: '#1E1E1E',
        statusBar: '#121212',
    },

    accessibility: {
        contrastRatio: 4.5,
        wcagLevel: 'AA',
        highContrast: false,
    },

    typography: {
        fontSizes: {
            xs: 12,
            sm: 14,
            md: 16,
            lg: 18,
            xl: 20,
            xxl: 24,
        },
        lineHeights: {
            xs: 16,
            sm: 20,
            md: 24,
            lg: 28,
            xl: 32,
            xxl: 36,
        },
        fontWeights: {
            light: '300',
            normal: '400',
            medium: '500',
            semibold: '600',
            bold: '700',
        },
    },

    spacing: {
        xs: 4,
        sm: 8,
        md: 16,
        lg: 24,
        xl: 32,
        xxl: 48,
    },

    borderRadius: {
        none: 0,
        sm: 4,
        md: 8,
        lg: 12,
        xl: 16,
        full: 9999,
    },
};

// Dark high contrast theme (WCAG AAA compliant)
export const darkHighContrastTheme: AccessibleTheme = {
    name: 'Dark High Contrast',
    colors: {
        primary: '#FFFFFF',
        primaryDark: '#FFFFFF',
        primaryLight: '#CCCCCC',
        secondary: '#FFFFFF',
        secondaryDark: '#FFFFFF',
        secondaryLight: '#CCCCCC',

        background: '#000000',
        surface: '#000000',
        card: '#000000',

        text: '#FFFFFF',
        textSecondary: '#FFFFFF',
        textDisabled: '#999999',
        textInverse: '#000000',

        border: '#FFFFFF',
        divider: '#FFFFFF',

        error: '#FF4444',
        errorLight: '#330000',
        warning: '#FFAA00',
        warningLight: '#332200',
        success: '#44FF44',
        successLight: '#003300',
        info: '#4444FF',
        infoLight: '#000033',

        link: '#66CCFF',
        linkVisited: '#CC99FF',
        focus: '#FFFFFF',
        selection: '#FFFFFF',

        overlay: 'rgba(255, 255, 255, 0.8)',
        backdrop: 'rgba(255, 255, 255, 0.6)',

        notification: '#FF4444',
        tabBar: '#000000',
        statusBar: '#000000',
    },

    accessibility: {
        contrastRatio: 7.0,
        wcagLevel: 'AAA',
        highContrast: true,
    },

    typography: {
        fontSizes: {
            xs: 14,
            sm: 16,
            md: 18,
            lg: 20,
            xl: 22,
            xxl: 26,
        },
        lineHeights: {
            xs: 18,
            sm: 22,
            md: 26,
            lg: 30,
            xl: 34,
            xxl: 38,
        },
        fontWeights: {
            light: '400',
            normal: '500',
            medium: '600',
            semibold: '700',
            bold: '800',
        },
    },

    spacing: {
        xs: 6,
        sm: 12,
        md: 20,
        lg: 28,
        xl: 36,
        xxl: 52,
    },

    borderRadius: {
        none: 0,
        sm: 2,
        md: 4,
        lg: 6,
        xl: 8,
        full: 9999,
    },
};

export const themes = {
    standard: standardTheme,
    highContrast: highContrastTheme,
    dark: darkTheme,
    darkHighContrast: darkHighContrastTheme,
};

export type ThemeName = keyof typeof themes;

export const getThemeForColorScheme = (
    colorScheme: ColorSchemeName,
    highContrast: boolean = false
): AccessibleTheme => {
    if (colorScheme === 'dark') {
        return highContrast ? darkHighContrastTheme : darkTheme;
    }
    return highContrast ? highContrastTheme : standardTheme;
};