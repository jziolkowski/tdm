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
    }
}