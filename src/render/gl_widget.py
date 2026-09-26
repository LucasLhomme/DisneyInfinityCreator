import moderngl
from PIL import Image
import customtkinter as ctk
import numpy as np
import trimesh

VERTEX_SHADER = '''
#version 330
in vec3 in_position;
in vec3 in_normal;
uniform mat4 mvp;
out vec3 v_normal;
void main() {
    gl_Position = mvp * vec4(in_position, 1.0);
    v_normal = in_normal;
}
'''

FRAGMENT_SHADER = '''
#version 330
in vec3 v_normal;
out vec4 f_color;
void main() {
    vec3 light_dir = normalize(vec3(1.0, 1.5, 1.0));
    float lum = max(dot(normalize(v_normal), light_dir), 0.1) + 0.2;
    f_color = vec4(vec3(0.6, 0.6, 0.65) * lum, 1.0);
}
'''

def perspective_matrix(fov, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fov) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = -1.0
    m[3, 2] = (2.0 * far * near) / (near - far)
    return m

def lookat_matrix(eye, target, up):
    f = (target - eye)
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[:3, 3] = [-np.dot(s, eye), -np.dot(u, eye), np.dot(f, eye)]
    return m.T

class GLRenderer:
    def __init__(self, label_widget):
        self.label = label_widget
        self.ctx = moderngl.create_context(standalone=True)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.fbo = None
        self.width = 100
        self.height = 100
        
        self.prog = self.ctx.program(vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER)
        self.vao = None
        self.mesh = None
        
        # Camera
        self.eye = np.array([0.0, 1.0, 3.5], dtype=np.float32)
        self.target = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        
        self.update_fbo()
        self.set_mesh(None)

    def set_mesh(self, mesh):
        self.mesh = mesh
        if mesh is None:
            # Creer un mannequin par defaut (capsule) si aucun modele n'est charge
            self.mesh = trimesh.creation.capsule(height=1.0, radius=0.3)
            self.mesh.apply_translation([0, 0.8, 0])
            
        # Extraire donnees
        verts = self.mesh.vertices.astype('f4')
        normals = self.mesh.vertex_normals.astype('f4')
        faces = self.mesh.faces.astype('i4')
        
        vbo_data = np.hstack([verts, normals]).astype('f4').tobytes()
        ibo_data = faces.tobytes()
        
        vbo = self.ctx.buffer(vbo_data)
        ibo = self.ctx.buffer(ibo_data)
        
        self.vao = self.ctx.vertex_array(
            self.prog,
            [(vbo, '3f 3f', 'in_position', 'in_normal')],
            index_buffer=ibo
        )
        
        # Ajuster la camera
        bounds = self.mesh.bounds
        center = (bounds[0] + bounds[1]) / 2.0
        size = np.linalg.norm(bounds[1] - bounds[0])
        self.target = center
        self.eye = center + np.array([size*0.5, size*0.3, size*1.2], dtype=np.float32)
        
        self.render()

    def update_fbo(self):
        if self.width <= 0 or self.height <= 0:
            return
        if self.fbo:
            self.fbo.release()
            
        color_rb = self.ctx.renderbuffer((self.width, self.height))
        depth_rb = self.ctx.depth_renderbuffer((self.width, self.height))
        self.fbo = self.ctx.framebuffer(color_attachments=[color_rb], depth_attachment=depth_rb)

    def render(self):
        if not self.fbo or not self.vao:
            return
            
        self.fbo.use()
        self.ctx.clear(0.09, 0.09, 0.1) # Obsidian dark color
        
        proj = perspective_matrix(45.0, self.width / self.height, 0.1, 100.0)
        view = lookat_matrix(self.eye, self.target, self.up)
        mvp = np.dot(view, proj) # numpy dot avec matrices projette m1 * m2
        
        self.prog['mvp'].write(mvp.astype('f4').tobytes())
        self.vao.render(moderngl.TRIANGLES)
        
        data = self.fbo.read(components=3, alignment=1)
        image = Image.frombytes('RGB', (self.width, self.height), data)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(self.width, self.height))
        self.label.configure(image=ctk_image, text="")
        self.label.image = ctk_image

    def resize(self, w, h):
        if w != self.width or h != self.height:
            if w > 0 and h > 0:
                self.width = w
                self.height = h
                self.update_fbo()
                self.render()
