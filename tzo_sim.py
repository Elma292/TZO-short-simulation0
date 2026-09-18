import sys
import math
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pygame
import moderngl
from array import array

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 1440, 900
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("Thorne-Zytkow Object (TZO) Inspiral & Equilibrium Simulation")
ctx = moderngl.create_context()
ctx.enable(moderngl.BLEND)
ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

quad_data = array('f', [
    -1.0, -1.0, 0.0, 0.0,
     1.0, -1.0, 1.0, 0.0,
    -1.0,  1.0, 0.0, 1.0,
     1.0,  1.0, 1.0, 1.0,
])

VERT_SHADER = """
#version 330 core
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

FRAG_SHADER = """
#version 330 core
out vec4 fragColor;
in vec2 v_uv;

uniform vec2  u_res;
uniform float u_time;
uniform vec3  u_ro;
uniform vec3  u_cam_fwd;
uniform vec3  u_cam_up;
uniform vec3  u_cam_right;
uniform vec3  u_ns_pos;
uniform vec3  u_core_pos;
uniform float u_r_orbit;
uniform float u_envelope_r;
uniform float u_core_r;
uniform float u_tzo_settled;
uniform int   u_cutaway;
uniform int   u_mode;
uniform float u_collapse_timer;

vec4 permute(vec4 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v){
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + 1.0 * C.xxx;
    vec3 x2 = x0 - i2 + 2.0 * C.xxx;
    vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
                i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3  ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ *ns.x + ns.yyyy;
    vec4 y = y_ *ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}

float solarTurbulence(vec3 p) {
    float v = 0.0;
    float a = 0.55;
    for (int i = 0; i < 4; ++i) {
        float n = 1.0 - abs(snoise(p));
        v += a * n * n;
        p = p * 2.25 + vec3(1.8, 3.4, 0.9);
        a *= 0.48;
    }
    return v;
}

float hash31(vec3 p) {
    p = fract(p * vec3(443.897, 441.423, 437.195));
    p += dot(p, p.yzx + 19.19);
    return fract((p.x + p.y) * p.z);
}

vec3 renderOmnidirectionalBackdrop(vec3 rd) {
    vec3 bg = vec3(0.0008, 0.001, 0.0016);

    vec3 grid_pos = rd * 260.0;
    vec3 id = floor(grid_pos);
    vec3 gv = fract(grid_pos) - 0.5;

    float h = hash31(id);
    if (h > 0.945) {
        float d = length(gv);
        float star_b = smoothstep(0.18, 0.0, d) * (0.5 + 1.8 * (h - 0.945) * 18.0);
        vec3 star_color = mix(vec3(0.75, 0.88, 1.0), vec3(1.0, 0.85, 0.65), fract(h * 123.45));
        bg += star_color * star_b;
    }

    vec3 grid_pos_fine = rd * 520.0;
    vec3 id_f = floor(grid_pos_fine);
    vec3 gv_f = fract(grid_pos_fine) - 0.5;
    float h_f = hash31(id_f);
    if (h_f > 0.978) {
        float d_f = length(gv_f);
        bg += vec3(0.85, 0.92, 1.0) * smoothstep(0.16, 0.0, d_f) * 0.45;
    }

    vec3 cluster_1 = normalize(vec3(-0.45, 0.25, -0.85));
    float d_c1 = acos(clamp(dot(rd, cluster_1), -1.0, 1.0));
    bg += vec3(0.9, 0.94, 1.05) * (exp(-d_c1 * 11.5) * 0.25);

    vec3 cluster_grid = rd * 680.0;
    vec3 cid = floor(cluster_grid);
    vec3 cgv = fract(cluster_grid) - 0.5;
    float chash = hash31(cid);
    if (chash < exp(-d_c1 * 9.0) * 0.75) {
        bg += mix(vec3(0.8, 0.9, 1.0), vec3(1.0, 0.9, 0.7), fract(chash * 31.4)) * smoothstep(0.20, 0.0, length(cgv));
    }

    vec3 cluster_2 = normalize(vec3(0.72, -0.38, 0.58));
    float d_c2 = acos(clamp(dot(rd, cluster_2), -1.0, 1.0));
    bg += vec3(1.0, 0.82, 0.65) * exp(-d_c2 * 14.0) * 0.18;

    vec3 s1_pos = normalize(vec3(0.38, 0.46, -0.80));
    float s1_d = length(rd - s1_pos);
    if (s1_d < 0.14) {
        float halo = 0.00045 / (s1_d * s1_d + 0.00014);
        vec3 to_s1 = rd - s1_pos;
        float spike1 = smoothstep(0.0022, 0.0, abs(to_s1.x + to_s1.y * 0.2)) * smoothstep(0.065, 0.0, abs(to_s1.y));
        float spike2 = smoothstep(0.0022, 0.0, abs(to_s1.y - to_s1.x * 0.2)) * smoothstep(0.065, 0.0, abs(to_s1.x));
        bg += (vec3(0.65, 0.88, 1.4) * halo + vec3(1.1, 1.2, 1.4) * (spike1 + spike2) * 1.4);
    }

    vec3 s2_pos = normalize(vec3(-0.65, -0.28, -0.70));
    float s2_d = length(rd - s2_pos);
    if (s2_d < 0.12) {
        float halo = 0.00035 / (s2_d * s2_d + 0.00015);
        vec3 to_s2 = rd - s2_pos;
        float spike1 = smoothstep(0.0022, 0.0, abs(to_s2.x)) * smoothstep(0.055, 0.0, abs(to_s2.y));
        float spike2 = smoothstep(0.0022, 0.0, abs(to_s2.y)) * smoothstep(0.055, 0.0, abs(to_s2.x));
        bg += (vec3(1.6, 0.7, 0.2) * halo + vec3(1.4, 0.9, 0.5) * (spike1 + spike2) * 1.3);
    }

    return bg;
}

