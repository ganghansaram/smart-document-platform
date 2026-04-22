# Electromagnetic Compatibility Test Procedure for Avionics Equipment

<!-- Page 1 -->

## 1. SCOPE

This document defines the test procedures and requirements for evaluating the
electromagnetic compatibility (EMC) characteristics of avionics hardware intended
for installation on military aircraft systems. The procedures defined herein cover
all hardware that processes, transmits, or receives electrical signals during
normal operation. Compliance with this document is required unless otherwise
specified by the procuring activity.

## 2. APPLICABILITY

The requirements of this document shall apply to all line replaceable units (LRU)
and shop replaceable units (SRU) that operate in the radio frequency band from
30 Hz to 18 GHz. Hardware exempt from these requirements includes purely mechanical
assemblies and battery powered devices with operating times less than 60 seconds.
The contractor shall identify all candidate hardware in accordance with the
applicable system specification.

## 3. REFERENCE DOCUMENTS

The following publications form a part of this document to the extent specified
herein. In the event of a conflict between the text of this document and the
references cited, the text of this document shall take precedence. MIL-STD-461G
governs the emission and susceptibility limits. MIL-STD-464D defines system level
requirements. RTCA DO-160G provides commercial equivalence guidance.

## 4. GENERAL TEST CONDITIONS

### 4.1 Ambient Environment

All tests shall be performed in a shielded chamber providing a minimum of 100 dB
of isolation between 10 kHz and 10 GHz. The ambient temperature within the
chamber shall be maintained between 18 and 28 degrees Celsius. Relative humidity
shall not exceed 75 percent during any test sequence. The ambient electromagnetic
environment shall be at least 6 dB below the lowest specified emission limit.

### 4.2 Equipment Configuration

The hardware under test shall be configured in its normal operating mode with all
interconnecting cables installed as defined in the installation drawing. Power
input cables shall be routed through a line impedance stabilization network (LISN)
having an impedance of 50 microhenries in parallel with 50 ohms. The hardware
shall be bonded to the ground plane using the methods specified in the installation
control document.

## 5. CONDUCTED EMISSIONS

### 5.1 Test Setup

Conducted emissions on power leads shall be measured using a current sensor
positioned 5 centimeters from the hardware connector. The measurement receiver
shall employ a 1 kHz resolution bandwidth from 30 Hz to 1 kHz, a 10 kHz bandwidth
from 1 kHz to 100 kHz, and a 100 kHz bandwidth above 100 kHz. Peak detection mode
shall be used for all measurements unless specifically directed otherwise.

### 5.2 Limits

The narrowband emissions shall not exceed the levels defined in Figure 5-1 for
Class A hardware or Figure 5-2 for Class B hardware. Broadband emissions shall
comply with the limits in Figure 5-3. Discrete emissions exceeding the limit by
more than 3 dB shall be reported individually with frequency, amplitude, and
bandwidth recorded in the test report.

## 6. RADIATED EMISSIONS

### 6.1 Antenna Configuration

A biconical antenna shall be used from 30 MHz to 200 MHz, a log periodic antenna
from 200 MHz to 1 GHz, and a horn antenna above 1 GHz. The antenna shall be
positioned 1 meter from the front surface of the hardware under test. Vertical and
horizontal polarization measurements shall be carried out at each frequency.

### 6.2 Limits

Radiated emissions shall not exceed the limits specified in Table 6-1. Where the
hardware exhibits emissions within 3 dB of the limit, additional measurements
shall be performed to verify the result. The contractor shall provide rationale
for any exceedance request submitted to the procuring activity.

## 7. SUSCEPTIBILITY REQUIREMENTS

The hardware under test shall not exhibit malfunction, degradation of performance,
or deviation from specified parameters when subjected to the radiated and conducted
susceptibility levels of Table 7-1. The performance criteria for each operating
mode shall be defined in the hardware specification. Recovery without operator
intervention shall be required after removal of the susceptibility stimulus.

## 8. TEST REPORT

A formal test report shall be prepared in accordance with the contract data
requirements list (CDRL). The report shall include test setup photographs,
calibration data for all measurement instruments, complete plots of measured data,
and a tabulation of all exceedances with proposed corrective action. The report
shall be submitted within 30 calendar days of test completion.
