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