# Icon fixtures

These images were created for AresOS package 07 from geometric shapes and flat
colors. They contain no app/vendor/game artwork. `compass.ico` wraps the same
original PNG for Windows icon-resource extraction tests. The rectangular sunset
also exercises aspect-ratio preservation.

The 16×16 `*-golden.png` files freeze the reviewed `pixel-1` conversion. Tests compare
every pixel and never update a golden automatically. A deliberate style change
must bump the converter version, regenerate the goldens explicitly and review
both the tiny textures and the in-game fixture screenshots.
