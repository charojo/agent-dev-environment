---
description: How to add a new scene to the Papeterie Engine
---

To add a new scene to the Papeterie Engine, follow these steps:

1.  **Prepare Assets**:
    -   Create/Identify the main source image.
    -   Identify individual layers (backgrounds, middle-ground, foreground, sprites).
    -   Export each layer as a transparent `.png` and place them in `/assets/sprites/<sprite_name>/<sprite_name>.png`.

2.  **Generate Prompts**:
    -   For each new sprite, create a `.prompt` file in the same directory: `/assets/sprites/<sprite_name>/<sprite_name>.prompt`.
    -   Describe the sprite's visual appearance and intended physical behavior (e.g., "A heavy lantern that bobs slowly").

3.  **Compile Sprites**:
    -   Use the `SpriteCompiler` to generate `.prompt.json` metadata for each new sprite.
    -   You can run this via a script or by calling `SpriteCompiler.compile_sprite(name, description)`.

4.  **Define the Scene**:
    -   Create a new scene configuration file in `assets/story/scene_<name>.json`.
    -   Follow the schema defined in `docs/scene_design.md`.
    -   Example structure:
        ```json
        {
          "scene_name": "Villagers by the Lake",
          "layers": [
            {
              "sprite_name": "background_lake",
              "z_depth": 1,
              "scroll_speed": 0.1
            },
            {
              "sprite_name": "villagers",
              "z_depth": 5,
              "scroll_speed": 1.0
            }
          ]
        }
        ```

5.  **Run and Verify**:
    -   Run the theatre with the new scene:
        ```bash
        python src/renderer/theatre.py assets/story/scene_<name>.json
        ```
    -   Verify parallax depth, bobbing, and any environmental reactions.

6.  **Refinement**:
    -   Adjust `z_depth`, `scroll_speed`, or sprite metadata (`bob_frequency`, etc.) in the `.json` file.
    -   Changes to the `.json` file during runtime should be automatically reloaded.
