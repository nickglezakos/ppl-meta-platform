# EyeNet Vision Product Roadmap
**PPL Meta Implementation Status**

---

## Product Development Status Overview

| Product | Variant | Status | Target Launch | Hardware Requirements | Key Features |
|---------|---------|--------|----------------|----------------------|--------------|
| **Intelligent Signage** | Fixed Installation | Beta Testing Ready | Q2 2026 | IP Camera + Display Screens | Automated demographic-based content delivery |
| | ⭐ Mobile Variant | Beta Testing Ready | Q2 2026 | Mobile Camera + Tablets | Marketing teams on the go, conferences, kiosks, pop-up activations |
| **Underage Detector** | Standard | Beta Testing Ready | Q2 2026 | IP Camera (POS) | Real-time age verification at point-of-sale |
| **Gate Activity** | Standard | Beta Testing Ready | Q2 2026 | IP Camera (Gate/Corridor) | Crowd analytics, threat detection, facial recognition |
| **Room & Gate Protection** | Standard | Beta Testing Ready | Q2 2026 | IP Camera (Room/Gate) | Attendance tracking, access control, compliance reporting |
| **Sentinel** | Fixed Station | Beta Testing Ready | Q2 2026 | IP Camera (Guard Station) | Guard accountability, activity monitoring |
| | ⭐ Mobile Variant | Beta Testing Ready | Q2 2026 | Mobile Camera + Tablets | VIP protection, dynamic security perimeters, executive details |
| **Security Officer Agent** | Software Ready | Software Complete | Q3/Q4 2026 | Smart Glasses + RPi4 | Wearable field operations with real-time alerts (Hardware in development) |

---

## Product Maps

### 1. INTELLIGENT SIGNAGE
**Status**: ✅ Beta Testing Ready  
**Target Launch**: Q2 2026

#### Purpose
Transform digital displays into intelligent marketing platforms with demographic-driven content delivery.

#### Product Variants

**Variant A: Fixed Installation**
- Permanent placement in retail, airports, advertising centers
- IP-based camera integration
- Stationary display devices

**Variant B: Mobile Variant** ⭐ ***Marketing Teams on the Go***
- Portable system for field marketing deployments
- **EyeNet mobile camera + tablet** configuration
- Ideal for pop-up marketing, trade shows, conferences, kiosks, and temporary retail activations
- Real-time demographic insights enable agile campaign adjustments
- Marketing teams can deploy audience-targeted content in minutes

#### Key Features
- Demographic-based content automation (age/gender detection)
- Real-time audience analytics and engagement metrics
- Web-based media management interface
- Activity insights with traffic counts and heatmaps
- Multi-mode deployment support
- **Mobile variant**: Portable setup with tablet dashboard and wireless camera connectivity

#### Deployment Modes
- **Spot Mode**: POS counters, product displays
- **Gate Mode**: Retail entrances, mall corridors
- **Area Mode**: Large retail spaces, store interiors
- **Mobile Station Mode**: _Tablet + mobile camera for marketing teams on the go, kiosks, conferences, and event venues_

#### Hardware Requirements

**Fixed Variant**:
- IP Cameras (with edge processing capability)
- Network connectivity to central platform
- Display devices (Digital signage screens)
- Central orchestration server

**Mobile Variant**:
- EyeNet mobile camera
- Tablets (iPad/Android) for content display and analytics
- Wireless connectivity (WiFi/4G)
- Mobile charging solution (portable battery packs)

#### Target Markets

**Fixed Installations**:
- Retail shops and shopping malls
- Airport displays
- Advertising agencies

**Mobile Variant**:
- Marketing agencies (field campaigns)
- Event venues and conferences
- Trade show exhibitors
- Temporary retail pop-up shops
- Field marketing teams
- Brand activation agencies

#### Metrics of Success
- Content engagement rate
- Customer dwell time on displays
- Demographic accuracy
- Campaign conversion optimization
- Real-time audience insights accuracy

#### Beta Testing Plan

**Fixed Variant**:
- Pilot in 2-3 retail locations
- Test demographic accuracy across demographics
- Validate user interface for content managers

**Mobile Variant**:
- Test with 2-3 marketing agencies doing field campaigns
- Validate tablet usability in mobile environments
- Test wireless connectivity in conference/event venues
- Measure engagement metrics for on-the-go deployments
- Gather UX feedback from mobile marketing teams
- Test setup/teardown speed for rapid deployment

#### Next Steps
1. Finalize IP camera integration
2. Prepare beta site agreements
3. Create marketing analytics dashboard
4. Develop campaign tracking API
5. Launch Q2 2026

---

