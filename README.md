# Arbitrary Points Tracker GUI

Points Tracker is a simple GUI app to track your points every day. It has a friendly interface, saves your data, and shows your progress in a weekly view.

![preview](https://i.imgur.com/1gqVxdp.png)

## Key Features

- **Track Points Daily**: Easily add or remove points for each day.
- **Weekly View**: See your points for each week in a color-coded heatmap.
- **Customize**: Choose between light and dark mode, set daily point goals, and pick your favorite font.
- **Help and Keybindings**: Find a help window with options and keybindings under the Help menu in the toolbar.

## How to Start

1. **Install Python 3** if you don’t have it already.
2. Install the required library:
   ```bash
   pip install pyqt5
   ```
3. Run the app:
   ```bash
   python points-tracker.pyw
   ```

### Note:
- Upon launching, the app automatically creates:
  - A **database file** (`points.db`) in the same folder to save all your daily entries.
  - A **settings file** (`settings.json`) in the same folder if you apply any custom settings.

## Compiled Version

A compiled version is available (built with auto-py-to-exe), so you don’t need to run the Python code.

## Usage

### Adding and Removing Points
- **With `CTRL` Key**: 
  - **Left-click** on a square to add points.
  - **Right-click** on a square to remove points.
- **Without `CTRL` Key**: Left-clicking on a square will select that day’s date.

This is all you need to know to get started with Points Tracker!
