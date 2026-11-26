# aresos-shell/1.3

A desktop or view with the corresponding advertised capability receives
`apps_state` after hello and when the snapshot changes. Each row describes a
catalogue app that has a window. `active` means one window has the keyboard.
`hidden` means every window is minimized. The desktop clears the snapshot on
disconnect.

`activate_app` confirms that the chosen window or its modal child has focus,
joins a launch that has started without a window, or falls through to
`open_app`. The example includes the desktop's optional `screen` hint.
