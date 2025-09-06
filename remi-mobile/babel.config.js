module.exports = {
    presets: ['babel-preset-expo'],
    plugins: [
        [
            'module-resolver',
            {
                root: ['./src'],
                extensions: ['.ios.js', '.android.js', '.js', '.ts', '.tsx', '.json'],
                alias: {
                    '@': './src',
                    '@/components': './src/components',
                    '@/screens': './src/screens',
                    '@/navigation': './src/navigation',
                    '@/services': './src/services',
                    '@/hooks': './src/hooks',
                    '@/utils': './src/utils',
                    '@/types': './src/types',
                    '@/constants': './src/constants',
                },
            },
        ],
        'react-native-reanimated/plugin', // Must be last
    ],
};