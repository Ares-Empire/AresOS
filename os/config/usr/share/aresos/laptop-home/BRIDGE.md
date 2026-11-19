# Laptop home bridge

Load the packaged entry point at `aresos-home://page/index.html`. Its relative URLs can load
packaged scripts, stylesheets, data, pictures and fonts. Use external scripts or modules for
page JavaScript. CSS can use local system fonts by name. The resource policy allows
requests to the packaged page and catalogue icon origins.

## Calls

All snapshots are copies. The bridge updates them together before firing events.

| Call | Result |
| --- | --- |
| `home()` | `{palette, apps}`. `palette` maps one-character keys to `#rrggbb` colours. `apps` is an array of houses. |
| `programs()` | An array of catalogue entries. |
| `open(id)` | A promise for `{state}` on success or `{state: "failed", message}` on failure. The helper's success states are `starting`, `focused`, `background` and `closed`. Display `message` as text. An offline call resolves with `Opening is back in a moment`. |
| `status()` | `{battery: {level, charging}}` with an integer percentage and a boolean, or `{battery: null}` when absent. |

A house has `id`, `name`, `short`, `group` and `cells` strings. `cells` has 144
characters for the 12 × 12 logo in row order, starting at the top. A dot is transparent.
`place` is the optional place string (for example `N0L0`). `slot` is the optional hotbar
index from 0 to 8. `name` comes from the catalogue, with `short` as the fallback while
the helper discovers a newly published app. The saved town includes these names.

A catalogue entry has string `id` and `name`, nullable string `generic_name`, string array
`keywords` and boolean `has_icon`. For an entry with `has_icon`, request
`aresos-home://icon/APP_ID`. Supply a visual fallback if the image fails to load, since the
file can disappear or fail validation. Render catalogue and house text as text.

## Events

Use `aresosHome.addEventListener(name, handler)` and
`aresosHome.removeEventListener(name, handler)`. Register listeners during module startup.
After `DOMContentLoaded` the program replays all five events in the order below, with the
latest state. For the first draw, wait for that replay so the initial running IDs can light
their houses. Subsequent events contain the values as of that update.

| Event | `event.detail` |
| --- | --- |
| `home` | `null`. Read `home()` again. |
| `programs` | The complete catalogue array, in the same format as `programs()`. |
| `running` | An array of running app IDs. An app runs while the helper sees a window for it. |
| `status` | The current status object, in the same format as `status()`. |
| `helper` | A boolean. Enable opening only while it is true. |

While the helper is away, the town and running IDs stay visible. A reconnect before the game
publishes retains the saved town and supplies current running IDs. The helper accepts opens
again at that point. A complete published empty town clears the saved town.

## Page geometry

`window.laptopHome.world.snapshot()` gives the viewport, floor, road and roof ledges, and
house occluders in 1920 × 1080 stage coordinates. Its `streetOffsets` maps each group ID to
the current horizontal translation in those coordinates. Read it on demand during a slide.
The houses and roofs move with their streets. Day roads and their ledges stay in place.
