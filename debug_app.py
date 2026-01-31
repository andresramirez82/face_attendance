import traceback
import sys
import flet as ft

try:
    from main import main
    ft.app(main)
except Exception:
    traceback.print_exc()
