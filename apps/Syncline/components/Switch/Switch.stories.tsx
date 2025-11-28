import type { Meta, StoryObj } from "@storybook/react-native";
import { fn } from "storybook/test";
import { View } from "react-native";
import CustomSwitch  from "./Switch";

const meta = {
    title: "Switch",
    component: CustomSwitch,
    args: {
        text: "Hello world",
    },
    decorators: [
        (Story) => (
            <View style={{ padding: 16 }}>
                <Story />
            </View>
        ),
    ],
} satisfies Meta<typeof CustomSwitch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Basic: Story = {
    args: {
        onPress: fn(),
    },
};

