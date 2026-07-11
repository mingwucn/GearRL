# RCIM Physical Demonstrator Protocol

This protocol is the required evidence gate for an RCIM submission. The software system must not claim that this validation has occurred until every artifact below is attached to an immutable experiment bundle.

## Demonstrator

- Select one externally approved benchmark case and one certified GearRL layout.
- Freeze the exact problem JSON, validation certificate, CAE report, DXF/SVG exports, material, module, face width, target signed speed ratio, and load case before fabrication.
- Manufacture or procure the gears, shafts, spacers, housing plate, bearings, and couplings. Record supplier part numbers, material certificates, and dimensional inspection results.
- Assemble only the exported design. Record every manual adjustment as a deviation; an adjustment invalidates direct design-to-manufacture claims unless it is fed back into a new certified run.

## Measurements

Measure and archive the following for at least three independent assemblies or repeat runs:

| Measurement | Instrument | Acceptance criterion |
| --- | --- | --- |
| Input/output angular-velocity ratio | Encoder or tachometer | Within the declared ratio tolerance |
| Rotation direction | Encoder trace | Matches signed certified ratio |
| Center distances and shaft locations | CMM, caliper, or dial indicator | Within declared geometric tolerance |
| Backlash and minimum clearance | Dial indicator / inspection | Meets declared manufacturing allowance |
| Applied torque and output torque | Torque sensor or calibrated brake | Matches the stated load-case model within predeclared uncertainty |
| Temperature, noise, and visible wear | Logged observation | Reported descriptively; not used to claim fatigue validation |

## Evidence Bundle

Create one write-once bundle per assembly containing raw sensor files, calibration records, photographs, assembly steps, inspection measurements, test command/configuration, source commit, and an explicit comparison of measured versus certified values.

The RCIM paper may claim a physical demonstrator only when the full bundle has been independently reviewed and the measured ratio, fit, and declared load-condition checks pass. Otherwise use the AEI digital-workflow submission path.
