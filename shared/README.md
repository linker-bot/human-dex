# Shared hand adapter

Both ROS recorders use this module. Policy hand vectors contain the ten independent
joints in `hand_adapter.JOINTS` order, in URDF radians. Action layout is left arm,
right arm, left hand, right hand (32 entries for the current robot).

Copy hand_mapping.example.json to a local configuration and replace every null:

    {"name": "verified_hardware_channel", "scale": 0.01, "offset": -0.2}

or use a verified zero-based `index` instead of `name`. The conversion is
`canonical_radians = hardware_value * scale + offset`; scale includes direction
and unit conversion. State and command mappings are independent. Never infer
hardware ordering from URDF file order. Command indices must cover 0..9; named
commands are emitted in canonical order with their explicit names. Confirm that
the downstream driver honors names, or use indexed commands with verified order.

Set `HUMAN_DEX_HAND_CONFIG` to the absolute JSON path. Set model to `L20lite` or
`l10v6`. Missing calibration fails at initialization; examples intentionally do
not contain a usable hardware mapping. When copying the ROS package outside this
repository, set `HUMAN_DEX_ROOT` to this repository root so it can find shared/.

Limits are based on the linker-bot/linkerhand-urdf models and intersect master
limits with mimic limits. They describe model angles, not calibrated hardware
safety limits. No blanket negative-angle clamp is applied. Velocity arrays are
empty unless explicitly supplied elsewhere; effort conversion is not assumed.
The 10 mimic joints are not extra policy outputs.

Existing 30-dimensional datasets, statistics and checkpoints are incompatible
with the new 32-dimensional task. Recollect missing channels and retrain;
do not silently pad old demonstrations. The other inherited task definitions
have not been migrated to this robot's schema.

Offline checks: `python3 -m unittest discover -s tests -v`.
