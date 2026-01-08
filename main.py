import sys
from PySide6.QtWidgets import QApplication

# Import the global Qt Style Sheet (QSS) for the whole app.
# This is where your colors, borders, fonts, hover states, etc. live.
# If you want to change the look & feel later, you usually edit theme.py, not this file.
from eye_file.ui.theme import EYEFILE_QSS

# Import the main window class (your actual UI layout lives there).
# As the project grows, the MainWindow will orchestrate panels, menus, signals, and services.
from eye_file.ui.main_window import MainWindow


def main() -> int:
    """
    App entrypoint.

    Responsibilities of this function:
    - Create exactly ONE QApplication (Qt's event loop + global app state).
    - Apply a base style and your custom theme (QSS).
    - Create the main window and show it.
    - Start the Qt event loop (blocking call) and return the exit code.
    """

    # QApplication is required for any Qt GUI app.
    # It manages the event loop (mouse/keyboard events, repainting, timers, signals, etc.).
    #
    # sys.argv passes command-line arguments to Qt. You usually keep this even if you don't use args.
    app = QApplication(sys.argv)

    # "Fusion" is a cross-platform Qt style. It makes widgets consistent across OSes.
    # Your QSS overrides (or complements) the base style, so visuals stay predictable.
    #
    # If you want a more "native Windows" look, you could remove this line,
    # but Fusion + QSS is usually more consistent for custom themes.
    app.setStyle("Fusion")

    # Apply the theme globally to every widget in the application.
    #
    # To modify:
    # - Change colors/fonts/borders in `eyefile/ui/theme.py`.
    # - Avoid scattering style changes across many widgets unless there is a strong reason.
    app.setStyleSheet(EYEFILE_QSS)

    # Create the main window (top-level UI).
    # To modify the UI layout, edit `eyefile/ui/main_window.py`.
    window = MainWindow()

    # Make the window visible on screen.
    window.show()

    # Start the Qt event loop.
    # This call blocks until the user closes the app (or you call app.quit()).
    #
    # The integer returned is the process exit code.
    return app.exec()


if __name__ == "__main__":
    # Standard Python entrypoint guard.
    #
    # raise SystemExit(...) ensures the OS receives the same exit code returned by Qt.
    # (Useful for scripting/testing and consistent termination behavior.)
    raise SystemExit(main())