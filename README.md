# Enhanced ADB MCP Server for Flutter/Android Development

A comprehensive MCP server for controlling Android devices via ADB, specifically designed for Flutter development, UI testing, and visual QA workflows.

## Features

### 📱 Device Management
- List connected devices with details
- Get comprehensive device info (model, Android version, battery, etc.)
- Screen specifications with DP calculations

### 📸 Visual Capture
- Screenshots (base64 or file)
- Screen recording with start/stop control
- Capture with metadata for Figma comparison

### 🔍 UI Inspection
- Full UI hierarchy dump (XML)
- Find elements by text or resource ID
- Get all clickable elements with coordinates
- Extract all visible text for verification

### 🎯 Input & Interaction
- Tap, double-tap, long-press
- Swipe and scroll (up/down/to-text)
- Text input and clear
- Key events (HOME, BACK, ENTER, etc.)
- Tap elements by text or ID

### 📦 App Management
- Launch/stop/clear apps
- Install/uninstall APKs
- List packages with filtering
- Get current activity
- App info (version, install date, etc.)

### 🐛 Debugging & Logs
- Logcat with filtering (tag, level, package)
- Flutter-specific logs
- Crash logs extraction
- ANR traces

### ⚡ Performance Profiling
- Memory usage per app
- CPU monitoring
- GPU rendering info
- Frame stats for jank detection
- Battery statistics

### 🌐 Network Control
- Network info (WiFi status, IP)
- Toggle WiFi/Airplane mode
- Set/clear HTTP proxy

### ⚙️ Developer Options
- Animation scale (speed up tests)
- Show taps (for recordings)
- Show layout bounds
- Screen rotation control
- Change resolution/density

### ♿ Accessibility Testing
- Font scale adjustment
- TalkBack toggle
- High contrast mode
- Color inversion

### 📍 Emulator Features
- GPS location spoofing
- Simulate SMS/calls

## Prerequisites

1. **ADB installed** and in your PATH
   ```bash
   adb version
   ```

2. **Android device/emulator** connected with USB debugging enabled
   ```bash
   adb devices
   ```

3. **Python 3.10+** with `uv` (recommended) or `pip`

## Installation

```bash
cd adb-mcp-server

# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Configuration

### Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "adb": {
      "command": "uv",
      "args": ["--directory", "/path/to/adb-mcp-server", "run", "python", "server.py"]
    }
  }
}
```

