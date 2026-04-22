# Electromagnetic Compatibility Test Procedure for Avionics Equipment

<!-- Page 1 -->

## 1. SCOPE

This standard establishes the test procedures and requirements for measuring the
electromagnetic compatibility (EMC) characteristics of avionics equipment intended
for installation on military aircraft platforms. The procedures defined herein apply
to all equipment that processes, transmits, or receives electrical signals during
normal operation. Compliance with this standard is mandatory unless otherwise
specified by the procuring activity.

## 2. APPLICABILITY

The requirements of this standard shall apply to all line replaceable units (LRU)
and shop replaceable units (SRU) that operate in the radio frequency range from
30 Hz to 18 GHz. Equipment exempt from these requirements includes purely mechanical
assemblies and battery powered devices with operating durations less than 60 seconds.
The contractor shall identify all candidate equipment in accordance with the
applicable system specification.

## 3. REFERENCE DOCUMENTS

The following documents form a part of this specification to the extent specified
herein. In the event of a conflict between the text of this specification and the
references cited, the text of this specification shall take precedence. MIL-STD-461G
governs the emission and susceptibility limits. MIL-STD-464D defines system level
requirements. RTCA DO-160G provides commercial equivalence guidance.

## 4. GENERAL TEST CONDITIONS

### 4.1 Ambient Environment

All tests shall be performed in a shielded enclosure providing a minimum of 100 dB
of attenuation between 10 kHz and 10 GHz. The ambient temperature within the
enclosure shall be maintained between 18 and 28 degrees Celsius. Relative humidity
shall not exceed 75 percent during any test sequence. The ambient electromagnetic
environment shall be at least 6 dB below the lowest specified emission limit.

### 4.2 Equipment Configuration

The equipment under test shall be configured in its normal operating mode with all
interconnecting cables installed as defined in the installation drawing. Power
input cables shall be routed through a line impedance stabilization network (LISN)
having an impedance of 50 microhenries in parallel with 50 ohms. The equipment
shall be bonded to the ground plane using the methods specified in the installation
control document.

## 5. CONDUCTED EMISSIONS

### 5.1 Test Setup

Conducted emissions on power leads shall be measured using a current probe
positioned 5 centimeters from the equipment connector. The measurement receiver
shall employ a 1 kHz resolution bandwidth from 30 Hz to 1 kHz, a 10 kHz bandwidth
from 1 kHz to 100 kHz, and a 100 kHz bandwidth above 100 kHz. Peak detection mode
shall be used for all measurements unless specifically directed otherwise.

### 5.2 Limits

The narrowband emissions shall not exceed the levels defined in Figure 5-1 for
Class A equipment or Figure 5-2 for Class B equipment. Broadband emissions shall
comply with the limits in Figure 5-3. Discrete emissions exceeding the limit by
more than 3 dB shall be reported individually with frequency, amplitude, and
bandwidth recorded in the test report.

## 6. RADIATED EMISSIONS

### 6.1 Antenna Configuration

A biconical antenna shall be used from 30 MHz to 200 MHz, a log periodic antenna
from 200 MHz to 1 GHz, and a horn antenna above 1 GHz. The antenna shall be
positioned 1 meter from the front face of the equipment under test. Vertical and
horizontal polarization measurements shall be performed at each frequency.

### 6.2 Limits

Radiated emissions shall not exceed the limits specified in Table 6-1. Where the
equipment exhibits emissions within 3 dB of the limit, additional measurements
shall be performed to verify the result. The contractor shall provide rationale
for any exceedance request submitted to the procuring activity.

## 7. SUSCEPTIBILITY REQUIREMENTS

The equipment under test shall not exhibit malfunction, degradation of performance,
or deviation from specified parameters when subjected to the radiated and conducted
susceptibility levels of Table 7-1. The performance criteria for each operating
mode shall be defined in the equipment specification. Recovery without operator
intervention shall be required after removal of the susceptibility stimulus.

## 8. TEST REPORT

A formal test report shall be prepared in accordance with the contract data
requirements list (CDRL). The report shall include test setup photographs,
calibration data for all measurement equipment, complete plots of measured data,
and a tabulation of all exceedances with proposed corrective action. The report
shall be submitted within 30 calendar days of test completion.
