//GLSL

// Input vertex data
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;

// Output to fragment shader
out vec2 texcoord;
out float world_z;

// Uniforms from Panda3D
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;

    // Calculate world position and pass the Z component
    vec4 world_pos = p3d_ModelMatrix * p3d_Vertex;
    world_z = world_pos.z;
}
