import flet as ft
from flet import Colors, BoxShadow, Offset, TextStyle, FontWeight, ButtonStyle, ControlState, RoundedRectangleBorder

class AppColors:
    PRIMARY = "#6366f1"
    SECONDARY = "#a855f7"
    BACKGROUND = "#0f172a"
    SURFACE = "#1e293b"
    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#94a3b8"
    SUCCESS = "#22c55e"
    DANGER = "#ef4444"
    GLASS = "#ffffff0a"

class AppStyles:
    CARD_STYLE = {
        "bgcolor": AppColors.SURFACE,
        "padding": 20,
        "border_radius": 15,
        "shadow": BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=Colors.with_opacity(0.1, "black"),
            offset=Offset(0, 5),
        ),
    }

    HERO_TEXT = TextStyle(
        size=36,
        weight=FontWeight.BOLD,
        color=AppColors.TEXT_PRIMARY,
        letter_spacing=1.2,
    )

    SUBTITLE_TEXT = TextStyle(
        size=16,
        color=AppColors.TEXT_SECONDARY,
    )

    SIDEBAR_BUTTON = {
        "variant": ButtonStyle(
            color={
                ControlState.DEFAULT: AppColors.TEXT_SECONDARY,
                ControlState.HOVERED: AppColors.TEXT_PRIMARY,
            },
            bgcolor={
                ControlState.HOVERED: AppColors.GLASS,
            },
            padding=20,
            shape=RoundedRectangleBorder(radius=10),
        )
    }
