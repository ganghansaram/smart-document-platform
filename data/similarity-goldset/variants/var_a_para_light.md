# EMC Test Procedures for Avionics Hardware

<!-- Page 1 -->

## 1. Scope of Application

The present standard provides test procedures along with requirements for
characterizing electromagnetic compatibility properties of avionics units used
in military aircraft installations. These procedures cover any unit that handles,
emits, or accepts electrical signals in normal operation. Conformance to this
standard is required except when the procuring authority specifies otherwise.

## 2. What Is Covered

The provisions of this standard apply to every line replaceable unit (LRU) and
shop replaceable unit (SRU) operating across the radio frequency span between
30 Hz and 18 GHz. Items not subject to these provisions are purely mechanical
assemblies along with battery driven units whose operation lasts under 60 seconds.
The contractor is responsible for identifying every candidate unit per the
relevant system specification.

## 3. Documents Cited

The publications below form part of this specification within the limits noted
in subsequent sections. Should the text of this specification conflict with any
cited reference, the text of this specification governs. Emission and susceptibility
limits are governed by MIL-STD-461G. System level requirements are defined in
MIL-STD-464D. Commercial equivalence guidance comes from RTCA DO-160G.

## 4. General Conditions for Testing

### 4.1 Surrounding Environment

Every test must be carried out inside a shielded enclosure delivering attenuation
of at least 100 dB in the 10 kHz to 10 GHz range. Temperature inside the enclosure
must be held within an 18 to 28 degree Celsius window. Relative humidity must
remain at or below 75 percent throughout any test sequence. Background
electromagnetic levels must sit at least 6 dB beneath the lowest specified
emission limit.

### 4.2 Configuration of the Equipment

Test articles must be set up in their normal operating configuration with every
interconnecting cable installed per the installation drawing. Power supply cables
must pass through a line impedance stabilization network (LISN) with impedance
characterized by 50 microhenries paralleled with 50 ohms. The article must be
bonded to the ground plane following the methods given in the installation
control document.

## 5. Conducted Emission Testing

### 5.1 Setup of the Test

To measure conducted emissions on power leads, employ a current probe placed at
a 5 centimeter distance from the equipment connector. Receiver settings call for
a 1 kHz resolution bandwidth between 30 Hz and 1 kHz, a 10 kHz bandwidth between
1 kHz and 100 kHz, and a 100 kHz bandwidth beyond 100 kHz. Apply peak detection
mode throughout unless directed otherwise.

### 5.2 Allowable Levels

Narrowband emission levels must not surpass the values shown in Figure 5-1 for
Class A units or in Figure 5-2 for Class B units. Broadband emissions must satisfy
the levels in Figure 5-3. When discrete emissions exceed any limit by more than
3 dB, document each one separately with its frequency, amplitude, and bandwidth
captured in the report.

## 6. Radiated Emission Testing

### 6.1 Antenna Selection

Use a biconical antenna in the 30 MHz to 200 MHz range, a log periodic antenna
from 200 MHz up to 1 GHz, and a horn antenna for frequencies above 1 GHz. Place
the antenna at 1 meter from the front face of the test article. Carry out
measurements at each frequency for both vertical and horizontal polarizations.

### 6.2 Allowable Levels

Radiated emission levels must not surpass the limits given in Table 6-1. Whenever
emissions fall within 3 dB of the limit, additional verification measurements
must follow. The contractor must justify any exceedance request submitted to
the procuring authority.

## 7. Susceptibility Provisions

When subjected to the radiated and conducted susceptibility levels of Table 7-1,
the article under test must show no malfunction, performance degradation, or
parameter deviation. Performance criteria per operating mode are to be defined
in the equipment specification. Recovery without operator intervention is required
once the susceptibility stimulus is removed.

## 8. Reporting

A formal report must be prepared per the contract data requirements list (CDRL).
The report must contain test setup photographs, calibration data for every
measurement instrument, full plots of measured data, and a tabulation of every
exceedance with proposed corrective action. Submission must occur within 30
calendar days following test completion.