### Cursor IDE

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "adb": {
      "command": "uv",
      "args": ["--directory", "/path/to/adb-mcp-server", "run", "python", "server.py"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add adb -- uv --directory /path/to/adb-mcp-server run python server.py
```

## Available Tools (60+)

### Device Management
| Tool | Description |
|------|-------------|
| `list_devices()` | List all connected devices |
| `get_device_info()` | Comprehensive device details |
| `get_screen_specs()` | Screen size, density, DP values |

### Visual Capture
| Tool | Description |
|------|-------------|
| `screenshot()` | Capture as base64 PNG |
| `screenshot_to_file(filename)` | Save screenshot to file |
| `start_screen_record(duration, filename)` | Start recording (max 180s) |
| `stop_screen_record()` | Stop recording |
| `pull_recordings(local_dir)` | Download recordings |
| `capture_screen_for_comparison(name)` | Screenshot with metadata |

### UI Inspection
| Tool | Description |
|------|-------------|
| `get_ui_hierarchy()` | Full UI tree as XML |
| `get_clickable_elements()` | All tappable elements with coordinates |
| `find_element_by_text(text)` | Find by text content |
| `find_element_by_id(resource_id)` | Find by resource ID |
| `get_all_text_on_screen()` | Extract all visible text |

### Input & Interaction
| Tool | Description |
|------|-------------|
| `tap(x, y)` | Tap at coordinates |
| `tap_element(text, resource_id)` | Tap by element identifier |
| `double_tap(x, y)` | Double tap |
| `long_press(x, y, duration)` | Long press |
| `swipe(x1, y1, x2, y2, duration)` | Swipe gesture |
| `scroll_down()` / `scroll_up()` | Scroll screen |
| `scroll_to_text(text)` | Scroll until text visible |
| `input_text(text)` | Type text |
| `clear_text_field(length)` | Clear current field |
| `press_key(keycode)` | Press any key |
| `press_back()` / `press_home()` | Navigation buttons |

### App Management
| Tool | Description |
|------|-------------|
| `get_current_activity()` | Current foreground app |
| `launch_app(package)` | Launch by package name |
| `launch_activity(package, activity)` | Launch specific activity |
| `force_stop_app(package)` | Force stop app |
| `clear_app_data(package)` | Clear app data |
| `list_packages(filter, include_system)` | List installed apps |
| `get_app_info(package)` | App details |
| `install_apk(path)` | Install APK |
| `uninstall_app(package)` | Uninstall app |

### Debugging & Logs
| Tool | Description |
|------|-------------|
| `get_logcat(lines, filter_tag, level)` | Get logs |
| `clear_logcat()` | Clear log buffer |
| `get_flutter_logs(lines)` | Flutter-specific logs |
| `get_crash_logs(package)` | Crash/exception logs |
| `get_anr_traces()` | ANR traces |

### Performance
| Tool | Description |
|------|-------------|
| `get_memory_info(package)` | Memory usage |
| `get_cpu_info()` | CPU usage |
| `get_battery_stats()` | Battery details |
| `get_gpu_info()` | GPU rendering info |
| `get_frame_stats(package)` | Frame timing stats |

### Network
| Tool | Description |
|------|-------------|
| `get_network_info()` | WiFi status, IP |
| `toggle_wifi(enable)` | Enable/disable WiFi |
| `toggle_airplane_mode(enable)` | Toggle airplane mode |
| `set_proxy(host, port)` | Set HTTP proxy |
| `clear_proxy()` | Clear proxy |

### Developer Options
| Tool | Description |
|------|-------------|
| `toggle_show_taps(enable)` | Visual tap feedback |
| `toggle_show_layout_bounds(enable)` | Show layout bounds |
| `set_animation_scale(scale)` | Animation speed (0-1) |
| `rotate_screen(orientation)` | portrait/landscape/auto |
| `change_screen_size(w, h)` | Override resolution |
| `reset_screen_size()` | Reset to default |
| `change_density(dpi)` | Override DPI |
| `reset_density()` | Reset to default |

### Accessibility
| Tool | Description |
|------|-------------|
| `set_font_scale(scale)` | System font size |
| `toggle_talkback(enable)` | Screen reader |
| `toggle_high_contrast(enable)` | High contrast text |
| `toggle_color_inversion(enable)` | Invert colors |

### Files & Shell
| Tool | Description |
|------|-------------|
| `push_file(local, remote)` | Copy to device |
| `pull_file(remote, local)` | Copy from device |
| `list_files(path)` | List directory |
| `read_file(path)` | Read text file |
| `shell_command(cmd)` | Run any shell command |
| `reboot_device(mode)` | Reboot device |

### Emulator Only
| Tool | Description |
|------|-------------|
| `set_location(lat, lng)` | Fake GPS location |
| `send_sms(number, message)` | Simulate SMS |
| `simulate_call(number)` | Simulate incoming call |

## Example Prompts

### Basic Usage
- "Take a screenshot of my phone"
- "What's the current screen resolution and density?"
- "List all installed apps containing 'flutter'"
- "What's currently on screen? Get all the text"

### UI Testing
- "Find the login button and tap it"
- "Scroll down until you find 'Settings'"
- "Get all clickable elements and their positions"
- "Type 'test@email.com' into the current field"

### Debugging
- "Show me the last 50 Flutter logs"
- "Are there any crash logs for my app?"
- "What's the memory usage of com.myapp?"

### Visual QA
- "Capture this screen for comparison with Figma"
- "Take a screenshot and tell me about the UI structure"
- "Set the font scale to 1.3 and take a screenshot for accessibility testing"

### Performance Testing
- "Set animation scale to 0 and run through the app"
- "Get frame stats for my app - is there any jank?"
- "What's the GPU rendering performance?"

### Device Simulation
- "Change the screen to 1080x1920 to simulate a smaller phone"
- "Rotate to landscape mode"
- "Set location to San Francisco (37.7749, -122.4194)"

## Extending

Add new tools easily:

```python
@mcp.tool()
def my_custom_tool(param: str, device_serial: str | None = None) -> str:
    """Description shown to AI"""
    return run_adb(["shell", "your-command", param], device_serial)
```

## Tips for Flutter Development

1. **Speed up tests**: Use `set_animation_scale(0)` to disable animations
2. **Visual QA**: Use `capture_screen_for_comparison()` with Figma MCP
3. **Debug logs**: `get_flutter_logs()` filters Flutter-specific output
4. **Hot reload**: Keep `flutter run` terminal open, use device for interaction
5. **Responsive testing**: Use `change_screen_size()` and `change_density()`

## License

MIT
