"""GTK 4 toplevel for the frame smoke test."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, Gtk

COLOUR = '#d7d3c9'


def activate(app):
    css = Gtk.CssProvider()
    css.load_from_string(f'window {{ background-color: {COLOUR}; color: #1a181f; }}')
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window = Gtk.ApplicationWindow(application=app, title='GTK 4 ÄÖÜß', default_width=620, default_height=300)
    window.set_child(Gtk.Label(label='GTK 4 window'))
    window.present()


app = Gtk.Application(application_id='org.aresos.FrameHarness')
app.connect('activate', activate)
app.run([])
