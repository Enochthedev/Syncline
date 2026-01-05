import { Stack } from "expo-router";
import { ThemeProvider } from "../src/contexts/ThemeContext";
import { AuthProvider } from "../src/contexts/AuthContext";
import { AuthGuard } from "../src/components/AuthGuard";

const StorybookEnabled = process.env.EXPO_PUBLIC_STORYBOOK_ENABLED === "true";

export const unstable_settings = {
  initialRouteName: StorybookEnabled ? "(storybook)/index" : "(auth)/login",
};

import { TamaguiProvider } from "tamagui";
import config from "../tamagui.config";
import { useTheme } from "../src/contexts/ThemeContext";

export default function RootLayout() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <RootLayoutContent />
      </ThemeProvider>
    </AuthProvider>
  );
}

function RootLayoutContent() {
  const { isDark } = useTheme();

  return (
    <TamaguiProvider config={config} defaultTheme={isDark ? "dark" : "light"}>
      <AuthGuard>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Protected guard={StorybookEnabled}>
            <Stack.Screen name="(storybook)/index" />
          </Stack.Protected>

          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="profile" />
        </Stack>
      </AuthGuard>
    </TamaguiProvider>
  );
}
