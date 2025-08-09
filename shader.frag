//GLSL

// Input from vertex shader
in vec2 texcoord;
in float world_z;

// Uniforms
uniform sampler2D p3d_Texture0; // This will be our slope map
uniform float osg_FrameTime; // Use time to make it dynamic

// Output color
out vec4 fragColor;

void main() {
    float slope = texture(p3d_Texture0, texcoord).r;

    // Psychedelic colors based on world height (Z) and time
    float time_factor = osg_FrameTime * 0.5;
    vec3 color = vec3(
        0.5 + 0.5 * sin(world_z * 0.1 + time_factor),
        0.5 + 0.5 * cos(world_z * 0.15 + time_factor * 1.2),
        0.5 + 0.5 * sin(world_z * 0.2 + time_factor * 0.8)
    );

    // Add distortion for steep slopes
    // If the slope is steep (value close to 1), make the colors more intense and distorted
    if (slope > 0.6) {
        color.rg = color.gr; // Swap red and green channels
        color *= 1.5;
    }

    // Add contour lines based on height
    if (mod(world_z, 20.0) < 0.5) {
        color = vec3(0.1); // Dark lines
    }

    fragColor = vec4(color, 1.0);
}
