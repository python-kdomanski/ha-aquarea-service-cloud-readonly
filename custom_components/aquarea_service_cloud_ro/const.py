DOMAIN = "aquarea_service_cloud_ro"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"
CONF_NAME_LANGUAGE = "name_language"
NAME_LANGUAGES = ("auto", "pl", "en")
DEFAULT_SCAN_INTERVAL = 60
PLATFORMS = ["sensor"]
SERVICE_URL = "https://aquarea-service.panasonic.com/"
HISTORY_POLL_INTERVAL = 300
HISTORY_LOOKBACK = 3600
HISTORY_MAX_AGE = 1200
# Indices confirmed from the user's Service Cloud chart requests.
HISTORY_FIELDS = {
    "OutdoorCurrent": 63,
    "HeatingInputPower": 72,
    "DhwInputPower": 78,
}

SENSORS = {
    "RunningStatus": ("Running status", None, "enum"),
    "WorkingMode": ("Working mode", None, "enum"),
    "WaterInleet": ("Water inlet", "°C", "temperature"),
    "WaterOutleet": ("Water outlet", "°C", "temperature"),
    "Zone1ActualTemperature": ("Zone 1 actual temperature", "°C", "temperature"),
    "Zone1SetpointTemperature": ("Zone 1 setpoint temperature (cloud value)", "°C", "temperature"),
    "Zone1WaterTemperature": ("Zone 1 water temperature", "°C", "temperature"),
    "Zone2ActualTemperature": ("Zone 2 actual temperature", "°C", "temperature"),
    "Zone2SetpointTemperature": ("Zone 2 setpoint temperature", "°C", "temperature"),
    "Zone2WaterTemperature": ("Zone 2 water temperature", "°C", "temperature"),
    "DailyWaterTankActualTemperature": ("DHW tank temperature", "°C", "temperature"),
    "DailyWaterTankSetpointTemperature": ("DHW tank setpoint", "°C", "temperature"),
    "BufferTankTemperature": ("Buffer tank temperature", "°C", "temperature"),
    "OutdoorTemperature": ("Outdoor temperature", "°C", "temperature"),
    "WaterFlow": ("Water flow", None, "measurement"),
    "PumpSpeed": ("Pump speed", None, "measurement"),
    "HeatDirection": ("Heat direction", None, "enum"),
    "RoomHeaterStatus": ("Room heater status", None, "enum"),
    "DailyWaterHeaterStatus": ("DHW heater status", None, "enum"),
    "DefrostStatus": ("Defrost status", None, "enum"),
    "SolarStatus": ("Solar status", None, "enum"),
    "SolarTemperature": ("Solar temperature", "°C", "temperature"),
    "BiMode": ("Bivalent mode", None, "enum"),
    "ErrorStatus": ("Error status", None, "enum"),
    "CompressorFrequency": ("Compressor frequency", None, "measurement"),
    "Runtime": ("Runtime", None, "measurement"),
    "RunCount": ("Run count", None, "measurement"),
    "RoomHeaterPerformance": ("Room heater performance", None, "measurement"),
    "RoomHeaterRunTime": ("Room heater runtime", None, "measurement"),
    "DailyWaterHeaterRunTime": ("DHW heater runtime", None, "measurement"),
    "OutdoorCurrent": ("Prąd zewnętrzny", "A", "current"),
    "HeatingInputPower": ("Pobór mocy w trybie grzania", "kW", "power"),
    "DhwInputPower": ("Pobór mocy w trybie CWU", "kW", "power"),
}

STATUS_FIELDS = {
    "RunningStatus": ("005", "textValue"), "WorkingMode": ("007", "textValue"),
    "WaterInleet": ("009", "value"), "WaterOutleet": ("011", "value"),
    "Zone1ActualTemperature": ("013", "value"), "Zone1SetpointTemperature": ("015", "value"),
    "Zone1WaterTemperature": ("017", "value"), "Zone2ActualTemperature": ("019", "value"),
    "Zone2SetpointTemperature": ("021", "value"), "Zone2WaterTemperature": ("023", "value"),
    "DailyWaterTankActualTemperature": ("025", "value"), "DailyWaterTankSetpointTemperature": ("027", "value"),
    "BufferTankTemperature": ("029", "value"), "OutdoorTemperature": ("031", "value"),
    "WaterFlow": ("035", "value"), "PumpSpeed": ("037", "value"),
    "HeatDirection": ("039", "textValue"), "RoomHeaterStatus": ("041", "textValue"),
    "DailyWaterHeaterStatus": ("043", "textValue"), "DefrostStatus": ("045", "textValue"),
    "SolarStatus": ("047", "value"), "SolarTemperature": ("049", "value"),
    "BiMode": ("051", "value"), "ErrorStatus": ("053", "value"),
    "CompressorFrequency": ("056", "value"), "Runtime": ("058", "value"),
    "RunCount": ("060", "value"), "RoomHeaterPerformance": ("063", "value"),
    "RoomHeaterRunTime": ("065", "value"), "DailyWaterHeaterRunTime": ("068", "value"),
}

TRANSLATIONS = {
    "2006-0310": "On", "2006-0300": "Off", "2006-0339": "Heat + Tank",
    "2006-032F": "Auto (Heat)", "2006-0325": "Heat", "2006-0940": "Room",
    "2006-0960": "Off", "2006-09B0": "On", "2006-09A0": "Off",
}
