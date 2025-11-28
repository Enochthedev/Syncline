// Sky Blue Color Palette
export const colors = {
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

    // Platform colors (updated to match sky blue theme)
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

export const typography = {
    h1: {
        fontSize: 32,
        fontWeight: 'bold' as const,
        lineHeight: 40,
        color: colors.text,
    },
    h2: {
        fontSize: 24,
        fontWeight: 'bold' as const,
        lineHeight: 32,
        color: colors.text,
    },
    h3: {
        fontSize: 20,
        fontWeight: '600' as const,
        lineHeight: 28,
        color: colors.text,
    },
    h4: {
        fontSize: 18,
        fontWeight: '600' as const,
        lineHeight: 24,
        color: colors.text,
    },
    body: {
        fontSize: 16,
        lineHeight: 24,
        color: colors.text,
    },
    bodySmall: {
        fontSize: 14,
        lineHeight: 20,
        color: colors.textSecondary,
    },
    caption: {
        fontSize: 12,
        lineHeight: 16,
        color: colors.textTertiary,
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

export default theme;
