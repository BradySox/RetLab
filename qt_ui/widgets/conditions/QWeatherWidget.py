from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QGridLayout
from dcs.weather import Weather as PydcsWeather

from game.timeofday import TimeOfDay
from game.utils import mps
from game.weather.conditions import Conditions
from game.weather.weathertext import (
    WIND_LEVEL_LABELS,
    air_text,
    clouds_text,
    visibility_text,
    wind_text,
)
from qt_ui import uiconstants as CONST


class QWeatherWidget(QGroupBox):
    """
    UI Component to display current weather forecast
    """

    turn = None
    conditions = None
    auto_fog = False

    def __init__(self):
        super(QWeatherWidget, self).__init__("")
        self.setProperty("style", "QWeatherWidget")

        self.icons = {
            TimeOfDay.Dawn: CONST.ICONS["Dawn"],
            TimeOfDay.Day: CONST.ICONS["Day"],
            TimeOfDay.Dusk: CONST.ICONS["Dusk"],
            TimeOfDay.Night: CONST.ICONS["Night"],
        }

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.makeWeatherIcon()
        self.makeCloudRainFogWidget()
        self.makeWindsWidget()

    def makeWeatherIcon(self):
        """Makes the Weather Icon Widget"""
        self.weather_icon = QLabel()
        self.weather_icon.setPixmap(self.icons[TimeOfDay.Dawn])
        self.layout.addWidget(self.weather_icon)

    def makeCloudRainFogWidget(self):
        """Makes the clouds, rain and visibility, and air lines."""
        self.textLayout = QVBoxLayout()
        self.layout.addLayout(self.textLayout)

        self.forecastClouds = self.makeLabel()
        self.textLayout.addWidget(self.forecastClouds)

        self.forecastRain = self.makeLabel()
        self.textLayout.addWidget(self.forecastRain)

        self.forecastAir = self.makeLabel()
        self.textLayout.addWidget(self.forecastAir)

    def makeWindsWidget(self):
        """Factory for the winds widget."""
        windsLayout = QGridLayout()
        self.layout.addLayout(windsLayout)

        windsLayout.addWidget(self.makeIcon(CONST.ICONS["Weather_winds"]), 0, 0, 3, 1)

        self.windLabels = []
        for row, level in enumerate(WIND_LEVEL_LABELS):
            windsLayout.addWidget(self.makeLabel(level), row, 1)
            speed = self.makeLabel("0 kts")
            direction = self.makeLabel("000°")
            windsLayout.addWidget(speed, row, 2)
            windsLayout.addWidget(direction, row, 3)
            self.windLabels.append((speed, direction))

    def makeLabel(self, text: str = "") -> QLabel:
        """Shorthand to generate a QLabel with widget standard style

        :arg pixmap QPixmap for the icon.
        """
        label = QLabel(text)
        label.setProperty("style", "text-sm")

        return label

    def makeIcon(self, pixmap: QPixmap) -> QLabel:
        """Shorthand to generate a QIcon with pixmap.

        :arg pixmap QPixmap for the icon.
        """
        icon = QLabel()
        icon.setPixmap(pixmap)

        return icon

    def setCurrentTurn(
        self, turn: int, conditions: Conditions, auto_fog: bool = False
    ) -> None:
        """Sets the turn information display.

        :arg turn Current turn number.
        :arg conditions Current time and weather conditions.
        :arg auto_fog DCS sets the fog itself (the Use DCS' automatic fog setting).
        """
        self.turn = turn
        self.conditions = conditions
        self.auto_fog = auto_fog

        self.update_forecast()
        self.updateWinds()

    def updateWinds(self):
        """Updates the UI with the current conditions wind info."""
        wind = self.conditions.weather.wind
        for (speed_label, dir_label), level in zip(
            self.windLabels, (wind.at_0m, wind.at_2000m, wind.at_8000m)
        ):
            speed, direction = wind_text(
                mps(level.speed or 0).knots, int(level.direction or 0)
            )
            speed_label.setText(speed)
            dir_label.setText(direction)

    def update_forecast(self):
        """Updates the forecast text and icon from the current conditions."""
        weather = self.conditions.weather
        clouds = weather.clouds
        self.forecastClouds.setText(clouds_text(clouds))
        if clouds is not None and clouds.preset is not None:
            self.forecastClouds.setToolTip(clouds.preset.ui_name)
        else:
            self.forecastClouds.setToolTip("")

        cloud_density = 0
        if clouds is not None:
            cloud_density = 5 if clouds.preset is not None else clouds.density
        weather_type = "clear" if not cloud_density else "partly-cloudy"

        precipitation = clouds.precipitation if clouds is not None else None
        if clouds is not None and clouds.preset is not None:
            rain = "Rain" if "Rain" in clouds.preset.name else "No rain"
        elif precipitation == PydcsWeather.Preceptions.Rain:
            rain = "Rain"
        elif precipitation == PydcsWeather.Preceptions.Thunderstorm:
            rain = "Thunderstorm"
        else:
            rain = "No rain"
        if rain == "Rain":
            weather_type = "rain"
        elif rain == "Thunderstorm":
            weather_type = "thunderstorm"

        fog = None if self.auto_fog else weather.fog
        dust = None if self.auto_fog else getattr(weather, "dust", None)
        visibility = visibility_text(fog, dust, self.auto_fog)
        self.forecastRain.setText(f"{rain} · {visibility}")
        if fog is not None:
            weather_type = "cloudy-fog" if cloud_density > 1 else "fog"

        self.forecastAir.setText(air_text(weather.atmospheric))
        self.update_forecast_icons(weather_type)

    def update_forecast_icons(self, weather_type: str) -> None:
        time = "night" if self.conditions.time_of_day == TimeOfDay.Night else "day"
        icon_key = f"Weather_{time}-{weather_type}"
        icon = CONST.ICONS.get(icon_key) or CONST.ICONS["Weather_night-partly-cloudy"]
        self.weather_icon.setPixmap(icon)
