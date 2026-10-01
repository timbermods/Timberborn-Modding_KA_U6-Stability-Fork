1.1.0.2
* Re-added the multi-length tunnels (TE_Tunnel_1 to 9) as flat 1.1 blueprints, regenerated from the archived nested prefab modules with tools/flatten_tunnels.py. They are still flagged dev-mode only (as the original author had them) because tunnelling through terrain has not been verified on 1.1. Enable dev mode to test them; they appear in the Paths group.

1.1.0.1
* Fix crash on new game: 'No type found for key DrivewayModelSpec' (renamed to DrivewayModelsSpec with a Driveways list in 1.1) for the Small Gate and Levee Tunnel.
* Fix path tiles, shafts and other objects on top of bridges being deleted on every save load. The 1.1 loader adds objects ordered by base level and then by highest occupation, so a bridge whose base layer occupied Corners/Top was loaded after the objects resting on it. Corners/Top now sit on the stackable deck layer (like the vanilla Platform) and the base layer is unoccupied. The bridge anchor cell no longer reserves Corners.
* Requires game version 1.1.0.0 or newer.

1.0.0.9
* Fix mod for game version 1.0.11.1


---
MinimumGameVersion: 1.1.0.0
MaximumGameVersion: 1.1.99.9
---