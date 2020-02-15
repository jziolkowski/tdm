setoptions = {
    "0": {
        "description": "Save power state and use after restart",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled"},
            "1": {"description": "Enabled", "default": "True"}
        }
    },

    "1": {
        "description": "Set button multipress mode",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled"},
            "1": {"description": "Enabled", "default": "True"}
        }
    },

    "11": {
        "description": "Swap button single and double press functionality",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled", "default": "True"},
            "1": {"description": "Enabled"}
        }
    },

    "13": {
        "description": "Allow immediate action on single button press",
        "type": "select",
        "parameters": {
            "0": {"description": "Single, multi-press and hold button actions", "default": "True"},
            "1": {"description": "Only single press action for immediate response"}
        }
    },

    "15": {
        "description": "Set PWM control for LED lights",
        "type": "select",
        "parameters": {
            "0": {"description": "basic PWM Control"},
            "1": {"description": "control with Color or Dimmer commands", "default": "True"}
        }
    },

    "16": {
        "description": "Set addressable LED Clock scheme parameter",
        "type": "select",
        "parameters": {
            "0": {"description": "clock-wise mode", "default": "True"},
            "1": {"description": "counter-clock-wise mode"}
        }
    },

    "17": {
        "description": "Show Color string as",
        "type": "select",
        "parameters": {
            "0": {"description": "hex string", "default": "True"},
            "1": {"description": "comma-separated decimal string"}
        }
    },

    "20": {
        "description": "Update of Dimmer/Color/CT without turning power on",
        "type": "select",
        "parameters": {
            "0": {"description": "disabled (default)", "default": "True"},
            "1": {"description": "enabled"}
        }
    },


    "26": {
        "description": "Use indexes even when only one relay is present",
        "type": "select",
        "parameters": {
            "0": {"description": "Messages use POWER", "default": "True"},
            "1": {"description": "Messages use POWER1"}
        }
    },

    "32": {
        "description": "Number of 0.1 seconds to hold button before sending HOLD action message",
        "type": "value",
        "parameters": {
            "min": "1",
            "max": "100",
            "default": "40"
        }
    },

    "40": {
        "description": "Stop detecting any input change on the button GPIO [0.1s]",
        "type": "value",
        "parameters": {
            "min": "0",
            "max": "250",
            "default": "1"
        }
    },

    "61": {
        "description": "Force local operation when ButtonTopic or SwitchTopic is set",
        "type": "select",
        "parameters": {
            "0": {"description": "Disabled", "default": "True"},
            "1": {"description": "Enabled"}
        }
    },

    "63": {
        "description": "Scan relay power feedback state at restart",
        "type": "select",
        "parameters": {
            "0": {"description": "Enabled", "default": "True"},
            "1": {"description": "Disabled"}
        }
    },

    "68": {
        "description": "Set PWM channel combinations",
        "type": "select",
        "parameters": {
            "0": {"description": "Treat PWM as a single RGB(WW) light ", "default": "True"},
            "1": {"description": "Treat every PWM as separate channel"}
        }
    }
}