// Kerr Black Hole Shader: Mathematically replicates the Gyoto / Reference Accretion Disk & Lensing Arches
vec4 evaluateKerrBlackHole(vec2 p_local, float r_core) {
    float r = length(p_local);
    float rh = r_core * 0.58; // Radius of event horizon

    // Asymmetric Kerr Shadow (Flattened on left due to frame dragging)
    float kerr_boundary = rh * (1.0 + 0.08 * (p_local.x / (r + 0.0001)));
    if (r < kerr_boundary) {
        return vec4(0.0, 0.0, 0.0, 1.0); // Inside event horizon: pure black
    }

    float isco = rh * 1.04;
    float r_out = r_core * 2.30;

    // Relativistic Doppler beaming gradient
    float cos_theta = p_local.x / (r + 0.0001);
    float doppler_factor = clamp(1.0 - 0.72 * cos_theta, 0.18, 2.2);
    float beaming = pow(doppler_factor, 2.8);

    // 1. Equatorial Primary Disk Plane
    float r_eq = sqrt(p_local.x * p_local.x + pow(p_local.y / 0.22, 2.0));
    float disk_body = smoothstep(isco, isco + 0.025, r_eq) * smoothstep(r_out, isco, r_eq) * exp(-abs(p_local.y) * 38.0);

    // 2. Gravitationally Bent Upper Arc (Behind hole warped over the top)
    float y_top_bent = p_local.y - sqrt(max(0.0, r * r - p_local.x * p_local.x * 0.92)) * 0.54;
    float r_top_arch = sqrt(p_local.x * p_local.x + pow(y_top_bent / 0.38, 2.0));
    float arch_top = smoothstep(isco, isco + 0.035, r_top_arch) * smoothstep(r_out * 0.82, isco, r_top_arch) * smoothstep(-0.01, 0.05, p_local.y);

    // 3. Gravitationally Bent Lower Arc (Behind hole warped under the bottom)
    float y_bot_bent = p_local.y + sqrt(max(0.0, r * r - p_local.x * p_local.x * 0.88)) * 0.44;
    float r_bot_arch = sqrt(p_local.x * p_local.x + pow(y_bot_bent / 0.34, 2.0));
    float arch_bot = smoothstep(isco, isco + 0.035, r_bot_arch) * smoothstep(r_out * 0.70, isco, r_bot_arch) * smoothstep(0.01, -0.05, p_local.y);

    float combined_disk = disk_body * 1.6 + arch_top * 1.4 + arch_bot * 1.0;

    // Color gradient: Warm ember -> Golden yellow -> Incandescent white-gold hotspot
    vec3 deep_red   = vec3(0.90, 0.07, 0.005);
    vec3 warm_amber = vec3(3.5, 1.1, 0.06);
    vec3 beam_white = vec3(7.5, 6.8, 4.8);

    vec3 disk_color = mix(deep_red, warm_amber, smoothstep(0.3, 1.3, beaming));
    disk_color = mix(disk_color, beam_white, smoothstep(1.5, 2.6, beaming) * combined_disk);

    // Relativistic Photon Ring right along the shadow edge
    float photon_ring = exp(-abs(r - kerr_boundary * 1.025) * 180.0) * 2.5 * (0.6 + 0.4 * beaming);
    disk_color += vec3(1.8, 1.5, 1.1) * photon_ring;

    return vec4(disk_color * combined_disk + vec3(1.8, 1.5, 1.1) * photon_ring, combined_disk + photon_ring);
}

