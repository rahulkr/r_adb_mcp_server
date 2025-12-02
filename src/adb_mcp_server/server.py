#!/usr/bin/env python3
"""
Enhanced ADB MCP Server for Flutter/Android Development
Comprehensive tools for UI testing, debugging, and visual QA
"""

import subprocess
import base64
import json
import re
import time
import tempfile
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("adb-dev-server")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_adb(args: list[str], device_serial: str | None = None, timeout: int = 30) -> str:
    """Run an ADB command and return output"""
    cmd = ["adb"]
    if device_serial:
        cmd.extend(["-s", device_serial])
    cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0 and result.stderr:
            return f"Error: {result.stderr}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {str(e)}"


def run_adb_binary(args: list[str], device_serial: str | None = None) -> bytes:
    """Run an ADB command and return binary output"""
    cmd = ["adb"]
    if device_serial:
        cmd.extend(["-s", device_serial])
    cmd.extend(args)
    
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout


# ============================================================================
# DEVICE MANAGEMENT
# ============================================================================

@mcp.tool()
def list_devices() -> str:
    """List all connected Android devices with details"""
    return run_adb(["devices", "-l"])


@mcp.tool()
def get_device_info(device_serial: str | None = None) -> dict:
    """Get comprehensive device information"""
    props = [
        ("model", "ro.product.model"),
        ("manufacturer", "ro.product.manufacturer"),
        ("device", "ro.product.device"),
        ("android_version", "ro.build.version.release"),
        ("sdk_version", "ro.build.version.sdk"),
        ("build_id", "ro.build.id"),
        ("hardware", "ro.hardware"),
        ("serial", "ro.serialno"),
        ("locale", "persist.sys.locale"),
        ("timezone", "persist.sys.timezone"),
    ]
    
    info = {}
    for name, prop in props:
        info[name] = run_adb(["shell", "getprop", prop], device_serial).strip()
    
    # Add screen info
    info["screen_size"] = run_adb(["shell", "wm", "size"], device_serial).strip()
    info["screen_density"] = run_adb(["shell", "wm", "density"], device_serial).strip()
    
    # Battery info
    battery = run_adb(["shell", "dumpsys", "battery"], device_serial)
    for line in battery.split('\n'):
        if 'level:' in line:
            info["battery_level"] = line.split(':')[1].strip() + "%"
        if 'status:' in line:
            status_map = {'2': 'Charging', '3': 'Discharging', '4': 'Not charging', '5': 'Full'}
            status = line.split(':')[1].strip()
            info["battery_status"] = status_map.get(status, status)
    
    return info


@mcp.tool()
def get_screen_specs(device_serial: str | None = None) -> dict:
    """Get detailed screen specifications - useful for responsive design"""
    size_output = run_adb(["shell", "wm", "size"], device_serial)
    density_output = run_adb(["shell", "wm", "density"], device_serial)
    
    # Parse physical size
    size_match = re.search(r'Physical size: (\d+)x(\d+)', size_output)
    override_match = re.search(r'Override size: (\d+)x(\d+)', size_output)
    
    width, height = 0, 0
    if override_match:
        width, height = int(override_match.group(1)), int(override_match.group(2))
    elif size_match:
        width, height = int(size_match.group(1)), int(size_match.group(2))
    
    # Parse density
    density = 0
    density_match = re.search(r'Physical density: (\d+)', density_output)
    if density_match:
        density = int(density_match.group(1))
    
    # Calculate useful metrics
    dp_width = (width / density) * 160 if density else 0
    dp_height = (height / density) * 160 if density else 0
    
    return {
        "width_px": width,
        "height_px": height,
        "density_dpi": density,
        "width_dp": round(dp_width, 1),
        "height_dp": round(dp_height, 1),
        "aspect_ratio": f"{width}:{height}",
        "density_bucket": get_density_bucket(density)
    }


def get_density_bucket(dpi: int) -> str:
    """Map DPI to Android density bucket"""
    if dpi <= 120: return "ldpi"
    if dpi <= 160: return "mdpi"
    if dpi <= 240: return "hdpi"
    if dpi <= 320: return "xhdpi"
    if dpi <= 480: return "xxhdpi"
    return "xxxhdpi"


# ============================================================================
# SCREENSHOTS & VISUAL CAPTURE
# ============================================================================

@mcp.tool()
def screenshot(device_serial: str | None = None) -> dict:
    """
    Take a screenshot of the device screen.
    Returns base64 encoded PNG image that can be viewed directly.
    """
    img_data = run_adb_binary(["exec-out", "screencap", "-p"], device_serial)
    
    if not img_data or len(img_data) < 100:
        return {"error": "Failed to capture screenshot"}
    
    img_base64 = base64.b64encode(img_data).decode('utf-8')
    return {
        "type": "image",
        "format": "png",
        "size_bytes": len(img_data),
        "data": img_base64
    }


