import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components/native';
import { Animated, TouchableOpacity } from 'react-native';

const AnimatedSwitch = ({ value, onValueChange, disabled = false }) => {
  const [isOn, setIsOn] = useState(value);
  const animatedValue = useRef(new Animated.Value(value ? 1 : 0)).current;

  useEffect(() => {
    Animated.spring(animatedValue, {
      toValue: isOn ? 1 : 0,
      useNativeDriver: true,
      friction: 6,
    }).start();
  }, [isOn]);

  const handleToggle = () => {
    if (!disabled) {
      const newValue = !isOn;
      setIsOn(newValue);
      onValueChange?.(newValue);
    }
  };

  const translateX = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: [3, 31],
  });

  const backgroundColor = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['#cccccc', '#4296f4'],
  });

  return (
    <TouchableOpacity onPress={handleToggle} activeOpacity={0.8} disabled={disabled}>
      <Track as={Animated.View} style={{ backgroundColor }} disabled={disabled}>
        <Thumb
          as={Animated.View}
          style={{
            transform: [{ translateX }],
          }}
        />
      </Track>
    </TouchableOpacity>
  );
};

const Track = styled.View`
  width: 56px;
  height: 32px;
  border-radius: 16px;
  padding: 3px;
  justify-content: center;
  opacity: ${props => props.disabled ? 0.5 : 1};
`;

const Thumb = styled.View`
  width: 26px;
  height: 26px;
  background-color: #ffffff;
  border-radius: 13px;
  shadow-color: #000;
  shadow-offset: 0px 2px;
  shadow-opacity: 0.2;
  shadow-radius: 4px;
  elevation: 4;
`;

export default AnimatedSwitch;