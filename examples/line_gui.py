"""
A GUI that uses a photo and user input to determine the orientation of the
mirrors of a triangular cavity. Can also calculate where it expects the
mode axis to live.
"""

import sys
import math
from itertools import combinations
from PySide.QtGui import QApplication, QWidget, QGridLayout, QPixmap, QGraphicsView, QGraphicsScene, QGraphicsLineItem, QPen, QBrush, QColor
from PySide.QtCore import QLineF, QPointF, Qt
from PySide.QtUiTools import QUiLoader

def triangle_from_lines(lines):
    vertices, sides = [], []
    for line_pair in combinations(lines, 2):
        type, point = line_pair[0].intersect(line_pair[1])
        vertices.append(point)
    for vert_pair in combinations(vertices, 2):
        sides.append(QLineF(vert_pair[0], vert_pair[1]))
    return vertices, sides

def dot(v1, v2):
    return v1.x()*v2.x() + v1.y()*v2.y()

def mag(v):
    return math.sqrt(v.x()**2 + v.y()**2)

def orthic_triangle(vertices):
    # Points projected normally onto the opposite side
    pts, sides = [], []
    for i in range(3):
        # Rotate the list of vertices
        v1, v2, v3 = vertices[i:] + vertices[:i]
        dv = v2-v1
        xhat = dv/mag(dv)
        pts.append(v1 + dot((v3-v1), xhat) * xhat)
    for vert_pair in combinations(pts, 2):
        sides.append(QLineF(vert_pair[0], vert_pair[1]))
    return pts, sides

def find_axis(top_line, bot_line):
    type, origin = top_line.intersect(bot_line)
    # Force angles into right half-plane regardless of click order
    top_angle = (top_line.angle() + 90)%180 - 90
    bot_angle = (bot_line.angle() + 90)%180 - 90
    xaxis = QLineF(origin, QPointF(0, 0)) # Need to make non-zero vector
    xaxis.setLength(100)
    xaxis.setAngle((top_angle + bot_angle)/2)
    yaxis = QLineF(xaxis)
    yaxis.setAngle(xaxis.angle() + 90)
    return origin, xaxis, yaxis

def find_rel_coords(line, origin, xaxis, yaxis):
    copy = QLineF(line)
    line.setLength(line.length()/2.0)
    midpoint = line.p2()
    x = midpoint.x() - origin.x()
    y = midpoint.y() - origin.y()
    angle = line.angle()%180 - yaxis.angle() # Force line's angle into upper half-plane
    return x, y, angle

class GraphicsScene(QGraphicsScene):
    def __init__(self, mode, flags=[], **kwargs):
        QGraphicsScene.__init__(self, 0, 0, 2*1280, 2*1024)
        self.pts = []
        self.curpts = []
        self.flags = flags
        proc_map = {'tricavity': (self.tricavity, [2,2,2]),
                    'ruler': (self.ruler, [2,2,2,2])}
        self.process_points, self.numpts = proc_map[mode]
        self.pts_left = self.numpts[:] # Shallow copy
        self.kwargs = kwargs

    def mousePressEvent(self, event):
        pos = event.scenePos()
        pts_left = self.pts_left # Shorthand
        if self.pts_left:
            # Assume (for now) that remaining elements are always > 0
            self.curpts.append(pos)

            self.pts_left[0] -= 1
            if self.pts_left[0] == 0:
                self.pts_left.pop(0)
                self.pts.append(self.curpts)
                self.curpts = []
                if not self.pts_left:
                    # We've input our lines, now let's use them
                    self.process_points(**self.kwargs)
        
    def ruler(self):
        # All points for this mode are grouped into pairs
        px_lens = [QLineF(pt[0],pt[1]).length() for pt in self.pts]
        px_ruler_len = px_lens.pop(-1)
        mm_ruler_len = 9.0
        scale = mm_ruler_len/px_ruler_len
        print("Side len: {:.2f} mm".format(px_lens[0]*scale))
        print("Top len: {:.2f} mm".format(px_lens[1]*scale))
        print("Bot len: {:.2f} mm".format(px_lens[2]*scale))

    def tricavity(self, scale_triplet=None):
        # All points for this mode are grouped into pairs
        linesegs = [QLineF(pt[0],pt[1]) for pt in self.pts]
        
        # Calculate interesting things
        verts, sides = triangle_from_lines(linesegs)
        m_verts, m_sides = orthic_triangle(verts)
        origin, xaxis, yaxis = find_axis(linesegs[1], linesegs[2])
        x, y, angle = find_rel_coords(linesegs[0], origin, xaxis, yaxis)

        if scale_triplet:
            scale = sum((mm/line.length() for (mm,line) in zip(scale_triplet, linesegs)))/3.0
            units = 'mm'
        else:
            scale = 1
            units = 'px'

        # Draw 'cavity' triangle
        if 'cavity' in self.flags:
            for side in sides:
                self.draw_line(side)

        # Draw 'mode' triangle
        if 'mode' in self.flags:
            for side in m_sides:
                self.draw_line(side)

        if 'axis' in self.flags:
            self.draw_line(xaxis)
            self.draw_line(yaxis)

        if 'coords' in self.flags:
            print('x: {:.2f} {}'.format(x*scale, units))
            print('y: {:.2f} {}'.format(y*scale, units))
            print('angle: {:.2f} degrees'.format(angle))


    def draw_line(self, linef):
        line = QGraphicsLineItem(linef)
        line.setPen(QPen(QBrush(QColor(0, 0, 0)), 1))
        self.addItem(line)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    loader = QUiLoader()
    ui = loader.load('line_gui.ui')
    ui.show()
    
    pixmap = QPixmap(u'Top.jpg')
    pixmap = pixmap.scaled(2*pixmap.size())

    scene = GraphicsScene('tricavity', ['axis', 'coords'], scale_triplet=(.55,3.04,3.08))
    pix_item = scene.addPixmap(pixmap)
    pix_item.setCursor(Qt.CrossCursor)

    layout = ui.findChild(QGridLayout, 'gridLayout')
    view = QGraphicsView(scene)
    layout.addWidget(view)

    app.exec_()