@mcp.tool()
def screenshot_to_file(
    filename: str = "screenshot.png",
    device_serial: str | None = None
) -> str:
    """Save screenshot to a local file"""
    img_data = run_adb_binary(["exec-out", "screencap", "-p"], device_serial)
    
    if not img_data or len(img_data) < 100:
        return "Error: Failed to capture screenshot"
    
    with open(filename, 'wb') as f:
        f.write(img_data)
    
    return f"Screenshot saved to {filename} ({len(img_data)} bytes)"


@mcp.tool()
def start_screen_record(
    duration_seconds: int = 30,
    filename: str = "recording",
    device_serial: str | None = None
) -> str:
    """
    Start recording the screen. Max duration is 180 seconds.
    Recording runs in background - use stop_screen_record to stop early.
    """
    duration = min(duration_seconds, 180)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_path = f"/sdcard/{filename}_{timestamp}.mp4"
    
    # Start recording in background
    run_adb([
        "shell", "nohup", "screenrecord",
        "--time-limit", str(duration),
        remote_path, "&"
    ], device_serial)
    
    return f"Recording started: {remote_path} (max {duration}s). Use stop_screen_record to stop early."


@mcp.tool()
def stop_screen_record(device_serial: str | None = None) -> str:
    """Stop any ongoing screen recording"""
    run_adb(["shell", "pkill", "-l", "SIGINT", "screenrecord"], device_serial)
    return "Screen recording stopped. Files are saved on device at /sdcard/"


@mcp.tool()
def pull_recordings(
    local_dir: str = "./recordings",
    device_serial: str | None = None
) -> str:
    """Pull all screen recordings from device to local directory"""
    os.makedirs(local_dir, exist_ok=True)
    
    # List recordings
    files = run_adb(["shell", "ls", "/sdcard/*.mp4"], device_serial)
    if "No such file" in files or not files.strip():
        return "No recordings found on device"
    
    pulled = []
    for f in files.strip().split('\n'):
        f = f.strip()
        if f.endswith('.mp4'):
            local_path = os.path.join(local_dir, os.path.basename(f))
            run_adb(["pull", f, local_path], device_serial)
            pulled.append(local_path)
    
    return f"Pulled {len(pulled)} recordings to {local_dir}: {pulled}"


# ============================================================================
# UI INSPECTION & ANALYSIS
# ============================================================================

@mcp.tool()
def get_ui_hierarchy(device_serial: str | None = None) -> str:
    """
    Dump the complete UI hierarchy as XML.
    Shows all visible elements, their properties, bounds, and content descriptions.
    """
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"], device_serial)
    output = run_adb(["shell", "cat", "/sdcard/ui_dump.xml"], device_serial)
    run_adb(["shell", "rm", "/sdcard/ui_dump.xml"], device_serial)
    return output


