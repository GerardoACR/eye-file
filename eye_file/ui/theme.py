# ---------------------------------------------------------------------------
# QSS (Qt Style Sheets)
# Think of this as "CSS for Qt widgets".
# It controls colors, borders, padding, hover states, etc.
#
# If you want to tweak the theme later, you'll mostly change values here:
# - Backgrounds: #0F1115, #151A21, #1B2230
# - Text: #E6E8EE, #AAB2C0
# - Accent orange: #FF8A3D, #C96B30
# ---------------------------------------------------------------------------
EYEFILE_QSS = """
/* Global defaults for (almost) all widgets */
* {
  font-family: "Segoe UI";
  font-size: 10.5pt;
  color: #E6E8EE;
}

/* Main window + generic widgets background */
QMainWindow, QWidget {
  background-color: #0F1115;
}

/* Frames / group boxes (not used yet, but you will use them later) */
QFrame, QGroupBox {
  background-color: #151A21;
  border: 1px solid #242C3A;
  border-radius: 8px;
}

/* Labels (text widgets) */
QLabel {
  color: #E6E8EE;
}

/* Default button style */
QPushButton {
  background-color: #1B2230;
  border: 1px solid #242C3A;
  border-radius: 8px;
  padding: 6px 10px;
}

/* Button hover state */
QPushButton:hover {
  background-color: #202A3A;
}

/* Button pressed state */
QPushButton:pressed {
  background-color: #151A21;
}

/* "PrimaryAction" button: selected by objectName, not by text */
QPushButton#PrimaryAction {
  border: 1px solid #C96B30;
}

/* Primary button hover: brighter orange border */
QPushButton#PrimaryAction:hover {
  border: 1px solid #FF8A3D;
}
"""
