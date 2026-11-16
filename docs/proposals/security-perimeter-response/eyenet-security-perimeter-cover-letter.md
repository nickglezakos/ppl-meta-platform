# Cover letter — Mine Site Security Perimeter

**To:** Phillip  
**From:** EyeNet  
**Date:** 15 November 2026  
**Re:** EyeNet compliance for the care-and-maintenance mine perimeter  
**Enclosed:** Mine Site Security Perimeter — EyeNet Compliance (`eyenet-security-perimeter-compliance-print.html`)

Dear Phillip,

Thank you for the site brief. The enclosed report maps the requested operating model — unfenced wide-area detection, night intrusion alerting, drone response, and an alarm-led control room — onto EyeNet as it is deployed today.

**On the software, EyeNet is ready out of the box for this site.** Gate, Presence, Vradar, Sentinel, Matrix, Cameras and Vision, the ONVIF connectors, and Area and Drone modes already cover virtual perimeters, person and vehicle detection, intrusion and loitering alarms, on-premises recording, and remote viewing over the hub link. Detection runs on the local installation. Video does not depend on the cloud. Standard business servers are sufficient; a GPU farm is not required.

The one software item still to complete is a **minor development on drone synchronisation**: tying a verified EyeNet alarm to the launch or tasking of the response drone, and bringing that aerial feed back into the same alarm and incident record. Drone mode already treats an aerial stream as another detection camera, and webhooks can already raise the cue. What remains is the small sync between the alarm and the drone, not a new platform. Hybrid-fuel, tethered, and drone-in-a-box airframes stay with the drone supplier. EyeNet consumes their video and drives the alarm workflow.

Hardware, aviation approval, and control-room facilities stay with the site and its suppliers. EyeNet is the detection, alarm, recording, and command layer on top of that equipment.

## Hardware prerequisites

These are the main items the site needs in place for the stack in the report. Phase 1 can start without the dock, the tether, or ground radar.

1. **Two existing towers.** One dual-sensor long-range PTZ per tower (thermal and day/night optical), one or two fixed wide-angle ONVIF/RTSP cameras on approaches and the pit edge, and a camera on the tower base. Stabilised mounts, a structural check for weight and wind, UPS at the base, lightning and surge protection, a loudspeaker, and fibre or radio back to the control room.
2. **Four solar mobile CCTV towers to start** (two further units only after alarm data shows the gaps). Each unit needs PTZ and fixed cameras, LED lighting, siren and loudspeaker, solar and battery for at least three nights, a 4G/LTE or mesh radio, and tamper plus GPS hardware on the mast.
3. **A response drone for close imaging**, with a thermal and zoom camera whose live stream EyeNet can ingest. The dock (drone-in-a-box) and the tethered overwatch aircraft are later additions, once endurance and aviation approval are settled. National aviation approval, including beyond visual line of sight for a docked aircraft, plus pilots and a maintenance contract, sit with the site.
4. **Control-room compute and desks.** An on-premises server and storage sized for about 30 days at the planned camera count, operator workstations, and power and network for a backup viewing position in the security office.
5. **Links.** Starlink, cellular, or Wi-Fi at the central areas, which the brief says are already there, plus radio or LTE from the perimeter cameras into that on-premises node. Perimeter cameras do not need a cloud path.
6. **Partner equipment outside the EyeNet licence.** Radio dispatch, vehicle GPS tracking, tower talk-down loudspeakers, and, if added later, ground radar slaved to a PTZ. Control-room UPS, surge protection, dust filtering, and the door lock are facilities work.

## What we need from the site owner

The EyeNet team can be briefed in detail, and can run a lab-scale test, once the site owner provides the following. These are confirmations and records, not a new design.

1. **Tower facts.** Height, location, line of sight into the pit and across the boundary, and what power and data exist at each tower base.
2. **A marked site map.** The virtual perimeter and the priority zones: pit floor, waste dumps, remote tracks, community boundary, and artisanal-mining hotspots. The map link in the brief is the starting point; we need the zones the security team actually wants watched.
3. **A control-room audit.** Current VMS brand and version, camera count and whether they are IP or analogue, server and storage age, days of recording kept, and the condition of the UPS and air conditioning.
4. **Phase-1 scope in writing.** Confirmation that the first build is the two towers plus four mobile towers and one response drone, with the dock, tether, extra mobile towers, and radar held until alarm data and aviation approval justify them.
5. **Shortlisted cameras and the drone stream.** Make and model, or confirmation that each camera and the drone expose ONVIF/RTSP, plus a short night or thermal sample if one already exists. The lab test uses the real stream type.
6. **Connectivity.** Where cellular, Wi-Fi, and Starlink reach today, and the intended backhaul from each tower and mobile mast (fibre, radio, or LTE).
7. **Operating rules.** What counts as after-hours, which areas are restricted, and how staff and contractors should be separated from unknown people and vehicles so known presence does not fill the alarm list.
8. **Named owners.** The security lead, the control-room owner, and the person who will sign the alarm procedures. Also who holds aviation responsibility and the pilot role.
9. **Where the EyeNet node sits.** Room, power, and network for the control-room server and for the backup viewing position, and confirmation that about 30 days of recording is the retention target.

## How we proceed

1. **Briefing.** With the pack above, the EyeNet team walks the site owner through the enclosed compliance map: what is already in the product, what the drone sync adds, and which hardware lines are site or partner supply.
2. **Lab-scale test, in our labs.** Before anything is shipped, we stand up the phase-1 software path on representative streams: tower and mobile-tower cameras, thermal and day/night feeds, virtual zones, intrusion and loitering rules, recording, and the drone-sync path against a lab drone stream. The site owner sees the alarm chain working at lab scale.
3. **Shipping and installation.** After that lab result is accepted, we coordinate shipping and installation on site with the towers, radios, servers, and drone the owner has confirmed. Field work then connects those feeds to the installation already proven in the lab, and operators are trained on the alarm-led procedure.

We are ready to schedule the briefing as soon as the nine items above are in hand.

Nick  
EyeNet  
eyenet-vision.com · nick@eyenet-vision.com
