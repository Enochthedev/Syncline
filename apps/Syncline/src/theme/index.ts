// Theme system with light and dark modes

// Light Mode Colors
export const lightColors = {
    // Primary - Sky Blue
    primary: '#0EA5E9',
    primaryLight: '#38BDF8',
    primaryDark: '#0284C7',
    primaryLighter: '#E0F2FE',

    // Secondary - Complementary
    secondary: '#8B5CF6',
    secondaryLight: '#A78BFA',
    secondaryDark: '#7C3AED',

    // Neutrals
    background: '#FFFFFF',
    backgroundSecondary: '#F8FAFC',
    surface: '#F1F5F9',
    surfaceLight: '#F8FAFC',

    // Text
    text: '#0F172A',
    textSecondary: '#64748B',
    textTertiary: '#94A3B8',

    // Borders
    border: '#E2E8F0',
    borderLight: '#F1F5F9',

    // Status Colors
    error: '#EF4444',
    errorLight: '#FEE2E2',
    success: '#10B981',
    successLight: '#D1FAE5',
    warning: '#F59E0B',
    warningLight: '#FEF3C7',
    info: '#3B82F6',
    infoLight: '#DBEAFE',

    // Platform colors
    gmail: '#EA4335',
    slack: '#4A154B',
    discord: '#5865F2',
    telegram: '#0088CC',
    twitter: '#1DA1F2',
    whatsapp: '#25D366',

    // Additional
    white: '#FFFFFF',
    black: '#000000',
    overlay: 'rgba(0, 0, 0, 0.5)',
};

// Dark Mode Colors
export const darkColors = {
    // Primary - Sky Blue (slightly adjusted for dark mode)
    primary: '#38BDF8',
    primaryLight: '#7DD3FC',
    primaryDark: '#0EA5E9',
    primaryLighter: '#082F49',

    // Secondary - Complementary
    secondary: '#A78BFA',
    secondaryLight: '#C4B5FD',
    secondaryDark: '#8B5CF6',

    // Neutrals
    background: '#0F172A',
    backgroundSecondary: '#1E293B',
    surface: '#334155',
    surfaceLight: '#475569',

    // Text
    text: '#F1F5F9',
    textSecondary: '#CBD5E1',
    textTertiary: '#94A3B8',

    // Borders
    border: '#334155',
    borderLight: '#475569',

    // Status Colors
    error: '#F87171',
    errorLight: '#7F1D1D',
    success: '#34D399',
    successLight: '#064E3B',
    warning: '#FBBF24',
    warningLight: '#78350F',
    info: '#60A5FA',
    infoLight: '#1E3A8A',

    // Platform colors (same in dark mode)
    gmail: '#EA4335',
    slack: '#4A154B',
    discord: '#5865F2',
    telegram: '#0088CC',
    twitter: '#1DA1F2',
    whatsapp: '#25D366',

    // Additional
    white: '#FFFFFF',
    black: '#000000',
    overlay: 'rgba(0, 0, 0, 0.7)',
};

// Default to light mode (will be overridden by useTheme hook)
export const colors = lightColors;

export const spacing = {
    xs: 4,
    s: 8,
    m: 16,
    l: 24,
    xl: 32,
    xxl: 48,
};

export const borderRadius = {
    xs: 4,
    s: 8,
    m: 12,
    l: 16,
    xl: 24,
    full: 9999,
};

export const shadows = {
    sm: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
    },
    md: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    lg: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 5,
    },
    xl: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.2,
        shadowRadius: 16,
        elevation: 8,
    },
};

// Dark mode shadows (stronger for dark backgrounds)
export const darkShadows = {
    sm: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.3,
        shadowRadius: 2,
        elevation: 1,
    },
    md: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.4,
        shadowRadius: 4,
        elevation: 3,
    },
    lg: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.5,
        shadowRadius: 8,
        elevation: 5,
    },
    xl: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.6,
        shadowRadius: 16,
        elevation: 8,
    },
};

export const typography = {
    h1: {
        fontSize: 32,
        fontWeight: 'bold' as const,
        lineHeight: 40,
    },
    h2: {
        fontSize: 24,
        fontWeight: 'bold' as const,
        lineHeight: 32,
    },
    h3: {
        fontSize: 20,
        fontWeight: '600' as const,
        lineHeight: 28,
    },
    h4: {
        fontSize: 18,
        fontWeight: '600' as const,
        lineHeight: 24,
    },
    body: {
        fontSize: 16,
        lineHeight: 24,
    },
    bodySmall: {
        fontSize: 14,
        lineHeight: 20,
    },
    caption: {
        fontSize: 12,
        lineHeight: 16,
    },
    button: {
        fontSize: 16,
        fontWeight: '600' as const,
        lineHeight: 24,
    },
};

export const theme = {
    colors,
    spacing,
    borderRadius,
    shadows,
    typography,
};

// Helper function to get themed colors
export const getThemeColors = (isDark: boolean) => {
    return isDark ? darkColors : lightColors;
};

// Helper function to get themed shadows
export const getThemeShadows = (isDark: boolean) => {
    return isDark ? darkShadows : shadows;
};

export default theme;