### 2. UNDERAGE DETECTOR
**Status**: ✅ Beta Testing Ready  
**Target Launch**: Q2 2026

#### Purpose
Point-of-sale age verification system ensuring compliance with age-restricted sales.

#### Key Features
- Real-time age estimation
- Distance-based person prioritization (closest first)
- Compliance flagging system
- Minimal personal data collection (age-only)
- Integration with POS workflows

#### Deployment Mode
- **Spot Mode**: POS counter monitoring (exclusive)

#### Hardware Requirements
- IP Camera (high-angle, pointing at POS counter)
- Central orchestration server
- Local display (optional - for age estimation display)

#### Target Markets
- Retail shops (alcohol, tobacco, age-restricted products)
- Supermarkets with age-restricted sections
- Bars and restaurants
- Convenience stores

#### Metrics of Success
- Age estimation accuracy
- False rejection rate
- Compliance documentation completeness
- Staff acceptance and usage rate
- Regulatory compliance documentation

#### Compliance Requirements
- Documentation of age estimation methodology
- Privacy compliance (age-only collection)
- Audit trail for compliance purposes
- Integration with local regulatory requirements

#### Beta Testing Plan
- Pilot in 2-3 retail locations selling age-restricted products
- Test accuracy across age ranges and ethnicities
- Validate staff workflow integration
- Measure false rejection rates
- Gather compliance officer feedback
- Document regulatory compliance approach

#### Next Steps
1. Finalize age detection model optimization
2. Establish retail partnerships for beta
3. Prepare compliance documentation
4. Create staff training materials
5. Launch Q2 2026

---

### 3. GATE ACTIVITY
**Status**: ✅ Beta Testing Ready  
**Target Launch**: Q2 2026

#### Purpose
Advanced security monitoring for entrances and corridors with crowd analytics and threat detection.

#### Key Features
- Real-time people counters
- Demographic analysis (age/gender)
- Crowd behavior metrics
- Activity heatmaps
- Abnormal activity alerts
- Facial recognition for persons of interest
- Live video streaming with annotations
- Flexible video storage (instant + deep archive)

#### Deployment Mode
- **Gate Mode**: Entrances, exits, corridors (exclusive)

#### Hardware Requirements
- High-resolution IP Camera (gate/corridor mounting)
- Network connectivity
- Central orchestration server
- Video storage infrastructure (instant + archive)
- Alert distribution system

#### Target Markets
- Security agencies
- Commercial buildings
- Industrial facilities
- Airports
- Public transport hubs
- Event organizers

#### Metrics of Success
- Crowd counting accuracy
- Abnormal behavior detection precision
- Facial recognition accuracy
- Video storage efficiency
- Alert response time
- Security incident documentation

#### Beta Testing Plan
- Pilot in 2-3 facilities (commercial building, parking garage, event venue)
- Test crowd counting accuracy
- Validate abnormal behavior detection
- Measure facial recognition performance
- Test video storage and retrieval
- Gather security team feedback
- Validate alert integration

#### Next Steps
1. Finalize facial recognition accuracy
2. Establish security partnerships for beta
3. Configure alert integration (email, SMS, integrations)
4. Create security dashboard views
5. Prepare video storage architecture
6. Launch Q2 2026

---

### 4. ROOM & GATE PROTECTION
**Status**: ✅ Beta Testing Ready  
**Target Launch**: Q2 2026

#### Purpose
Comprehensive attendance monitoring and access control with automated reporting and minor protection.

#### Key Features
- Schedule and member assignment
- Real-time attendance tracking
- Unauthorized access alerts
- Comprehensive attendance reporting
- Family notifications for minors
- Integration with Gate Activity
- Automated compliance documentation
- Access control enforcement

#### Deployment Modes
- **Area Mode**: Room/classroom monitoring
- **Gate Mode**: Room entry/exit points

#### Hardware Requirements
- IP Camera(s) (room and/or gate mounting)
- Network connectivity
- Central orchestration server
- Database for schedules and member lists
- Notification system (email/SMS)
- Reporting engine

#### Target Markets
- Schools and universities
- Gyms and fitness centers
- Industrial facilities
- Corporate offices
- Healthcare facilities

#### Metrics of Success
- Attendance accuracy
- Unauthorized access detection precision
- Report generation timeliness
- Family notification delivery
- Compliance documentation completeness
- System uptime (>99.5%)

#### Regulatory/Compliance Requirements
- COPPA compliance for minor notifications
- FERPA compliance for educational institutions
- HIPAA compliance for healthcare facilities
- Audit trail for access control
- Parent consent documentation for notifications

