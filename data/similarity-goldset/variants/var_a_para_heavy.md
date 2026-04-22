# Avionics Electromagnetic Compatibility Verification Manual

<!-- Page 1 -->

## 1. Introduction

For avionics components destined for military aircraft platforms, EMC testing
plays a fundamental verification role. We outline below a methodology that
permits engineers to characterize emission and susceptibility behavior across
all functional units involved in signal handling. Every contractor falls under
this methodology absent any waiver granted by the acquiring organization.

## 2. Coverage

Whether classified as a line replaceable unit or as a shop replaceable unit,
any module operating between 30 hertz and 18 gigahertz lies within the scope
described here. Two categories escape this scope: assemblies built entirely
from mechanical parts, and battery powered devices whose runtime stays under
one minute. Identification of equipment falling under these provisions is the
responsibility of whoever holds the contract.

## 3. Source Documents

Several external publications establish the technical basis. Where this manual
and an external reference disagree, this manual prevails. Emission ceilings and
susceptibility floors come from MIL-STD-461G. System integration considerations
flow from MIL-STD-464D. As an alternative path with commercial equivalence,
RTCA DO-160G may be considered.

## 4. Conditions Required for Valid Testing

### 4.1 Climate and Shielding

A shielded enclosure forms the basis of every test. Within the band of 10 kilohertz
to 10 gigahertz, that enclosure must keep external interference attenuated by no
less than 100 decibels. Climate control inside maintains a temperature window of
18 to 28 Celsius and humidity not above three quarters. Environmental noise needs
to remain at least 6 decibels under whichever emission limit is most stringent.

### 4.2 How the Equipment Sits

Test articles take their normal operational configuration, complete with every
interconnect cable as drawn. A line impedance stabilization network shapes power
delivery: 50 microhenries paired with 50 ohms in parallel. Bonding between the
device and ground plane follows whichever method the installation control
documentation prescribes.

## 5. Emissions via Conduction

### 5.1 Instrumentation Approach

Engineers route a current probe across the power leads, holding it 5 centimeters
away from the connector. Bandwidth selection on the receiver follows the band:
1 kilohertz resolution at the bottom, 10 kilohertz in the mid range, and 100
kilohertz once beyond 100 kilohertz. Detection mode defaults to peak unless an
alternative gets specified.

### 5.2 What Is Permissible

Class A and Class B equipment have separate ceilings shown in Figures 5-1 and
5-2 respectively, and narrowband emissions must respect these. Compliance with
Figure 5-3 governs broadband cases. Should any single discrete emission run more
than 3 decibels above its ceiling, log it on its own and capture frequency,
amplitude, and bandwidth.

## 6. Emissions via Radiation

### 6.1 Choosing an Antenna

Three antenna types span the test band. Below 200 megahertz, a biconical type
applies. Between 200 megahertz and 1 gigahertz, a log periodic does the work.
Above 1 gigahertz, the horn antenna takes over. Antenna placement: one meter
forward of the test article face. Polarizations vertical and horizontal both
get measured at every frequency point.

### 6.2 Permissible Levels

Whatever Table 6-1 specifies sets the ceiling for radiated emissions. Should an
emission come within 3 decibels of that ceiling, schedule a confirmation
measurement. Justification accompanies any waiver request the contractor sends
upward.

## 7. Resistance to Interference

While exposed to the radiated and conducted stress profiles of Table 7-1,
equipment must keep functioning without malfunction, performance loss, or
parameter excursion. Mode by mode, the equipment specification spells out the
acceptance bar. Once stress disappears, recovery happens automatically without
any operator action.

## 8. Final Reporting

A consolidated report goes to the procuring authority following the CDRL pattern.
Inside it, expect photographs of setups, calibration histories of measurement
gear, full data plots, and a structured listing of every limit exceedance paired
with the proposed remediation. The clock for submission is 30 calendar days
counting from when testing wraps up.