@mcp.tool()
def get_clickable_elements(device_serial: str | None = None) -> list[dict]:
    """
    Get all clickable/interactive elements on screen with their coordinates.
    Perfect for understanding what can be tapped.
    """
    xml = get_ui_hierarchy(device_serial)
    elements = []
    
    # Parse clickable elements
    pattern = r'<node[^>]*clickable="true"[^>]*>'
    for match in re.finditer(pattern, xml):
        node = match.group()
        
        element = {}
        
        # Extract text
        text_match = re.search(r'text="([^"]*)"', node)
        if text_match:
            element['text'] = text_match.group(1)
        
        # Extract content-desc
        desc_match = re.search(r'content-desc="([^"]*)"', node)
        if desc_match:
            element['content_desc'] = desc_match.group(1)
        
        # Extract resource-id
        id_match = re.search(r'resource-id="([^"]*)"', node)
        if id_match:
            element['resource_id'] = id_match.group(1)
        
        # Extract bounds and calculate center
        bounds_match = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
        if bounds_match:
            x1, y1 = int(bounds_match.group(1)), int(bounds_match.group(2))
            x2, y2 = int(bounds_match.group(3)), int(bounds_match.group(4))
            element['bounds'] = {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
            element['center'] = {'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2}
            element['size'] = {'width': x2 - x1, 'height': y2 - y1}
        
        # Extract class
        class_match = re.search(r'class="([^"]*)"', node)
        if class_match:
            element['class'] = class_match.group(1)
        
        if element:
            elements.append(element)
    
    return elements


@mcp.tool()
def find_element_by_text(
    text: str, 
    partial_match: bool = True,
    device_serial: str | None = None
) -> list[dict]:
    """
    Find UI elements containing specific text.
    Returns element details including tap coordinates.
    """
    xml = get_ui_hierarchy(device_serial)
    elements = []
    
    for match in re.finditer(r'<node[^>]*>', xml):
        node = match.group()
        
        text_match = re.search(r'text="([^"]*)"', node)
        desc_match = re.search(r'content-desc="([^"]*)"', node)
        
        found_text = text_match.group(1) if text_match else ""
        found_desc = desc_match.group(1) if desc_match else ""
        
        # Check if text matches
        matches = False
        if partial_match:
            matches = text.lower() in found_text.lower() or text.lower() in found_desc.lower()
        else:
            matches = text == found_text or text == found_desc
        
        if matches:
            element = {'text': found_text, 'content_desc': found_desc}
            
            bounds_match = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
            if bounds_match:
                x1, y1 = int(bounds_match.group(1)), int(bounds_match.group(2))
                x2, y2 = int(bounds_match.group(3)), int(bounds_match.group(4))
                element['center'] = {'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2}
                element['bounds'] = {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
            
            elements.append(element)
    
    return elements


@mcp.tool()
def find_element_by_id(
    resource_id: str,
    device_serial: str | None = None
) -> dict | None:
    """
    Find a UI element by its resource ID.
    Returns element details including tap coordinates.
    """
    xml = get_ui_hierarchy(device_serial)
    
    # Match partial resource ID (e.g., "button_submit" matches "com.app:id/button_submit")
    for match in re.finditer(r'<node[^>]*>', xml):
        node = match.group()
        
        id_match = re.search(r'resource-id="([^"]*)"', node)
        if id_match and resource_id in id_match.group(1):
            element = {'resource_id': id_match.group(1)}
            
            text_match = re.search(r'text="([^"]*)"', node)
            if text_match:
                element['text'] = text_match.group(1)
            
            bounds_match = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
            if bounds_match:
                x1, y1 = int(bounds_match.group(1)), int(bounds_match.group(2))
                x2, y2 = int(bounds_match.group(3)), int(bounds_match.group(4))
                element['center'] = {'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2}
                element['bounds'] = {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
            
            return element
    
    return None


# ============================================================================
# INPUT & INTERACTION
# ============================================================================

@mcp.tool()
def tap(x: int, y: int, device_serial: str | None = None) -> str:
    """Tap at screen coordinates (x, y)"""
    return run_adb(["shell", "input", "tap", str(x), str(y)], device_serial)


@mcp.tool()
def tap_element(
    text: str | None = None,
    resource_id: str | None = None,
    device_serial: str | None = None
) -> str:
    """
    Tap on an element by text or resource ID.
    More reliable than raw coordinates.
    """
    element = None
    
    if text:
        elements = find_element_by_text(text, partial_match=True, device_serial=device_serial)
        if elements:
            element = elements[0]
    elif resource_id:
        element = find_element_by_id(resource_id, device_serial=device_serial)
    
    if not element or 'center' not in element:
        return f"Element not found: text='{text}', resource_id='{resource_id}'"
    
    x, y = element['center']['x'], element['center']['y']
    run_adb(["shell", "input", "tap", str(x), str(y)], device_serial)
    return f"Tapped element at ({x}, {y})"


@mcp.tool()
def long_press(x: int, y: int, duration_ms: int = 1000, device_serial: str | None = None) -> str:
    """Long press at coordinates for specified duration"""
    return run_adb([
        "shell", "input", "swipe", 
        str(x), str(y), str(x), str(y), str(duration_ms)
    ], device_serial)


@mcp.tool()
def double_tap(x: int, y: int, device_serial: str | None = None) -> str:
    """Double tap at coordinates"""
    run_adb(["shell", "input", "tap", str(x), str(y)], device_serial)
    time.sleep(0.1)
    run_adb(["shell", "input", "tap", str(x), str(y)], device_serial)
    return f"Double tapped at ({x}, {y})"


@mcp.tool()
def swipe(
    start_x: int, 
    start_y: int, 
    end_x: int, 
    end_y: int, 
    duration_ms: int = 300,
    device_serial: str | None = None
) -> str:
    """Swipe from start to end coordinates"""
    return run_adb([
        "shell", "input", "swipe",
        str(start_x), str(start_y),
        str(end_x), str(end_y),
        str(duration_ms)
    ], device_serial)


@mcp.tool()
def scroll_down(device_serial: str | None = None) -> str:
    """Scroll down on the current screen"""
    specs = get_screen_specs(device_serial)
    center_x = specs['width_px'] // 2
    start_y = int(specs['height_px'] * 0.7)
    end_y = int(specs['height_px'] * 0.3)
    return swipe(center_x, start_y, center_x, end_y, 300, device_serial)


@mcp.tool()
def scroll_up(device_serial: str | None = None) -> str:
    """Scroll up on the current screen"""
    specs = get_screen_specs(device_serial)
    center_x = specs['width_px'] // 2
    start_y = int(specs['height_px'] * 0.3)
    end_y = int(specs['height_px'] * 0.7)
    return swipe(center_x, start_y, center_x, end_y, 300, device_serial)


@mcp.tool()
def scroll_to_text(
    text: str, 
    max_scrolls: int = 10,
    device_serial: str | None = None
) -> str:
    """Scroll until text is found on screen"""
    for i in range(max_scrolls):
        elements = find_element_by_text(text, partial_match=True, device_serial=device_serial)
        if elements:
            return f"Found '{text}' after {i} scrolls at {elements[0].get('center', 'unknown')}"
        scroll_down(device_serial)
        time.sleep(0.5)
    return f"Text '{text}' not found after {max_scrolls} scrolls"


@mcp.tool()
def input_text(text: str, device_serial: str | None = None) -> str:
    """Type text into the currently focused field"""
    # Escape special characters for shell
    escaped = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
    return run_adb(["shell", "input", "text", escaped], device_serial)


@mcp.tool()
def clear_text_field(length: int = 50, device_serial: str | None = None) -> str:
    """Clear text in current field by sending delete keys"""
    # Move to end and delete backwards
    run_adb(["shell", "input", "keyevent", "KEYCODE_MOVE_END"], device_serial)
    for _ in range(length):
        run_adb(["shell", "input", "keyevent", "KEYCODE_DEL"], device_serial)
    return f"Cleared up to {length} characters"


@mcp.tool()
def press_key(keycode: str, device_serial: str | None = None) -> str:
    """
    Press a key by keycode name or number.
    
    Common keycodes:
    - HOME (3), BACK (4), CALL (5), ENDCALL (6)
    - VOLUME_UP (24), VOLUME_DOWN (25), POWER (26)
    - CAMERA (27), ENTER (66), DEL/BACKSPACE (67)
    - TAB (61), SPACE (62), MENU (82)
    - SEARCH (84), MEDIA_PLAY_PAUSE (85)
    - PAGE_UP (92), PAGE_DOWN (93)
    """
    # Handle common names
    key_map = {
        'HOME': '3', 'BACK': '4', 'ENTER': '66', 'DELETE': '67', 'DEL': '67',
        'TAB': '61', 'SPACE': '62', 'MENU': '82', 'SEARCH': '84',
        'VOLUME_UP': '24', 'VOLUME_DOWN': '25', 'POWER': '26',
        'PAGE_UP': '92', 'PAGE_DOWN': '93', 'ESCAPE': '111', 'ESC': '111'
    }
    
    key = key_map.get(keycode.upper(), keycode)
    return run_adb(["shell", "input", "keyevent", key], device_serial)


@mcp.tool()
def press_back(device_serial: str | None = None) -> str:
    """Press the back button"""
    return press_key("BACK", device_serial)


@mcp.tool()
def press_home(device_serial: str | None = None) -> str:
    """Press the home button"""
    return press_key("HOME", device_serial)


@mcp.tool()
def press_recent_apps(device_serial: str | None = None) -> str:
    """Open recent apps / app switcher"""
    return run_adb(["shell", "input", "keyevent", "KEYCODE_APP_SWITCH"], device_serial)


# ============================================================================
# APP MANAGEMENT
# ============================================================================

@mcp.tool()
def get_current_activity(device_serial: str | None = None) -> dict:
    """Get the currently focused app and activity"""
    output = run_adb(["shell", "dumpsys", "activity", "activities"], device_serial)
    
    result = {
        "package": None,
        "activity": None,
        "full_component": None
    }
    
    # Look for ResumedActivity or mFocusedActivity
    for line in output.split('\n'):
        if 'ResumedActivity' in line or 'mFocusedActivity' in line:
            match = re.search(r'([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)', line)
            if match:
                result['package'] = match.group(1)
                result['activity'] = match.group(2)
                result['full_component'] = f"{match.group(1)}/{match.group(2)}"
            break
    
    return result


@mcp.tool()
def launch_app(package_name: str, device_serial: str | None = None) -> str:
    """Launch an app by package name"""
    return run_adb([
        "shell", "monkey", "-p", package_name,
        "-c", "android.intent.category.LAUNCHER", "1"
    ], device_serial)


@mcp.tool()
def launch_activity(
    package_name: str, 
    activity_name: str,
    device_serial: str | None = None
) -> str:
    """Launch a specific activity"""
    component = f"{package_name}/{activity_name}"
    return run_adb(["shell", "am", "start", "-n", component], device_serial)


@mcp.tool()
def force_stop_app(package_name: str, device_serial: str | None = None) -> str:
    """Force stop an app"""
    return run_adb(["shell", "am", "force-stop", package_name], device_serial)


@mcp.tool()
def clear_app_data(package_name: str, device_serial: str | None = None) -> str:
    """Clear all data for an app (like fresh install)"""
    return run_adb(["shell", "pm", "clear", package_name], device_serial)


@mcp.tool()
def list_packages(
    filter_text: str = "", 
    include_system: bool = False,
    device_serial: str | None = None
) -> list[str]:
    """List installed packages, optionally filtered"""
    args = ["shell", "pm", "list", "packages"]
    if not include_system:
        args.append("-3")  # Third-party only
    
    output = run_adb(args, device_serial)
    packages = [line.replace("package:", "").strip() 
                for line in output.split('\n') if line.strip()]
    
    if filter_text:
        packages = [p for p in packages if filter_text.lower() in p.lower()]
    
    return sorted(packages)


@mcp.tool()
def get_app_info(package_name: str, device_serial: str | None = None) -> dict:
    """Get detailed information about an installed app"""
    dump = run_adb(["shell", "dumpsys", "package", package_name], device_serial)
    
    info = {"package": package_name}
    
    # Extract version
    version_match = re.search(r'versionName=(\S+)', dump)
    if version_match:
        info['version_name'] = version_match.group(1)
    
    version_code_match = re.search(r'versionCode=(\d+)', dump)
    if version_code_match:
        info['version_code'] = version_code_match.group(1)
    
    # First install time
    install_match = re.search(r'firstInstallTime=(.+)', dump)
    if install_match:
        info['first_install'] = install_match.group(1).strip()
    
    # Last update time
    update_match = re.search(r'lastUpdateTime=(.+)', dump)
    if update_match:
        info['last_update'] = update_match.group(1).strip()
    
    # Target SDK
    sdk_match = re.search(r'targetSdk=(\d+)', dump)
    if sdk_match:
        info['target_sdk'] = sdk_match.group(1)
    
    return info


@mcp.tool()
def install_apk(apk_path: str, device_serial: str | None = None) -> str:
    """Install an APK file"""
    return run_adb(["install", "-r", apk_path], device_serial)


@mcp.tool()
def uninstall_app(package_name: str, device_serial: str | None = None) -> str:
    """Uninstall an app"""
    return run_adb(["uninstall", package_name], device_serial)


# ============================================================================
# DEBUGGING & LOGS
# ============================================================================

@mcp.tool()
def get_logcat(
    lines: int = 100,
    filter_tag: str | None = None,
    filter_level: str = "V",
    package_name: str | None = None,
    device_serial: str | None = None
) -> str:
    """
    Get logcat output.
    
    filter_level: V (Verbose), D (Debug), I (Info), W (Warning), E (Error), F (Fatal)
    """
    args = ["shell", "logcat", "-d", "-t", str(lines)]
    
    if filter_tag:
        args.extend(["-s", f"{filter_tag}:{filter_level}"])
    
    output = run_adb(args, device_serial)
    
    # Filter by package if specified
    if package_name:
        lines_list = output.split('\n')
        output = '\n'.join(l for l in lines_list if package_name in l)
    
    return output


@mcp.tool()
def clear_logcat(device_serial: str | None = None) -> str:
    """Clear the logcat buffer"""
    return run_adb(["shell", "logcat", "-c"], device_serial)


@mcp.tool()
def get_flutter_logs(lines: int = 100, device_serial: str | None = None) -> str:
    """Get Flutter-specific logs"""
    output = run_adb(["shell", "logcat", "-d", "-t", str(lines)], device_serial)
    
    # Filter for Flutter-related logs
    flutter_keywords = ['flutter', 'dart', 'FlutterEngine', 'FlutterActivity']
    log_lines = output.split('\n')
    flutter_lines = [l for l in log_lines 
                     if any(kw.lower() in l.lower() for kw in flutter_keywords)]
    
    return '\n'.join(flutter_lines) if flutter_lines else "No Flutter logs found"


@mcp.tool()
def get_crash_logs(package_name: str | None = None, device_serial: str | None = None) -> str:
    """Get crash/exception logs"""
    output = run_adb(["shell", "logcat", "-d", "-t", "500"], device_serial)
    
    # Look for crash indicators
    crash_keywords = ['FATAL EXCEPTION', 'AndroidRuntime', 'crash', 'Exception', 'Error']
    log_lines = output.split('\n')
    
    crash_lines = []
    in_crash = False
    
    for line in log_lines:
        if any(kw in line for kw in crash_keywords):
            in_crash = True
        if in_crash:
            crash_lines.append(line)
            if line.strip() == '' or len(crash_lines) > 50:
                in_crash = False
    
    if package_name:
        crash_lines = [l for l in crash_lines if package_name in l or 'at ' in l]
    
    return '\n'.join(crash_lines) if crash_lines else "No crash logs found"


@mcp.tool()
def get_anr_traces(device_serial: str | None = None) -> str:
    """Get ANR (Application Not Responding) traces"""
    return run_adb(["shell", "cat", "/data/anr/traces.txt"], device_serial)


# ============================================================================
# PERFORMANCE & PROFILING
# ============================================================================

@mcp.tool()
def get_memory_info(package_name: str | None = None, device_serial: str | None = None) -> str:
    """Get memory usage information"""
    if package_name:
        return run_adb(["shell", "dumpsys", "meminfo", package_name], device_serial)
    return run_adb(["shell", "cat", "/proc/meminfo"], device_serial)


@mcp.tool()
def get_cpu_info(device_serial: str | None = None) -> str:
    """Get CPU usage information"""
    return run_adb(["shell", "top", "-n", "1", "-b"], device_serial)


@mcp.tool()
def get_battery_stats(device_serial: str | None = None) -> dict:
    """Get detailed battery statistics"""
    output = run_adb(["shell", "dumpsys", "battery"], device_serial)
    
    stats = {}
    for line in output.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            stats[key.strip()] = value.strip()
    
    return stats


@mcp.tool()
def get_gpu_info(device_serial: str | None = None) -> str:
    """Get GPU rendering information - useful for performance debugging"""
    return run_adb(["shell", "dumpsys", "gfxinfo"], device_serial)


@mcp.tool()
def get_frame_stats(package_name: str, device_serial: str | None = None) -> str:
    """Get frame rendering stats for an app - useful for detecting jank"""
    return run_adb(["shell", "dumpsys", "gfxinfo", package_name, "framestats"], device_serial)


# ============================================================================
# NETWORK & CONNECTIVITY
# ============================================================================

@mcp.tool()
def get_network_info(device_serial: str | None = None) -> dict:
    """Get network connectivity information"""
    wifi = run_adb(["shell", "dumpsys", "wifi"], device_serial)
    
    info = {
        "wifi_enabled": "Wi-Fi is enabled" in wifi,
        "connected": "CONNECTED" in wifi
    }
    
    # Get IP address
    ip_output = run_adb(["shell", "ip", "addr", "show", "wlan0"], device_serial)
    ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_output)
    if ip_match:
        info['ip_address'] = ip_match.group(1)
    
    return info


@mcp.tool()
def toggle_wifi(enable: bool, device_serial: str | None = None) -> str:
    """Enable or disable WiFi"""
    state = "enable" if enable else "disable"
    return run_adb(["shell", "svc", "wifi", state], device_serial)


@mcp.tool()
def toggle_airplane_mode(enable: bool, device_serial: str | None = None) -> str:
    """Enable or disable airplane mode"""
    value = "1" if enable else "0"
    run_adb(["shell", "settings", "put", "global", "airplane_mode_on", value], device_serial)
    # Broadcast the change
    intent = "android.intent.action.AIRPLANE_MODE"
    run_adb(["shell", "am", "broadcast", "-a", intent], device_serial)
    return f"Airplane mode {'enabled' if enable else 'disabled'}"


@mcp.tool()
def set_proxy(host: str, port: int, device_serial: str | None = None) -> str:
    """Set HTTP proxy for the device - useful for debugging network requests"""
    return run_adb([
        "shell", "settings", "put", "global", 
        "http_proxy", f"{host}:{port}"
    ], device_serial)


@mcp.tool()
def clear_proxy(device_serial: str | None = None) -> str:
    """Clear HTTP proxy settings"""
    return run_adb(["shell", "settings", "put", "global", "http_proxy", ":0"], device_serial)


# ============================================================================
# DEVELOPER OPTIONS & SETTINGS
# ============================================================================

@mcp.tool()
def toggle_show_taps(enable: bool, device_serial: str | None = None) -> str:
    """Show visual feedback for taps - useful for demos/recordings"""
    value = "1" if enable else "0"
    return run_adb(["shell", "settings", "put", "system", "show_touches", value], device_serial)


@mcp.tool()
def toggle_show_layout_bounds(enable: bool, device_serial: str | None = None) -> str:
    """Show layout bounds for all views - great for debugging layouts"""
    value = "true" if enable else "false"
    return run_adb([
        "shell", "setprop", "debug.layout", value
    ], device_serial)


@mcp.tool()
def set_animation_scale(scale: float = 1.0, device_serial: str | None = None) -> str:
    """
    Set animation scale (0 = off, 1 = normal, 0.5 = fast).
    Useful for speeding up UI tests.
    """
    scale_str = str(scale)
    run_adb(["shell", "settings", "put", "global", "window_animation_scale", scale_str], device_serial)
    run_adb(["shell", "settings", "put", "global", "transition_animation_scale", scale_str], device_serial)
    run_adb(["shell", "settings", "put", "global", "animator_duration_scale", scale_str], device_serial)
    return f"Animation scale set to {scale}"


@mcp.tool()
def rotate_screen(orientation: str = "portrait", device_serial: str | None = None) -> str:
    """
    Rotate screen orientation.
    orientation: 'portrait', 'landscape', 'reverse_portrait', 'reverse_landscape', or 'auto'
    """
    orientations = {
        'auto': ('0', 'user'),
        'portrait': ('1', '0'),
        'landscape': ('1', '1'),
        'reverse_portrait': ('1', '2'),
        'reverse_landscape': ('1', '3')
    }
    
    if orientation not in orientations:
        return f"Invalid orientation. Use: {list(orientations.keys())}"
    
    accel_rotation, user_rotation = orientations[orientation]
    
    if orientation == 'auto':
        run_adb(["shell", "settings", "put", "system", "accelerometer_rotation", "1"], device_serial)
    else:
        run_adb(["shell", "settings", "put", "system", "accelerometer_rotation", "0"], device_serial)
        run_adb(["shell", "settings", "put", "system", "user_rotation", user_rotation], device_serial)
    
    return f"Screen rotation set to {orientation}"


@mcp.tool()
def change_screen_size(width: int, height: int, device_serial: str | None = None) -> str:
    """Change screen resolution - useful for testing different screen sizes"""
    return run_adb(["shell", "wm", "size", f"{width}x{height}"], device_serial)


@mcp.tool()
def reset_screen_size(device_serial: str | None = None) -> str:
    """Reset screen size to physical default"""
    return run_adb(["shell", "wm", "size", "reset"], device_serial)


@mcp.tool()
def change_density(dpi: int, device_serial: str | None = None) -> str:
    """Change screen density - useful for testing different DPI"""
    return run_adb(["shell", "wm", "density", str(dpi)], device_serial)


@mcp.tool()
def reset_density(device_serial: str | None = None) -> str:
    """Reset density to physical default"""
    return run_adb(["shell", "wm", "density", "reset"], device_serial)


# ============================================================================
# FILE OPERATIONS
# ============================================================================

@mcp.tool()
def push_file(local_path: str, remote_path: str, device_serial: str | None = None) -> str:
    """Push a file to the device"""
    return run_adb(["push", local_path, remote_path], device_serial)


@mcp.tool()
def pull_file(remote_path: str, local_path: str, device_serial: str | None = None) -> str:
    """Pull a file from the device"""
    return run_adb(["pull", remote_path, local_path], device_serial)


@mcp.tool()
def list_files(remote_path: str = "/sdcard/", device_serial: str | None = None) -> str:
    """List files in a directory on the device"""
    return run_adb(["shell", "ls", "-la", remote_path], device_serial)


@mcp.tool()
def read_file(remote_path: str, device_serial: str | None = None) -> str:
    """Read a text file from the device"""
    return run_adb(["shell", "cat", remote_path], device_serial)


# ============================================================================
# SHELL & GENERAL
# ============================================================================

@mcp.tool()
def shell_command(command: str, device_serial: str | None = None) -> str:
    """
    Execute an arbitrary ADB shell command.
    Use with caution - this gives full shell access.
    """
    return run_adb(["shell", command], device_serial)


@mcp.tool()
def reboot_device(mode: str = "normal", device_serial: str | None = None) -> str:
    """
    Reboot the device.
    mode: 'normal', 'bootloader', 'recovery'
    """
    if mode == "normal":
        return run_adb(["reboot"], device_serial)
    elif mode in ["bootloader", "recovery"]:
        return run_adb(["reboot", mode], device_serial)
    return "Invalid mode. Use: normal, bootloader, recovery"


# ============================================================================
# FLUTTER-SPECIFIC TOOLS
# ============================================================================

@mcp.tool()
def get_flutter_performance_overlay(
    package_name: str,
    device_serial: str | None = None
) -> str:
    """Get Flutter rendering performance info"""
    output = run_adb([
        "shell", "dumpsys", "gfxinfo", package_name, "framestats"
    ], device_serial)
    return output


@mcp.tool()
def check_flutter_app_running(device_serial: str | None = None) -> dict:
    """Check if a Flutter app is currently in foreground"""
    activity = get_current_activity(device_serial)
    
    # Check if it's a Flutter activity
    is_flutter = False
    if activity.get('activity'):
        is_flutter = 'flutter' in activity['activity'].lower()
    
    # Also check for Flutter in logcat
    logs = run_adb(["shell", "logcat", "-d", "-t", "20", "-s", "flutter"], device_serial)
    has_recent_flutter_logs = len(logs.strip()) > 0
    
    return {
        "current_activity": activity,
        "likely_flutter_app": is_flutter or has_recent_flutter_logs,
        "recent_flutter_logs": has_recent_flutter_logs
    }


# ============================================================================
# ACCESSIBILITY & QA TESTING
# ============================================================================

@mcp.tool()
def get_accessibility_info(device_serial: str | None = None) -> str:
    """Get accessibility service information - useful for a11y testing"""
    return run_adb(["shell", "dumpsys", "accessibility"], device_serial)


@mcp.tool()
def set_font_scale(scale: float = 1.0, device_serial: str | None = None) -> str:
    """
    Set system font scale (0.85 = small, 1.0 = normal, 1.15 = large, 1.3 = largest).
    Useful for testing font scaling accessibility.
    """
    return run_adb([
        "shell", "settings", "put", "system", "font_scale", str(scale)
    ], device_serial)


@mcp.tool()
def toggle_talkback(enable: bool, device_serial: str | None = None) -> str:
    """Enable or disable TalkBack accessibility service"""
    service = "com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService"
    if enable:
        return run_adb([
            "shell", "settings", "put", "secure", 
            "enabled_accessibility_services", service
        ], device_serial)
    else:
        return run_adb([
            "shell", "settings", "put", "secure",
            "enabled_accessibility_services", ""
        ], device_serial)


@mcp.tool()
def toggle_high_contrast(enable: bool, device_serial: str | None = None) -> str:
    """Enable or disable high contrast text"""
    value = "1" if enable else "0"
    return run_adb([
        "shell", "settings", "put", "secure", "high_text_contrast_enabled", value
    ], device_serial)


@mcp.tool()
def toggle_color_inversion(enable: bool, device_serial: str | None = None) -> str:
    """Enable or disable display color inversion"""
    value = "1" if enable else "0"
    return run_adb([
        "shell", "settings", "put", "secure", "accessibility_display_inversion_enabled", value
    ], device_serial)


# ============================================================================
# EMULATOR SPECIFIC
# ============================================================================

@mcp.tool()
def set_location(
    latitude: float, 
    longitude: float,
    device_serial: str | None = None
) -> str:
    """Set GPS location (works on emulators)"""
    return run_adb([
        "emu", "geo", "fix", str(longitude), str(latitude)
    ], device_serial)


@mcp.tool()
def send_sms(
    phone_number: str,
    message: str,
    device_serial: str | None = None
) -> str:
    """Send an SMS to the emulator (emulator only)"""
    return run_adb([
        "emu", "sms", "send", phone_number, message
    ], device_serial)


@mcp.tool()
def simulate_call(
    phone_number: str,
    device_serial: str | None = None
) -> str:
    """Simulate incoming call (emulator only)"""
    return run_adb(["emu", "gsm", "call", phone_number], device_serial)


# ============================================================================
# VISUAL QA & COMPARISON HELPERS
# ============================================================================

@mcp.tool()
def capture_screen_for_comparison(
    screen_name: str,
    output_dir: str = "./screenshots",
    device_serial: str | None = None
) -> dict:
    """
    Capture screenshot with metadata for visual comparison.
    Saves PNG and returns info for comparing with Figma designs.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get device specs
    specs = get_screen_specs(device_serial)
    activity = get_current_activity(device_serial)
    
    # Capture screenshot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{screen_name}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    
    img_data = run_adb_binary(["exec-out", "screencap", "-p"], device_serial)
    with open(filepath, 'wb') as f:
        f.write(img_data)
    
    return {
        "filepath": filepath,
        "filename": filename,
        "screen_name": screen_name,
        "timestamp": timestamp,
        "device_specs": specs,
        "current_activity": activity,
        "size_bytes": len(img_data),
        "base64": base64.b64encode(img_data).decode('utf-8')
    }


@mcp.tool()
def get_all_text_on_screen(device_serial: str | None = None) -> list[dict]:
    """
    Extract all visible text from current screen.
    Useful for verifying text content matches designs.
    """
    xml = get_ui_hierarchy(device_serial)
    texts = []
    
    for match in re.finditer(r'<node[^>]*>', xml):
        node = match.group()
        
        text_match = re.search(r'text="([^"]*)"', node)
        if text_match and text_match.group(1).strip():
            text_info = {'text': text_match.group(1)}
            
            bounds_match = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
            if bounds_match:
                x1, y1 = int(bounds_match.group(1)), int(bounds_match.group(2))
                x2, y2 = int(bounds_match.group(3)), int(bounds_match.group(4))
                text_info['bounds'] = {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                text_info['position'] = {'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2}
            
            class_match = re.search(r'class="([^"]*)"', node)
            if class_match:
                text_info['element_type'] = class_match.group(1).split('.')[-1]
            
            texts.append(text_info)
    
    return texts


@mcp.tool()
def get_element_colors_at_position(
    x: int, 
    y: int,
    device_serial: str | None = None
) -> str:
    """
    Note: This captures a screenshot and the caller can analyze the pixel.
    For actual color extraction, use image processing on the screenshot.
    """
    return "Use screenshot() and analyze the image at the specified coordinates for color info."


if __name__ == "__main__":
    mcp.run()