#### Beta Testing Plan
- Pilot in 2-3 facilities (school, corporate office, fitness center)
- Test attendance accuracy
- Validate unauthorized access detection
- Test family notification system
- Verify compliance report generation
- Gather operator feedback
- Test integration with Gate Activity

#### Next Steps
1. Finalize member management interface
2. Establish educational/corporate partnerships
3. Develop compliance documentation
4. Create automated report templates
5. Test family notification system
6. Launch Q2 2026

---

### 5. SENTINEL
**Status**: ✅ Beta Testing Ready  
**Target Launch**: Q2 2026

#### Purpose
Automated security personnel monitoring ensuring vigilant oversight at guard stations and dynamic security operations.

#### Product Variants

**Variant A: Fixed Station Monitoring**
- Permanent guard station oversight
- IP-based camera integration
- 24/7 operational monitoring

**Variant B: Mobile Variant** ⭐ ***VIP Protection & Dynamic Security Perimeters***
- **EyeNet mobile camera + tablet** configuration
- Establish security perimeters on the fly for VIP protections
- Deploy quickly for executive protection details, high-value events, and temporary security operations
- Mobile security teams can configure and activate monitoring in minutes
- Tablet-based dashboard for real-time threat assessment and guard coordination
- Flexible positioning for evolving security scenarios

#### Key Features
- Customizable activity detection rules
- Instant alerts for activity/inactivity violations
- Live video streaming with annotations
- Shift-based monitoring configuration
- Guard accountability documentation
- Configurable alert thresholds
- **Mobile variant**: Portable setup with tablet dashboard and wireless camera connectivity for on-the-go deployment

#### Deployment Modes

**Fixed Variant**:
- **Area Mode**: Guard station monitoring with dedicated overhead cameras

**Mobile Variant**:
- **Area Mode (Mobile)**: _Tablet + mobile camera for establishing security perimeters on the fly, VIP protection assignments, temporary security posts, and event security management_

#### Hardware Requirements

**Fixed Variant**:
- IP Camera (guard station overhead mounting)
- Network connectivity
- Central orchestration server
- Alert distribution system (audio/visual alerts)
- Management dashboard

**Mobile Variant**:
- EyeNet mobile camera
- Tablets (iPad/Android) for live monitoring and command
- Wireless connectivity (WiFi/4G)
- Mobile charging solution
- Alert distribution to security team devices

#### Target Markets

**Fixed Variant**:
- Security firms with dedicated guard stations
- Corporate offices with security centers
- Industrial plants
- Government buildings

**Mobile Variant**:
- Executive protection/VIP security details
- Private security firms (high-value assignments)
- Law enforcement special events
- Temporary security deployments
- Event security companies
- High-profile conference/summit security
- Convention center and venue security

#### Metrics of Success
- Guard activity detection accuracy
- Alert response time
- False alert rate
- Guard shift compliance
- System uptime (>99.5%)
- Accountability documentation completeness

#### Beta Testing Plan

**Fixed Variant**:
- Pilot in 2-3 security operations (corporate office, industrial facility)
- Test activity detection accuracy
- Validate alert system
- Measure false alert rates

**Mobile Variant**:
- Test with 2-3 executive protection/VIP security details
- Validate tablet usability for mobile security teams
- Test rapid deployment and perimeter establishment
- Validate wireless connectivity in mobile scenarios
- Test alert integration with mobile security team devices
- Measure response time for threat detection and team coordination
- Gather feedback from mobile security operations teams

#### Next Steps
1. Finalize activity detection rules configuration
2. Establish security firm partnerships
3. Create customizable alert templates
4. Develop shift management interface
5. Build accountability reporting
6. Launch Q2 2026

---

### 6. SECURITY OFFICER AGENT
**Status**: ⚠️ Software Complete - Hardware Development Required  
**Target Launch**: Q3/Q4 2026

#### Purpose
Mobile security enhancement through wearable technology, providing real-time alerts and centralized command integration for field operations.

#### Key Features (Software)
- Real-time audio alerts for persons of interest
- Activity annotations sent to central command
- Person of interest management from live feed
- Collaborative team operations
- Centralized command integration
- Live agent feed streaming

#### Deployment Modes
- **Goggles Mode**: Wearable camera eyewear (PRIMARY)
- **Drone Mode**: Aerial surveillance support

#### Hardware Requirements (Development Needed)
**Smart Glasses Specification**:
- **Camera Placement**: Single camera mounted between lenses
- **Resolution**: Minimum 1080p video capability
- **Field of View**: 90-120 degrees (typical eyewear FOV)
- **Computing**: Raspberry Pi 4 connected via cable at back of glasses
- **Battery**: Sufficient for 8-hour shift (glasses + RPi4)
- **Weight**: <200g for all-day wearability
- **Durability**: Impact-resistant frame, weatherproof if outdoor use
- **Connectivity**: Wireless (WiFi/4G) to central command