void main() {
    vec2 flipped_coord = vec2(gl_FragCoord.x, u_res.y - gl_FragCoord.y);
    vec2 p = (flipped_coord - 0.5 * u_res) / u_res.y;

    vec3 ro = u_ro;
    vec3 rd = normalize(u_cam_fwd * 1.30 + u_cam_right * p.x + u_cam_up * p.y);

    vec3 bg_color = renderOmnidirectionalBackdrop(rd);

    int steps = 68;
    float step_len = 0.044;
    vec3 col = vec3(0.0);
    float trans = 1.0;

    vec3 cutaway_dir = -u_cam_fwd;

    float c_time = u_collapse_timer;
    float implosion = smoothstep(0.0, 1.0, c_time) * (1.0 - smoothstep(1.0, 2.0, c_time));
    float blast_expand = smoothstep(1.0, 4.0, c_time);
    float active_envelope_r = u_envelope_r * (1.0 - 0.14 * implosion) + blast_expand * 0.65;

    // THE FIX: Envelope clears out completely as the collapsar forms
    float envelope_dissipation = smoothstep(3.2, 0.8, c_time);

    float t_start = max(0.5, length(u_core_pos - ro) - active_envelope_r * 1.35);

    // Raymarching Loop (Only runs while envelope is still present)
    if (envelope_dissipation > 0.01) {
        for (int i = 0; i < steps; i++) {
            vec3 pos = ro + rd * (t_start + float(i) * step_len);

            vec3 rel = pos - u_core_pos;
            float d_core = length(rel);
            float d_ns   = length(pos - u_ns_pos);

            // Conical cutaway portal
            if (u_cutaway == 1 && c_time < 1.0) {
                float forward_proj = dot(rel, cutaway_dir);
                if (forward_proj > -0.05) {
                    float perp_dist = length(rel - cutaway_dir * forward_proj);
                    if (perp_dist < (forward_proj * 0.95 + 0.08)) {
                        continue;
                    }
                }
            }

            // 1. CENTRAL ENGINE (Pre-collapse only)
            float core_boundary = u_core_r + 0.06;
            if (d_core < core_boundary && c_time < 1.0) {
                float core_glow = smoothstep(core_boundary, 0.0, d_core);
                
                vec3 core_normal = mix(vec3(4.5, 1.2, 0.05), vec3(8.5, 3.8, 0.4), core_glow);
                vec3 purple_mantle = mix(vec3(0.40, 0.05, 0.75), vec3(2.2, 0.5, 3.2), core_glow);
                vec3 white_cyan_star = vec3(10.0, 11.5, 14.0);
                vec3 tzo_core_engine = mix(purple_mantle, white_cyan_star, smoothstep(0.38, 0.92, core_glow));
                
                vec3 active_core = mix(core_normal, tzo_core_engine, u_tzo_settled);

                col += active_core * core_glow * trans * (0.55 + u_tzo_settled * 0.45);
                trans *= max(0.0, 1.0 - core_glow * 1.6);
                if (trans < 0.02) break;
            }

            // 2. CONVECTIVE ENVELOPE
            float norm_r = d_core / active_envelope_r;
            if (norm_r < 1.14) {
                float turb = solarTurbulence(pos * 3.4 + vec3(0.0, u_time * 0.12, u_time * 0.05));
                float envelope_dens = pow(max(0.0, 1.0 - norm_r * 0.88), 1.5) * (0.40 + turb * 0.95) * envelope_dissipation;

                if (u_tzo_settled < 0.95 && d_ns < 0.75 && c_time == 0.0) {
                    float wake = smoothstep(0.45, 0.02, d_ns);
                    envelope_dens += wake * 0.38 * turb * (1.0 - u_tzo_settled);
                }

                if (envelope_dens > 0.008) {
                    vec3 ruby_crust   = vec3(0.85, 0.02, 0.001);
                    vec3 solar_amber  = vec3(3.2, 0.75, 0.03);
                    vec3 bright_cell  = vec3(6.5, 3.8, 0.8);

                    vec3 fire = mix(ruby_crust, solar_amber, smoothstep(0.06, 0.42, envelope_dens));
                    fire = mix(fire, bright_cell, smoothstep(0.42, 0.95, envelope_dens));

                    if (u_tzo_settled > 0.1 && norm_r < 0.45 && c_time < 0.8) {
                        float inner_tzo = smoothstep(0.45, 0.15, norm_r) * u_tzo_settled;
                        fire = mix(fire, vec3(1.2, 0.2, 2.2), inner_tzo * 0.7);
                    }

                    if (c_time > 0.8 && c_time < 2.5) {
                        float shock_wave = smoothstep(0.8, 1.5, c_time) * (1.0 - smoothstep(1.5, 2.5, c_time));
                        fire = mix(fire, vec3(4.0, 2.4, 1.0), shock_wave * 0.5);
                    }

                    float absorb = envelope_dens * step_len * 4.6;
                    col += fire * absorb * trans;
                    trans *= exp(-absorb * 2.5);
                    if (trans < 0.02) break;
                }
            }
        }
    }

    col += bg_color * trans;

    // 3. COLLAPSED KERR BLACK HOLE ACCRETION DISK
    if (c_time > 0.6) {
        vec3 to_core = u_core_pos - ro;
        float dist_cam_core = dot(to_core, u_cam_fwd);
        if (dist_cam_core > 0.1) {
            vec2 core_proj = vec2(dot(to_core, u_cam_right), dot(to_core, u_cam_up)) / dist_cam_core * 1.30;
            vec2 p_bh = p - core_proj;

            float bh_onset = smoothstep(0.6, 2.2, c_time);
            vec4 kerr = evaluateKerrBlackHole(p_bh, u_core_r);

            // Cleanly overlay the lensed accretion disk
            if (kerr.a > 0.001) {
                col = mix(col, kerr.rgb, bh_onset * smoothstep(0.0, 0.15, kerr.a));
            }
            // Event horizon silhouette (pure pitch black, masks all background and jets)
            float rh = u_core_r * 0.58 * (1.0 + 0.08 * (p_bh.x / (length(p_bh) + 0.0001)));
            if (length(p_bh) < rh) {
                col = mix(col, vec3(0.0), bh_onset);
            }
        }
    }

    // 4. RELATIVISTIC POLAR JETS (Masked outside the event horizon)
    if (c_time > 1.0 && c_time < 4.0) {
        vec3 to_core = ro - u_core_pos;
        vec3 jet_dir = vec3(0.0, 1.0, 0.0);
        vec3 closest_pt = ro + rd * dot(u_core_pos - ro, rd);
        float d_beam = length(cross(closest_pt - u_core_pos, jet_dir));

        vec2 core_proj = vec2(dot(u_core_pos - ro, u_cam_right), dot(u_core_pos - ro, u_cam_up)) / dot(u_core_pos - ro, u_cam_fwd) * 1.30;
        float p_dist = length(p - core_proj);

        // Jets only show outside the shadow
        if (p_dist > (u_core_r * 0.58)) {
            float jet_strength = smoothstep(1.0, 1.8, c_time) * (1.0 - smoothstep(2.5, 4.0, c_time));
            float beam_glow = exp(-d_beam * 18.0) * smoothstep(1.8, 0.1, abs(closest_pt.y - u_core_pos.y));
            col += vec3(0.3, 0.65, 2.2) * beam_glow * jet_strength * 1.4;
        }
    }

    // 5. PRE-MERGER COMPANION
    if (u_tzo_settled < 0.98 && c_time == 0.0) {
        vec3 to_ns = u_ns_pos - ro;
        float dist_cam_ns = dot(to_ns, u_cam_fwd);
        if (dist_cam_ns > 0.1) {
            vec2 ns_proj = vec2(dot(to_ns, u_cam_right), dot(to_ns, u_cam_up)) / dist_cam_ns * 1.30;
            float dist_to_ns = length(p - ns_proj);

            float occlude = (dot(u_ns_pos - u_core_pos, u_cam_fwd) < 0.0 && length(u_ns_pos - u_core_pos) < u_envelope_r * 0.8) ? 0.08 : 1.0;
            float fade = (1.0 - u_tzo_settled * 0.9);

            vec2 jet_axis = normalize(vec2(0.55, 0.84));
            vec2 delta_p = p - ns_proj;
            float proj_jet = abs(dot(delta_p, jet_axis));
            float perp_jet = length(delta_p - jet_axis * dot(delta_p, jet_axis));
            
            float jet_beam = smoothstep(0.006, 0.0, perp_jet) * smoothstep(0.09, 0.015, proj_jet) * 1.8;

            float r_mag = length(delta_p);
            float angle_mag = abs(dot(normalize(delta_p + 0.0001), jet_axis));
            float dipole_shape = abs(r_mag - 0.028 * (1.0 - angle_mag * angle_mag));
            float mag_field = smoothstep(0.003, 0.0, dipole_shape) * smoothstep(0.045, 0.008, r_mag) * 0.9;

            float ns_core = smoothstep(0.010, 0.002, dist_to_ns);
            float ns_halo = 0.0018 / (dist_to_ns * dist_to_ns + 0.00012);
            float ns_wide = 0.008 / (dist_to_ns + 0.06);

            vec3 base_ns = vec3(0.25, 0.65, 2.2) * ns_halo + vec3(0.08, 0.22, 0.75) * ns_wide + vec3(6.5, 7.5, 9.0) * ns_core;
            vec3 jets    = vec3(0.45, 0.85, 3.2) * jet_beam + vec3(0.2, 0.5, 1.8) * mag_field;

            col += (base_ns + jets) * occlude * fade;
        }
    }

    // ACES Tone Mapping
    vec3 x = col;
    col = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);

    fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""

