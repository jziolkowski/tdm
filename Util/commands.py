commands = {
  "BlinkCount": {
        "description": "Number of relay toggles (blinks)",
        "type": "value",
        "parameters": {
            "min": "0",
            "max": "32000",
            "default": "10"
        }
    },

  "BlinkTime": {
        "description": "Blink duration [0.1s]",
        "type": "value",
        "parameters": {
            "min": "2",
            "max": "3600",
            "default": "10"
        }
    },

  "ButtonDebounce": {
        "description": "Button debounce timing [ms]",
        "type": "value",
        "parameters": {
            "min": "40",
            "max": "100",
            "default": "50"
        }
    },

  "ButtonRetain": {
        "description": "Add MQTT retain flag on button press",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled", "default": "True"},
            "1": {"description": "Enabled"}
        }
    },

  "ButtonTopic": {
        "description": "MQTT button topic",
        "type": "select",
        "editable": "True",
        "parameters": {
            "0": {"description": "Disable use of ButtonTopic", "default": "True"},
            "1": {"description": "Set ButtonTopic to device %topic%"},
            "2": {"description": "Reset ButtonTopic to firmware default"}
        }
    },

  "Interlock": {
        "description": "Relay interlock mode",
        "type": "select",
        "parameters": {
            "0": {"description": "Self-locking mode for all relays", "default": "True"},
            "1": {"description": "Interlock mode for selected relays"}
        }
    },

  "PowerOnState": {
        "description": "Control relay state when the device is powered up",
        "type": "select",
        "parameters": {
            "0": {"description": "Keep relay(s) OFF after power up"},
            "1": {"description": "Turn relay(s) ON after power up"},
            "2": {"description": "Toggle relay(s) from last saved state"},
            "3": {"description": "Switch relay(s) to their last saved state", "default": "True"},
            "4": {"description": "Turn relay(s) ON and disable further relay control"},
            "5": {"description": "Turn relay(s) ON after a PulseTime period"}
        }
    },

  "PowerRetain": {
        "description": "Add MQTT power retain flag on status update",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled", "default": "True"},
            "1": {"description": "Enabled"}
        }
    },

  "PulseTime": {
        "description": "Control the relay PulseTime",
        "type": "value",
        "parameters": {
            "min": "0",
            "max": "64900"
        }
    },

  "SwitchMode": {
        "description": "Configure the behavior of a physical input peripheral configured as a Switch<x>",
        "type": "select",
        "parameters": {
            "0": {"description": "Toggle", "default": "True"},
            "1": {"description": "Follow [0=Off, 1=On]"},
            "2": {"description": "Inverted follow [0=On, 1=Off]"},
            "3": {"description": "Pushbutton [Default 0, 1=Toggle]"},
            "4": {"description": "Inverted pushbutton [Default 1, 0=Toggle]"},
            "5": {"description": "Pushbutton with hold [Default 1, 0=Toggle, 2=Hold]"},
            "6": {"description": "Inverted pushbutton with hold [Default 0, 1=Toggle, 2=Hold]"},
            "7": {"description": "Pushbutton toggle [0=Toggle, 1=Toggle]"}
        }
    },

  "SwitchDebounce": {
        "description": "Switch debounce timing [ms]",
        "type": "value",
        "parameters": {
            "min": "40",
            "max": "100",
            "default": "50"
        }
    },

  "SwitchRetain": {
        "description": "Add MQTT retain flag on switch press",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled", "default": "True"},
            "1": {"description": "Enabled"}
        }
    }
}