**Hardware Development Path**:
1. **Option A - Acquisition**: Source existing smart glasses platforms
   - Potential vendors: Meta Ray-Bans (modify), Vuzix (modify), North Focal USB
   - Timeline: 4-6 weeks
   - Budget: $500-2000 per unit

2. **Option B - Lab Development** (Recommended for customization)
   - Design custom frame with camera mount between lenses
   - Bracket system for RPi4 mounting at back
   - Cable management and strain relief
   - Custom firmware for camera integration
   - Battery harness design
   - Field testing and refinement
   - Timeline: 12-16 weeks
   - Budget: $3000-5000 for 2-3 prototypes

#### Target Markets
- Security agencies
- Law enforcement
- Private security firms
- Event security teams
- Crowd management operations

#### Metrics of Success (Software)
- Alert delivery latency to agent
- Central command response time
- Person of interest matching accuracy
- Team communication effectiveness
- Wearable comfort/usability rating
- Battery life in field conditions

#### Hardware Development Blockers
- **Smart glasses design and manufacturing**
- **RPi4 integration and mounting**
- **Camera optical alignment**
- **Battery management system**
- **Thermal management under load**
- **Field durability testing**

#### Development Roadmap
**Phase 1: Specification & Prototyping (Weeks 1-4)**
- Finalize smart glasses specifications
- Source camera module
- Obtain sample frames/materials
- Design in CAD (mounting brackets, cable management)

**Phase 2: Integration & Testing (Weeks 5-12)**
- Integrate camera with RPi4
- Build custom frame modifications
- Test connectivity and performance
- Thermal and durability testing
- Refine design based on testing

**Phase 3: Beta Development (Weeks 13-16)**
- Manufacture 2-3 beta units
- Field test with security partners
- Gather feedback on wearability
- Document design for manufacturing

**Phase 4: Manufacturing & Launch (Q3/Q4 2026)**
- Finalize design for production
- Establish manufacturing partnership
- Prepare beta testing with field team
- Launch Q3/Q4 2026

#### Next Steps (Immediate)
1. **Approve smart glasses development budget and timeline**
2. **Initiate vendor research (acquisition vs. custom development)**
3. **Assign hardware development lead**
4. **Establish security partner for field testing**
5. **Begin design specifications and CAD work**
6. **Validate software API compatibility with wearable hardware**

#### Critical Success Factors
- **Wearability**: Must be comfortable for 8-12 hour shifts
- **Battery Life**: Minimum 8-10 hours continuous operation
- **Durability**: Handle active field use in varied conditions
- **Reliability**: >99.5% uptime for mission-critical use
- **Integration**: Seamless connection to central command
- **Cost**: Target <$3000 per complete unit (RPi4 + glasses + camera)

---

## Cross-Product Launch Strategy

### Phase 1: Q2 2026 (5 Products Launch)
- Intelligent Signage
- Underage Detector
- Gate Activity
- Room & Gate Protection
- Sentinel

**Launch Activities**:
- Beta testing completion for all 5 products
- Create product marketing materials
- Establish sales channels for each vertical market
- Develop industry-specific case studies
- Launch go-to-market campaigns

### Phase 2: Q3/Q4 2026 (Security Officer Agent)
- Smart glasses prototype completion
- Field testing with security partners
- Software integration completion
- Product launch with hardware availability

---

## Resource Requirements Summary

| Product | Development | Beta Testing | Launch |
|---------|------------|-------------|--------|
| Intelligent Signage | Complete | Now | Q2 2026 |
| Underage Detector | Complete | Now | Q2 2026 |
| Gate Activity | Complete | Now | Q2 2026 |
| Room & Gate Protection | Complete | Now | Q2 2026 |
| Sentinel | Complete | Now | Q2 2026 |
| Security Officer Agent | Complete | Pending Hardware | Q3/Q4 2026 |

---

## Notes & Assumptions
- All software development for 5 primary products is complete and ready for beta testing
- Hardware for first 5 products is assumed to be standard IP camera + network infrastructure
- Security Officer Agent hardware development is critical path item for Q3/Q4 launch
- Custom smart glasses development is recommended over acquisition for IP protection and customization
- All products require proper deployment site partnerships for realistic beta testing
- Regulatory compliance is key consideration for Room & Gate Protection and Underage Detector products

---

*Product Roadmap - PPL Meta  
February 15, 2026*