prog = ctx.program(vertex_shader=VERT_SHADER, fragment_shader=FRAG_SHADER)
vbo = ctx.buffer(quad_data)
vao = ctx.simple_vertex_array(prog, vbo, 'in_pos', 'in_uv')
prog['u_res'].value = (WIDTH, HEIGHT)

ui_texture = ctx.texture((WIDTH, HEIGHT), 4)
ui_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

UI_VERT = """
#version 330 core
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = vec2(in_uv.x, 1.0 - in_uv.y);
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""
UI_FRAG = """
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_ui_tex;
void main() {
    fragColor = texture(u_ui_tex, v_uv);
}
"""
ui_prog = ctx.program(vertex_shader=UI_VERT, fragment_shader=UI_FRAG)
ui_prog['u_ui_tex'].value = 0
ui_vao = ctx.simple_vertex_array(ui_prog, vbo, 'in_pos', 'in_uv')

M_star = 12.0
M_ns = 1.4
BASE_PHOTOSPHERE = 1.38
R_photosphere = BASE_PHOTOSPHERE
R_core = 0.24

INITIAL_SEPARATION = 2.85
r_orbit = INITIAL_SEPARATION
theta = 3.2
sim_time_years = 0.0

running_sim = True
cutaway_active = True
visual_mode = 0
show_vectors = False
ui_visible = True
elapsed_sim_time = 0.0
tzo_settled = 0.0

collapse_triggered = False
collapse_timer = 0.0

cam_target = [0.45, 0.0, 0.0]
cam_dist = 6.4
cam_yaw = 0.0
cam_pitch = 0.0

clock = pygame.time.Clock()
font_mono = pygame.font.SysFont("Consolas", 14)
font_comm = pygame.font.SysFont("Consolas", 13)
font_title = pygame.font.SysFont("Consolas", 16, bold=True)

buttons_registry = []

def draw_hud_panel(surface, x, y, w, h, title, lines, buttons=None, commentary=None, is_collapsible=False):
    global buttons_registry
    panel_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, (8, 16, 28, 225), (0, 0, w, h), border_radius=6)
    pygame.draw.rect(panel_surf, (40, 110, 180, 220), (0, 0, w, h), width=1, border_radius=6)
    
    t_surf = font_title.render(f"v {title}", True, (210, 235, 255))
    panel_surf.blit(t_surf, (14, 12))
    
    if is_collapsible:
        hide_lbl = font_mono.render("[Hide: H]", True, (130, 180, 230))
        hw, hh = hide_lbl.get_width() + 10, hide_lbl.get_height() + 4
        hx = w - hw - 10
        hy = 10
        pygame.draw.rect(panel_surf, (20, 60, 100, 180), (hx, hy, hw, hh), border_radius=3)
        pygame.draw.rect(panel_surf, (45, 120, 200, 200), (hx, hy, hw, hh), width=1, border_radius=3)
        panel_surf.blit(hide_lbl, (hx + 5, hy + 2))
        buttons_registry.append((pygame.Rect(x + hx, y + hy, hw, hh), 'TOGGLE_UI'))

    cur_y = 40
    for row in lines:
        if row == "---":
            pygame.draw.line(panel_surf, (30, 80, 130, 150), (14, cur_y + 4), (w - 14, cur_y + 4), 1)
            cur_y += 12
            continue
        label, val = row
        l_surf = font_mono.render(label, True, (140, 185, 225))
        v_surf = font_mono.render(val, True, (230, 245, 255))
        panel_surf.blit(l_surf, (14, cur_y))
        panel_surf.blit(v_surf, (190, cur_y))
        cur_y += 18

    if commentary:
        cur_y += 6
        comm_box_h = 80
        pygame.draw.rect(panel_surf, (14, 28, 48, 200), (14, cur_y, w - 28, comm_box_h), border_radius=4)
        pygame.draw.rect(panel_surf, (50, 140, 220, 120), (14, cur_y, w - 28, comm_box_h), width=1, border_radius=4)
        
        c_title = font_comm.render("ASTROPHYSICAL COMMENTARY:", True, (255, 200, 80))
        panel_surf.blit(c_title, (22, cur_y + 6))
        
        words = commentary.split(" ")
        lines_wrapped = []
        cur_line = ""
        for word in words:
            test_line = f"{cur_line} {word}".strip()
            if font_comm.size(test_line)[0] < (w - 50):
                cur_line = test_line
            else:
                lines_wrapped.append(cur_line)
                cur_line = word
        if cur_line:
            lines_wrapped.append(cur_line)

        text_y = cur_y + 26
        for line in lines_wrapped[:2]:
            c_surf = font_comm.render(line, True, (200, 230, 255))
            panel_surf.blit(c_surf, (22, text_y))
            text_y += 18

        cur_y += comm_box_h + 8

    if buttons:
        cur_y += 4
        for btn_text, btn_key in buttons:
            b_surf = font_mono.render(btn_text, True, (170, 220, 255))
            bw, bh = b_surf.get_width() + 16, b_surf.get_height() + 8
            pygame.draw.rect(panel_surf, (25, 75, 125, 180), (14, cur_y, bw, bh), border_radius=4)
            pygame.draw.rect(panel_surf, (50, 140, 220, 220), (14, cur_y, bw, bh), width=1, border_radius=4)
            panel_surf.blit(b_surf, (22, cur_y + 4))
            buttons_registry.append((pygame.Rect(x + 14, y + cur_y, bw, bh), btn_key))
            cur_y += bh + 6

    surface.blit(panel_surf, (x, y))

def draw_collapsed_tab(surface, x, y):
    global buttons_registry
    lbl = font_mono.render("> Show Controls & Telemetry [H]", True, (180, 225, 255))
    w, h = lbl.get_width() + 20, lbl.get_height() + 12
    tab_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(tab_surf, (8, 16, 28, 220), (0, 0, w, h), border_radius=5)
    pygame.draw.rect(tab_surf, (40, 120, 210, 230), (0, 0, w, h), width=1, border_radius=5)
    tab_surf.blit(lbl, (10, 6))
    buttons_registry.append((pygame.Rect(x, y, w, h), 'TOGGLE_UI'))
    surface.blit(tab_surf, (x, y))

tobytes_fn = getattr(pygame.image, "tobytes", None)
if not tobytes_fn:
    tobytes_fn = lambda surf: pygame.image.tostring(surf, "RGBA")
else:
    tobytes_fn = lambda surf: pygame.image.tobytes(surf, "RGBA")

def handle_action(action_code):
    global running_sim, cutaway_active, visual_mode, show_vectors, collapse_triggered, collapse_timer, r_orbit, theta, sim_time_years, M_ns, ui_visible, tzo_settled, R_photosphere, cam_yaw, cam_pitch, cam_dist
    if action_code == 'SPACE':
        running_sim = not running_sim
    elif action_code == 'R':
        r_orbit = INITIAL_SEPARATION
        theta = 3.2
        sim_time_years = 0.0
        tzo_settled = 0.0
        R_photosphere = BASE_PHOTOSPHERE
        collapse_triggered = False
        collapse_timer = 0.0
        cam_yaw = 0.0
        cam_pitch = 0.0
        cam_dist = 6.4
    elif action_code == 'C':
        visual_mode = 1 if visual_mode == 0 else 0
    elif action_code == 'X':
        cutaway_active = not cutaway_active
    elif action_code == 'V':
        show_vectors = not show_vectors
    elif action_code == 'B':
        if tzo_settled < 0.9:
            tzo_settled = 1.0
            r_orbit = 0.02
        collapse_triggered = not collapse_triggered
        if not collapse_triggered:
            collapse_timer = 0.0
    elif action_code == 'TOGGLE_UI':
        ui_visible = not ui_visible

# ==========================================
# MAIN LOOP
# ==========================================
while True:
    dt = clock.tick(60) / 1000.0
    buttons_registry.clear()

    keys = pygame.key.get_pressed()
    cam_rot_speed = 1.35 * dt
    zoom_speed = 3.5 * dt

    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        cam_yaw -= cam_rot_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        cam_yaw += cam_rot_speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        cam_pitch = min(1.45, cam_pitch + cam_rot_speed)
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        cam_pitch = max(-1.45, cam_pitch - cam_rot_speed)
    if keys[pygame.K_q] or keys[pygame.K_EQUALS] or keys[pygame.K_KP_PLUS]:
        cam_dist = max(2.8, cam_dist - zoom_speed)
    if keys[pygame.K_e] or keys[pygame.K_MINUS] or keys[pygame.K_KP_MINUS]:
        cam_dist = min(15.0, cam_dist + zoom_speed)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key in (pygame.K_h, pygame.K_TAB):
                handle_action('TOGGLE_UI')
            elif event.key == pygame.K_SPACE:
                handle_action('SPACE')
            elif event.key == pygame.K_r:
                handle_action('R')
            elif event.key == pygame.K_c:
                handle_action('C')
            elif event.key == pygame.K_x:
                handle_action('X')
            elif event.key == pygame.K_v:
                handle_action('V')
            elif event.key == pygame.K_b:
                handle_action('B')
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn_rect, btn_key in buttons_registry:
                if btn_rect.collidepoint(event.pos):
                    handle_action(btn_key)
                    break

    v_orbital_kms = 32.0 * math.sqrt((M_star + M_ns) / max(0.1, r_orbit))

    if collapse_triggered and running_sim:
        collapse_timer += dt

    if collapse_triggered:
        if collapse_timer < 1.0:
            stage_name = "What-If Branch: Core Collapse"
            hydro_regime = "Gravitational Free-Fall of Degenerate Mantle"
            local_rho = 85.0
            tzo_status = "TOV Limit Exceeded (Degeneracy Broken)"
            stage_commentary = "Accretion exceeds 2.5 M_sun. Degeneracy pressure fails, triggering rapid inward mantle implosion."
        elif collapse_timer < 2.5:
            stage_name = "What-If Branch: Shock Detonation"
            hydro_regime = "Supernova Breakout & Relativistic Jet Eruption"
            local_rho = 240.0
            tzo_status = "Blandford-Znajek Relativistic Jets Active"
            stage_commentary = "Infalling matter powers a Kerr black hole engine. Polar GRB jets erupt as a hypernova shockwave detonates the star."
        else:
            stage_name = "What-If Branch: Kerr Black Hole"
            hydro_regime = "Lensed Accretion Torus + Gravitational Shadow"
            local_rho = 12.0
            tzo_status = "Kerr Singularity Formed (Relativistic Beaming)"
            stage_commentary = "Envelope dispersed. Kerr black hole with relativistic Doppler beaming and gravitational lensing arches exposed."
    elif r_orbit > R_photosphere:
        stage_name = "Stage 1: Detached Binary Orbit"
        hydro_regime = "Tidal Wind Accretion (Pre-CEE)"
        local_rho = 0.002 * math.exp(-(r_orbit - R_photosphere) * 2.5)
        drag_rate = 0.038
        tzo_status = "Pre-Inspiral Orbit"
        stage_commentary = "Stable detached Keplerian orbit. The neutron star companion siphons stellar wind without penetrating the outer photosphere."
    elif r_orbit > R_core * 1.15:
        stage_name = "Stage 2: Common-Envelope Plunge"
        hydro_regime = "Supersonic Bondi-Hoyle Shock Wake"
        normalized_depth = (R_photosphere - r_orbit) / (R_photosphere - R_core)
        local_rho = 0.05 + 2.2 * (normalized_depth ** 1.5)
        drag_rate = 0.048 + 0.075 * normalized_depth
        tzo_status = "Envelope Penetration"
        stage_commentary = "Supersonic BHL drag transfers orbital momentum into the convective mantle, rapidly driving the companion into the core."
    else:
        stage_name = "Stage 3: Stable TZO Equilibrium"
        hydro_regime = "Neutrino-Cooled rp-Process Core"
        local_rho = 15.2
        drag_rate = 0.005
        tzo_settled = min(1.0, tzo_settled + dt * 0.18)
        R_photosphere = min(BASE_PHOTOSPHERE * 1.18, R_photosphere + dt * 0.022)
        tzo_status = "Stable Equilibrium (rp-Nucleosynthesis)"
        stage_commentary = "Degenerate core achieves hydrostatic equilibrium powered by neutrino-cooled accretion and rapid proton capture."

    if running_sim and not collapse_triggered:
        elapsed_sim_time += dt
        sim_time_years += dt * 0.0014
        omega = (v_orbital_kms / 32.0) / max(0.18, r_orbit) * 0.46
        theta += omega * dt
        r_orbit = max(0.02, r_orbit - drag_rate * dt)
    elif running_sim and collapse_triggered:
        elapsed_sim_time += dt

    core_x, core_y, core_z = 0.45, 0.0, 0.0
    ns_x = core_x + r_orbit * math.cos(theta) * 1.15
    ns_y = core_y + r_orbit * math.sin(theta) * 0.45
    ns_z = r_orbit * math.sin(theta) * 0.40

    ro_x = cam_target[0] + cam_dist * math.cos(cam_pitch) * math.sin(cam_yaw)
    ro_y = cam_target[1] + cam_dist * math.sin(cam_pitch)
    ro_z = cam_target[2] + cam_dist * math.cos(cam_pitch) * math.cos(cam_yaw)
    cam_ro = (ro_x, ro_y, ro_z)

    fwd = [cam_target[0] - ro_x, cam_target[1] - ro_y, cam_target[2] - ro_z]
    fwd_len = math.sqrt(fwd[0]**2 + fwd[1]**2 + fwd[2]**2)
    fwd = [fwd[0]/fwd_len, fwd[1]/fwd_len, fwd[2]/fwd_len]

    world_up = [0.0, 1.0, 0.0]
    right = [fwd[1]*world_up[2] - fwd[2]*world_up[1],
             fwd[2]*world_up[0] - fwd[0]*world_up[2],
             fwd[0]*world_up[1] - fwd[1]*world_up[0]]
    right_len = math.sqrt(right[0]**2 + right[1]**2 + right[2]**2)
    right = [right[0]/right_len, right[1]/right_len, right[2]/right_len]

    up = [right[1]*fwd[2] - right[2]*fwd[1],
          right[2]*fwd[0] - right[0]*fwd[2],
          right[0]*fwd[1] - right[1]*fwd[0]]

    def safe_set(p, name, val):
        if name in p:
            p[name].value = val

    safe_set(prog, 'u_time', elapsed_sim_time)
    safe_set(prog, 'u_ro', cam_ro)
    safe_set(prog, 'u_cam_fwd', tuple(fwd))
    safe_set(prog, 'u_cam_up', tuple(up))
    safe_set(prog, 'u_cam_right', tuple(right))
    safe_set(prog, 'u_ns_pos', (ns_x, ns_y, ns_z))
    safe_set(prog, 'u_core_pos', (core_x, core_y, core_z))
    safe_set(prog, 'u_r_orbit', r_orbit)
    safe_set(prog, 'u_envelope_r', R_photosphere)
    safe_set(prog, 'u_core_r', R_core)
    safe_set(prog, 'u_tzo_settled', tzo_settled)
    safe_set(prog, 'u_cutaway', 1 if cutaway_active else 0)
    safe_set(prog, 'u_mode', visual_mode)
    safe_set(prog, 'u_collapse_timer', collapse_timer)

    ctx.clear(0.0, 0.0, 0.0, 1.0)
    vao.render(moderngl.TRIANGLE_STRIP)

    ui_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ui_surf.fill((0, 0, 0, 0))

    if ui_visible:
        telemetry_data = [
            ("Evolution Stage", f": {stage_name}"),
            ("Hydro Regime",    f": {hydro_regime}"),
            ("Cutaway View",    f": {'Active (Core Exposed)' if cutaway_active else 'Off (Envelope Sealed)'}"),
            "---",
            ("Orbital Separation", f": {r_orbit:.3f} AU ({r_orbit * 215.0:.0f} R_sun)"),
            ("Photosphere Radius", f": {R_photosphere:.3f} AU ({R_photosphere * 215.0:.0f} R_sun)"),
            ("Central Engine Radius",f": {R_core:.3f} AU ({R_core * 215.0:.0f} R_sun)"),
            ("Orbital Velocity",   f": {v_orbital_kms:.1f} km/s"),
            ("Evolutionary Fate",  f": {'Failed TZO -> Kerr Collapsar' if collapse_triggered else 'Canonical Thorne-Zytkow Object'}"),
            ("Status",             f": {tzo_status}"),
            ("Epoch Elapsed",      f": {sim_time_years:.4f} Years"),
        ]

        hud_buttons = [
            ("Pause / Resume (SPACE)", 'SPACE'),
            ("Reset Inspiral (R)", 'R'),
            ("Toggle Cutaway View (X)", 'X'),
            ("Toggle Vectors (V)", 'V'),
            (f"{'Revert to TZO' if collapse_triggered else 'Trigger Supernova Collapse'} (B)", 'B')
        ]

        draw_hud_panel(ui_surf, 32, 32, 510, 520, "TZO Evolutionary Telemetry", telemetry_data, hud_buttons, commentary=stage_commentary, is_collapsible=True)

        legend_data = [
            ("Host Star", ": Red Supergiant (12.0 M_sun)"),
            ("Envelope State", f": {'Dispersed Debris Field' if collapse_timer > 2.5 else f'Convective Mantle ({R_photosphere*215.0:.0f} R_sun)'}"),
            ("Central Engine", f": {'Lensed Kerr Disk & Shadow' if collapse_timer > 1.0 else ('rp-Process Mantle' if tzo_settled > 0.5 else 'Helium Core')}"),
            "---",
            ("Demo Control", ": Press 'B' to trigger Supernova Collapse"),
            ("Camera Navigation", ": Arrow Keys / WASD = Orbit | Q/E = Zoom"),
        ]
        draw_hud_panel(ui_surf, 32, HEIGHT - 190, 450, 160, "System Physical Parameters", legend_data)
    else:
        draw_collapsed_tab(ui_surf, 32, 32)

   

    if show_vectors and tzo_settled < 0.9 and not collapse_triggered:
        to_companion = [ns_x - cam_ro[0], ns_y - cam_ro[1], ns_z - cam_ro[2]]
        comp_depth = to_companion[0]*fwd[0] + to_companion[1]*fwd[1] + to_companion[2]*fwd[2]
        if comp_depth > 0.1:
            comp_ndc_x = (to_companion[0]*right[0] + to_companion[1]*right[1] + to_companion[2]*right[2]) / comp_depth * 1.30
            comp_ndc_y = (to_companion[0]*up[0]    + to_companion[1]*up[1]    + to_companion[2]*up[2])    / comp_depth * 1.30
            ns_screen_x = int(0.5 * WIDTH + comp_ndc_x * HEIGHT)
            ns_screen_y = int(0.5 * HEIGHT - comp_ndc_y * HEIGHT)

            vx_proj = -math.sin(theta) * 55
            vy_proj =  math.cos(theta) * 22
            pygame.draw.line(ui_surf, (0, 255, 255), (ns_screen_x, ns_screen_y), (int(ns_screen_x + vx_proj), int(ns_screen_y + vy_proj)), 2)
            ui_surf.blit(font_mono.render("v (orbital)", True, (0, 255, 255)), (int(ns_screen_x + vx_proj + 6), int(ns_screen_y + vy_proj - 8)))

    ui_texture.write(tobytes_fn(ui_surf))
    ui_texture.use(location=0)
    ui_vao.render(moderngl.TRIANGLE_STRIP)

    pygame.display.flip()