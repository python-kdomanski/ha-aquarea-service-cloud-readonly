"""Display-name catalogs; identity and protocol keys never depend on language."""

SENSOR_NAMES_EN = {'RunningStatus': 'Running status',
 'WorkingMode': 'Working mode',
 'WaterInleet': 'Water inlet',
 'WaterOutleet': 'Water outlet',
 'Zone1ActualTemperature': 'Zone 1 actual temperature',
 'Zone1SetpointTemperature': 'Zone 1 setpoint temperature (cloud value)',
 'Zone1WaterTemperature': 'Zone 1 water temperature',
 'Zone2ActualTemperature': 'Zone 2 actual temperature',
 'Zone2SetpointTemperature': 'Zone 2 setpoint temperature',
 'Zone2WaterTemperature': 'Zone 2 water temperature',
 'DailyWaterTankActualTemperature': 'DHW tank temperature',
 'DailyWaterTankSetpointTemperature': 'DHW tank setpoint',
 'BufferTankTemperature': 'Buffer tank temperature',
 'OutdoorTemperature': 'Outdoor temperature',
 'WaterFlow': 'Water flow',
 'PumpSpeed': 'Pump speed',
 'HeatDirection': 'Heat direction',
 'RoomHeaterStatus': 'Room heater status',
 'DailyWaterHeaterStatus': 'DHW heater status',
 'DefrostStatus': 'Defrost status',
 'SolarStatus': 'Solar status',
 'SolarTemperature': 'Solar temperature',
 'BiMode': 'Bivalent mode',
 'ErrorStatus': 'Error status',
 'CompressorFrequency': 'Compressor frequency',
 'Runtime': 'Runtime',
 'RunCount': 'Run count',
 'RoomHeaterPerformance': 'Room heater performance',
 'RoomHeaterRunTime': 'Room heater runtime',
 'DailyWaterHeaterRunTime': 'DHW heater runtime',
 'OutdoorCurrent': 'Outdoor current',
 'HeatingInputPower': 'Heating input power',
 'DhwInputPower': 'DHW input power'}

SENSOR_NAMES_PL = {'RunningStatus': 'Stan pracy pompy',
 'WorkingMode': 'Tryb pracy',
 'WaterInleet': 'Temperatura wody na wejściu',
 'WaterOutleet': 'Temperatura wody na wyjściu',
 'Zone1ActualTemperature': 'Temperatura rzeczywista strefy 1',
 'Zone1SetpointTemperature': 'Nastawa temperatury strefy 1 (wartość z chmury)',
 'Zone1WaterTemperature': 'Temperatura wody w strefie 1',
 'Zone2ActualTemperature': 'Temperatura rzeczywista strefy 2',
 'Zone2SetpointTemperature': 'Nastawa temperatury strefy 2 (wartość z chmury)',
 'Zone2WaterTemperature': 'Temperatura wody w strefie 2',
 'DailyWaterTankActualTemperature': 'Temperatura CWU',
 'DailyWaterTankSetpointTemperature': 'Temperatura zadana CWU',
 'BufferTankTemperature': 'Temperatura bufora',
 'OutdoorTemperature': 'Temperatura zewnętrzna',
 'WaterFlow': 'Przepływ wody',
 'PumpSpeed': 'Prędkość pompy obiegowej',
 'HeatDirection': 'Kierunek grzania',
 'RoomHeaterStatus': 'Stan grzałki CO',
 'DailyWaterHeaterStatus': 'Stan grzałki CWU',
 'DefrostStatus': 'Stan odszraniania',
 'SolarStatus': 'Stan instalacji solarnej',
 'SolarTemperature': 'Temperatura instalacji solarnej',
 'BiMode': 'Tryb biwalentny',
 'ErrorStatus': 'Kod błędu',
 'CompressorFrequency': 'Częstotliwość sprężarki',
 'Runtime': 'Czas pracy sprężarki',
 'RunCount': 'Liczba uruchomień sprężarki',
 'RoomHeaterPerformance': 'Moc grzałki CO',
 'RoomHeaterRunTime': 'Czas pracy grzałki CO',
 'DailyWaterHeaterRunTime': 'Czas pracy grzałki CWU',
 'OutdoorCurrent': 'Prąd zewnętrzny',
 'HeatingInputPower': 'Pobór mocy w trybie grzania',
 'DhwInputPower': 'Pobór mocy w trybie CWU'}

def sensor_names(language, system_language="en"):
    """An unset option preserves the mixed legacy names from version 0.2.0."""
    if language == "auto":
        language = (system_language or "en").replace("_", "-").split("-", 1)[0].lower()
        language = "pl" if language == "pl" else "en"
    if language == "pl":
        return SENSOR_NAMES_PL
    if language == "en":
        return SENSOR_NAMES_EN
    return {}
