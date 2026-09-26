from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat
import moderngl

class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setSamples(4)
        self.setFormat(fmt)
        
        self.ctx = None

    def initializeGL(self):
        self.ctx = moderngl.create_context()
        self.ctx.clear(0.09, 0.09, 0.1)

    def paintGL(self):
        if not self.ctx:
            return
        
        self.ctx.clear(0.09, 0.09, 0.1)
        self.ctx.finish()

    def resizeGL(self, w, h):
        if self.ctx:
            self.ctx.viewport = (0, 0, w, h)
