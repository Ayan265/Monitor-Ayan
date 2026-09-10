#!/usr/bin/python3
"""
Wayland Screenshot Helper for Accountability Monitor.

Takes a screenshot on Wayland via the XDG Desktop Portal (non-interactive)
and saves it to a specified path. Runs with SYSTEM Python (needs gi module).

Usage: python3 scripts/wayland_screenshot.py /tmp/output.png
Exit codes: 0 = success, 1 = failure
"""
import sys
import os
import shutil
import time

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

def take_screenshot(output_path, timeout_secs=5):
    """Take a screenshot via the XDG Desktop Portal and save to output_path."""
    
    result = {'uri': None, 'done': False, 'error': None}
    loop = GLib.MainLoop()
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    
    # We need to watch for the portal's Response signal on the request path
    request_token = f"monitor_{int(time.time())}"
    sender_name = bus.get_unique_name().replace('.', '_').replace(':', '')
    request_path = f"/org/freedesktop/portal/desktop/request/{sender_name}/{request_token}"
    
    def on_response(connection, sender, path, interface, signal, params):
        response_code = params[0]
        response_data = params[1]
        if response_code == 0:  # Success
            result['uri'] = response_data.get('uri', None)
        else:
            result['error'] = f"Portal returned response code {response_code}"
        result['done'] = True
        loop.quit()
    
    # Subscribe to the Response signal BEFORE making the call
    sub_id = bus.signal_subscribe(
        'org.freedesktop.portal.Desktop',
        'org.freedesktop.portal.Request',
        'Response',
        request_path,
        None,
        Gio.DBusSignalFlags.NO_MATCH_RULE,
        on_response
    )
    
    # Call the Screenshot portal with interactive=false and our handle_token
    try:
        bus.call_sync(
            'org.freedesktop.portal.Desktop',
            '/org/freedesktop/portal/desktop',
            'org.freedesktop.portal.Screenshot',
            'Screenshot',
            GLib.Variant('(sa{sv})', ('', {
                'interactive': GLib.Variant('b', False),
                'handle_token': GLib.Variant('s', request_token),
            })),
            GLib.VariantType('(o)'),
            Gio.DBusCallFlags.NONE,
            timeout_secs * 1000,
            None
        )
    except Exception as e:
        bus.signal_unsubscribe(sub_id)
        print(f"Portal call failed: {e}", file=sys.stderr)
        return False
    
    # Add a timeout to the main loop
    def on_timeout():
        if not result['done']:
            result['error'] = "Timeout waiting for portal response"
            loop.quit()
        return False
    GLib.timeout_add_seconds(timeout_secs, on_timeout)
    
    # Run the event loop until we get the response or timeout
    loop.run()
    bus.signal_unsubscribe(sub_id)
    
    if result['error']:
        print(f"Screenshot failed: {result['error']}", file=sys.stderr)
        return False
    
    if not result['uri']:
        print("No URI in portal response", file=sys.stderr)
        return False
    
    # The portal saves to a temp file and gives us a file:// URI
    source_path = result['uri']
    if source_path.startswith('file://'):
        source_path = source_path[7:]
    
    # Copy to the requested output path
    try:
        os.makedirs(os.path.dirname(output_path) or '/tmp', exist_ok=True)
        shutil.copy2(source_path, output_path)
        # Clean up the portal's temp file
        try:
            os.unlink(source_path)
        except OSError:
            pass
        return True
    except Exception as e:
        print(f"Failed to copy screenshot: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <output_path.png>", file=sys.stderr)
        sys.exit(1)
    
    output = sys.argv[1]
    success = take_screenshot(output)
    sys.exit(0 if success else 1)
