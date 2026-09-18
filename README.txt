===============================================================================
THORNE-ZYTKOW OBJECT (TZO) 3D INSPIRAL & EQUILIBRIUM SIMULATION
===============================================================================

1. PROJECT OVERVIEW
-------------------------------------------------------------------------------
This project is an interactive, real-time 3D astrophysical simulation modeling 
the formation, internal structure, and potential collapse of a theoretical 
hybrid star known as a Thorne-Zytkow Object (TZO). 

The simulation computes volumetric light transport and gas dynamics in real 
time at 60 FPS using custom GLSL shaders, Python, Pygame, and ModernGL.


2. WHAT IS A THORNE-ZYTKOW OBJECT (TZO)?
-------------------------------------------------------------------------------
First theorized by physicists Kip Thorne and Anna Zytkow in 1977, a Thorne-
Zytkow Object is an exotic stellar hybrid formed when a compact, degenerate 
stellar remnant (a neutron star) spirals into the interior of a massive giant 
star (such as a red supergiant) and settles directly at its core.

Key astrophysical distinctions of a TZO:
- Core Engine: Unlike normal stars powered by thermonuclear fusion of hydrogen 
  or helium (such as the CNO cycle), a TZO is powered by hyper-critical, 
  neutrino-cooled accretion of envelope gas directly onto the degenerate neutron core.
- rp-Process Nucleosynthesis: Surrounding the neutron core is an ultra-dense, 
  convective mantle undergoing rapid proton capture (rp-process) nucleosynthesis. 
  This unusual burning regime produces anomalous surface overabundances of 
  heavy elements such as Lithium (Li), Rubidium (Rb), and Molybdenum (Mo).
- Appearance: From the outside, a TZO resembles a standard luminous red 
  supergiant, but its interior dynamics, convective speeds, and evolutionary 
  lifespans are radically different.


3. EVOLUTIONARY STAGES IN THE SIMULATION
-------------------------------------------------------------------------------
The simulation models three sequential physical regimes, along with an 
optional catastrophe branch:

STAGE 1: DETACHED BINARY ORBIT
- The compact neutron star companion orbits outside the red supergiant's outer 
  photosphere.
- Orbital separation decays gradually due to tidal interactions and wind drag.

STAGE 2: COMMON-ENVELOPE EVOLUTION (CEE) PLUNGE
- The companion plunges directly into the star's extended convective mantle.
- Supersonic Bondi-Hoyle-Lyttleton (BHL) hydrodynamic drag transfers orbital 
  angular momentum into thermal energy, accelerating the inspiral inward 
  toward the core.

STAGE 3: STABLE TZO EQUILIBRIUM
- The neutron star merges with the central core region, forming a stable TZO.
- The core stabilizes into hydrostatic equilibrium, glowing as a white-cyan 
  degenerate engine enveloped by a distinct violet/purple rp-process burning 
  mantle.

WHAT-IF BRANCH: SUPERNOVA COLLAPSAR & KERR BLACK HOLE
- Toggled at any time via the [B] key.
- Simulates what occurs if hyper-critical accretion forces the degenerate core 
  past the Tolman-Oppenheimer-Volkoff (TOV) mass limit (~2.2 - 2.5 Solar Masses).
- Degeneracy pressure fails, triggering an inward mantle implosion, a hypernova 
  detonation, and the emergence of a rapidly rotating Kerr black hole with 
  relativistic Doppler beaming, gravitationally lensed accretion disk arches, 
  and twin polar relativistic jets.


4. SYSTEM REQUIREMENTS
-------------------------------------------------------------------------------
- Python: Version 3.8 or newer
- GPU: Dedicated or integrated graphics supporting OpenGL 3.3 Core Profile
- Required Python Packages:
    * pygame
    * moderngl


5. HOW TO INSTALL AND RUN
-------------------------------------------------------------------------------
Step 1: Open your terminal or command prompt and navigate to the project directory:
    cd path/to/project_folder

Step 2: Install the required dependencies:
    pip install pygame moderngl

Step 3: Run the simulation script:
    python tzo_sim.py


6. CONTROLS REFERENCE
-------------------------------------------------------------------------------
NAVIGATION:
- Arrow Keys or W / A / S / D : Orbit camera around the system (360-degree view)
- Q / E or + / -             : Zoom camera in / out
- Left Mouse Drag             : Orbit camera smoothly using mouse
- Mouse Scroll Wheel          : Zoom camera smoothly using mouse

SIMULATION CONTROLS:
- Spacebar : Pause / Resume simulation time and orbital decay
- X        : Toggle Conical Cutaway View (exposes the central engine & mantle)
- B        : Trigger / Revert "What-If" Supernova Collapse (Kerr Black Hole)
- V        : Toggle companion orbital velocity vector overlay
- R        : Reset simulation back to initial pre-merger binary stage
- H / Tab  : Show / Hide real-time telemetry HUD overlay
- Esc      : Exit application


7. VISUAL & TECHNICAL ARCHITECTURE
-------------------------------------------------------------------------------
- Volumetric Raymarching: Rather than static polygon meshes, the star's mantle 
  and turbulent convective cells are generated via 3D fractional Brownian 
  simplex noise and raymarched step-by-step in a GLSL fragment shader.
- Radiative Transfer: Employs Beer-Lambert light extinction through the 
  stellar plasma density gradients.
- Color Pipeline: Uses an Academy Color Encoding System (ACES) filmic tone 
  mapper to map high-dynamic-range irradiance into displayable colors without 
  blowing out highlights or clipping saturated glows.
- Deep Space Backdrop: Features a mathematically rendered celestial sphere 
  incorporating procedural globular star clusters and foreground stars with 
  4-point optical diffraction spikes.
===============================================================================