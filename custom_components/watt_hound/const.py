DOMAIN = "watt_hound"

# Config entry keys
CONF_POWER_SENSOR = "power_sensor"
CONF_PHASE_SENSORS = "phase_sensors"
CONF_MEASURE_DELAY = "measure_delay"
CONF_CLEAN_WINDOW = "clean_window"
CONF_MIN_SAMPLES = "min_samples"
CONF_MAX_SAMPLES = "max_samples"
CONF_TRACK_LIGHTS = "track_lights"
CONF_TRACK_SWITCHES = "track_switches"
CONF_EXCLUDED_ENTITIES = "excluded_entities"

# Defaults – tuned for a Shelly 3EM reporting every ~2s
DEFAULT_MEASURE_DELAY = 4       # seconds to wait before sampling after a switch event
DEFAULT_CLEAN_WINDOW = 6        # seconds – no other events allowed within this window
DEFAULT_MIN_SAMPLES = 3         # minimum clean measurements before exposing a value
DEFAULT_MAX_SAMPLES = 30        # rolling window size for the estimator

# Storage
STORAGE_KEY = "watt_hound.learned"
STORAGE_VERSION = 1

# Sensor attribute keys
ATTR_ESTIMATED_POWER = "estimated_power"
ATTR_ON_DELTA_AVG = "on_delta_avg"
ATTR_OFF_DELTA_AVG = "off_delta_avg"
ATTR_SAMPLE_COUNT = "sample_count"
ATTR_CONFIDENCE = "confidence"
ATTR_LAST_CLEAN = "last_clean_measurement"
ATTR_DIRTY_COUNT = "dirty_count"
