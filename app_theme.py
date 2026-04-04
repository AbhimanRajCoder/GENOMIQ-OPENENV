"""
GenomIQ — Custom Gradio theme: Adaptive Laboratory.

Supports both Light and Dark modes based on user system settings.
Uses a professional, high-fidelity research aesthetic.
"""

from gradio.themes import Base
from gradio.themes.utils import colors, fonts, sizes


class GenomIQTheme(Base):
    def __init__(self):
        super().__init__(
            primary_hue=colors.indigo,
            secondary_hue=colors.slate,
            neutral_hue=colors.slate,
            font=fonts.GoogleFont("Inter"),
            font_mono=fonts.GoogleFont("JetBrains Mono"),
        )
        self.set(
            # Backgrounds
            body_background_fill="#f8fafc",          # Light: Slate 50
            body_background_fill_dark="#0b0f1a",     # Dark: Deep Navy
            block_background_fill="#ffffff",         # Light: White
            block_background_fill_dark="#121826",    # Dark: Dark Navy

            # Borders
            block_border_color="#e2e8f0",            # Light
            block_border_color_dark="#1e293b",       # Dark
            border_color_accent="#6366f1",

            # Text
            block_label_text_color="#64748b",
            block_label_text_color_dark="#94a3b8",
            block_title_text_color="#0f172a",
            block_title_text_color_dark="#f1f5f9",
            body_text_color="#1e293b",
            body_text_color_dark="#f1f5f9",

            # Buttons
            button_primary_background_fill="#4f46e5",
            button_primary_background_fill_hover="#4338ca",
            button_primary_text_color="#ffffff",
            button_secondary_background_fill="#f1f5f9",
            button_secondary_background_fill_dark="#1e293b",
            button_secondary_background_fill_hover="#e2e8f0",
            button_secondary_text_color="#334155",
            button_secondary_text_color_dark="#cbd5e1",

            # Inputs
            input_background_fill="#ffffff",
            input_background_fill_dark="#0f172a",
            input_border_color="#cbd5e1",
            input_border_color_dark="#334155",

            # Layout
            block_shadow="0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
            section_header_text_size=sizes.text_md,
        )
