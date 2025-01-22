import pygame as pg
import math

class PhysicalPiece:
    type_to_pendulum_length = {"P": 3.5, "R": 5.1, "N": 4, "B": 4, "Q": 6, "K": 6}
    def __init__(self, type, drag_point_x_pos, drag_point_y_pos, spin_angle,
                  drag_point_x_acc, drag_point_y_acc, spin_anglar_vel,
                  SQUARE_SIZE, GRAVITY, FRICTION, DRAG_POS, IMAGES):
        self.type = type
        self.SQUARE_SIZE = SQUARE_SIZE
        self.GRAVITY = GRAVITY
        self.FRICTION = FRICTION
        self.DRAG_POS = DRAG_POS
        self.IMAGES = IMAGES
        self.pen_len = self.type_to_pendulum_length[self.type[1]]
        self.dp_x_pos = drag_point_x_pos
        self.dp_y_pos = drag_point_y_pos
        self.sp_ang = spin_angle
        self.dp_x_vel = drag_point_x_acc
        self.dp_y_vel = drag_point_y_acc
        self.sp_ang_vel = spin_anglar_vel
        

    def draw(self, screen):
        new_width, new_center = self.get_new_width_and_center()
        screen.blit(pg.transform.rotate(self.IMAGES[self.type], self.sp_ang), pg.Rect(new_center[0] - (new_width // 2), new_center[1] - (new_width // 2), new_width, new_width))

    def get_new_width_and_center(self):
        new_width = int(self.SQUARE_SIZE * (abs(math.sin(math.radians(self.sp_ang))) + abs(math.cos(math.radians(self.sp_ang)))))
        new_center = [0,0]
        new_center[0] = int(self.dp_x_pos + self.SQUARE_SIZE * (0.5 - self.DRAG_POS) * math.sin(math.radians(self.sp_ang)))
        new_center[1] = int(self.dp_y_pos + self.SQUARE_SIZE * (0.5 - self.DRAG_POS) * math.cos(math.radians(self.sp_ang)))
        return new_width, new_center

    def update(self, drag_point_x_pos, drag_point_y_pos, drag_point_x_acc, drag_point_y_acc):
        self.dp_x_pos = drag_point_x_pos
        self.dp_y_pos = drag_point_y_pos
        self.sp_ang = self.sp_ang + self.sp_ang_vel
        self.sp_ang_vel = (self.sp_ang_vel - ((self.GRAVITY - drag_point_y_acc) * math.sin(math.radians(self.sp_ang) + drag_point_x_acc * math.cos(math.radians(self.sp_ang)))) / self.pen_len) * (1 - self.FRICTION)

