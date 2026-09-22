#覆盖路径规划可视化（pygame 画图）
import pygame
import sys
import math

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
DARK_GREEN = (0, 100, 0)
DARK_GRAY = (80, 80, 80)
LIGHT_BLUE = (200, 230, 255)
RED = (255, 80, 80)

class CoveragePlanner:
    def __init__(self):
        # 窗口参数（可调整大小）
        self.width, self.height = 1200, 800
        self.fullscreen = False
        self.init_display()
        
        # 加载中文字体
        self.font_small, self.font_norm, self.font_title = self.load_chinese_fonts()
        
        # 地图参数（单位：米）
        self.work_area = [(-1.5, -1.0), (1.5, -1.0), (1.5, 1.0), (-1.5, 1.0)]
        self.temp_points = []
        self.mode = "draw_area"
        
        # 路径参数
        self.spacing_m = 0.5          # 航线间距（米）
        self.angle = 0                # 角度（度）
        self.path = []
        self.waypoints = []
        
        # 视图参数
        self.offset_x = self.width // 2
        self.offset_y = self.height // 2
        self.zoom = 1.0
        self.px_per_m = 100.0         # 基础比例：1米=100像素
        
        self.plan_coverage()
    
    def load_chinese_fonts(self):
        """加载中文字体，如果失败则使用默认字体并显示英文"""
        font_paths = [
            'simhei.ttf', 'msyh.ttc', 'msyhbd.ttc',  # 常见中文字体文件名
            'C:/Windows/Fonts/simhei.ttf',           # Windows 路径
            '/System/Library/Fonts/PingFang.ttc',    # macOS 路径
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'  # Linux
        ]
        font_loaded = False
        for path in font_paths:
            try:
                pygame.font.Font(path, 12)
                # 如果能加载，则创建不同大小的字体对象
                small = pygame.font.Font(path, 16)
                norm = pygame.font.Font(path, 20)
                title = pygame.font.Font(path, 26)
                font_loaded = True
                print(f"已加载中文字体: {path}")
                return small, norm, title
            except:
                continue
        if not font_loaded:
            print("警告: 未找到中文字体，将使用默认字体（可能无法显示中文）")
            # 回退到默认字体，但所有文本改为英文（避免乱码）
            self.use_english = True
            return (pygame.font.Font(None, 16), pygame.font.Font(None, 20), pygame.font.Font(None, 26))
        return (pygame.font.Font(None, 16), pygame.font.Font(None, 20), pygame.font.Font(None, 26))
    
    def init_display(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.width, self.height = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("覆盖路径规划")
    
    def world_to_screen(self, pos):
        x = pos[0] * self.px_per_m * self.zoom + self.offset_x
        y = -pos[1] * self.px_per_m * self.zoom + self.offset_y
        return (int(x), int(y))
    
    def screen_to_world(self, pos):
        x = (pos[0] - self.offset_x) / (self.px_per_m * self.zoom)
        y = -(pos[1] - self.offset_y) / (self.px_per_m * self.zoom)
        return (x, y)
    
    def generate_coverage_path(self):
        if not self.work_area or len(self.work_area) < 3:
            return []
        
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        
        def rot(p, inv=False):
            x, y = p
            if inv:
                return (x*cos_a + y*sin_a, -x*sin_a + y*cos_a)
            return (x*cos_a - y*sin_a, x*sin_a + y*cos_a)
        
        rot_area = [rot(p) for p in self.work_area]
        xs = [p[0] for p in rot_area]
        ys = [p[1] for p in rot_area]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        
        path = []
        y = min_y + self.spacing_m / 2
        direction = 1
        
        while y <= max_y:
            inters = []
            for i in range(len(rot_area)):
                p1, p2 = rot_area[i], rot_area[(i+1)%len(rot_area)]
                if (p1[1] <= y <= p2[1]) or (p2[1] <= y <= p1[1]):
                    if p1[1] != p2[1]:
                        t = (y - p1[1]) / (p2[1] - p1[1])
                        inters.append(p1[0] + t*(p2[0] - p1[0]))
            if len(inters) >= 2:
                inters.sort()
                if direction == 1:
                    path.extend([rot((inters[0], y), True), rot((inters[-1], y), True)])
                else:
                    path.extend([rot((inters[-1], y), True), rot((inters[0], y), True)])
            y += self.spacing_m
            direction *= -1
        return path
    
    def plan_coverage(self):
        self.path = self.generate_coverage_path()
        self.waypoints = []
        for i, p in enumerate(self.path):
            is_turn = (i>0 and i<len(self.path)-1 and
                      abs(p[1]-self.path[i-1][1]) > self.spacing_m*0.5 and
                      abs(self.path[i+1][1]-p[1]) > self.spacing_m*0.5)
            self.waypoints.append({'pos': p, 'turn': is_turn})
        print(f"规划完成: {len(self.path)} 航点, 间距 {self.spacing_m:.2f}m")
    
    def draw_grid(self):
        tl = self.screen_to_world((0,0))
        br = self.screen_to_world((self.width,self.height))
        min_x, max_x = min(tl[0],br[0]), max(tl[0],br[0])
        min_y, max_y = min(tl[1],br[1]), max(tl[1],br[1])
        
        ppm = self.px_per_m * self.zoom
        if ppm < 20: step = 5.0
        elif ppm < 50: step = 2.0
        elif ppm < 100: step = 1.0
        elif ppm < 200: step = 0.5
        else: step = 0.2
        
        x = math.floor(min_x/step)*step
        while x <= max_x:
            sx = self.world_to_screen((x,0))[0]
            if 0 <= sx <= self.width:
                color = (180,180,180) if abs(x-round(x))<0.01 else (220,220,220)
                pygame.draw.line(self.screen, color, (sx,0), (sx,self.height), 1)
            x += step
        
        y = math.floor(min_y/step)*step
        while y <= max_y:
            sy = self.world_to_screen((0,y))[1]
            if 0 <= sy <= self.height:
                color = (180,180,180) if abs(y-round(y))<0.01 else (220,220,220)
                pygame.draw.line(self.screen, color, (0,sy), (self.width,sy), 1)
            y += step
    
    def draw_axes(self):
        origin = self.world_to_screen((0,0))
        ppm = self.px_per_m * self.zoom
        
        if 0 <= origin[1] <= self.height:
            pygame.draw.line(self.screen, BLACK, (0,origin[1]), (self.width,origin[1]), 2)
            step = 0.5 if ppm*0.5>=20 else (1.0 if ppm*0.5<20 else 0.25)
            left = self.screen_to_world((0,origin[1]))[0]
            right = self.screen_to_world((self.width,origin[1]))[0]
            x = math.floor(left/step)*step
            while x <= right:
                sx = self.world_to_screen((x,0))[0]
                if 0 <= sx <= self.width:
                    pygame.draw.line(self.screen, BLACK, (sx,origin[1]-5), (sx,origin[1]+5), 1)
                    label = "0" if abs(x)<0.01 else f"{x:.1f}"
                    txt = self.font_small.render(label, True, BLACK)
                    self.screen.blit(txt, txt.get_rect(center=(sx, origin[1]+12)))
                x += step
        
        if 0 <= origin[0] <= self.width:
            pygame.draw.line(self.screen, BLACK, (origin[0],0), (origin[0],self.height), 2)
            step = 0.5 if ppm*0.5>=20 else (1.0 if ppm*0.5<20 else 0.25)
            top = self.screen_to_world((origin[0],0))[1]
            bottom = self.screen_to_world((origin[0],self.height))[1]
            y = math.floor(bottom/step)*step
            while y <= top:
                sy = self.world_to_screen((0,y))[1]
                if 0 <= sy <= self.height:
                    pygame.draw.line(self.screen, BLACK, (origin[0]-5,sy), (origin[0]+5,sy), 1)
                    label = "0" if abs(y)<0.01 else f"{y:.1f}"
                    txt = self.font_small.render(label, True, BLACK)
                    self.screen.blit(txt, txt.get_rect(right=origin[0]-8, centery=sy))
                y += step
    
    def draw_work_area(self):
        if self.work_area:
            pts = [self.world_to_screen(p) for p in self.work_area]
            if len(pts) >= 3:
                surf = pygame.Surface((self.width,self.height), pygame.SRCALPHA)
                pygame.draw.polygon(surf, (*CYAN, 80), pts)
                self.screen.blit(surf, (0,0))
                pygame.draw.polygon(self.screen, BLUE, pts, 3)
        if self.mode == "draw_area" and self.temp_points:
            pts = [self.world_to_screen(p) for p in self.temp_points]
            if len(pts) > 1:
                pygame.draw.lines(self.screen, ORANGE, False, pts, 3)
            for p in pts:
                pygame.draw.circle(self.screen, ORANGE, p, 5)
    
    def draw_path(self):
        if len(self.path) > 1:
            pts = [self.world_to_screen(p) for p in self.path]
            for i in range(len(pts)-1):
                pygame.draw.line(self.screen, GREEN, pts[i], pts[i+1], 3)
            for wp in self.waypoints:
                pos = self.world_to_screen(wp['pos'])
                color = YELLOW if wp['turn'] else GREEN
                r = 6 if wp['turn'] else 4
                pygame.draw.circle(self.screen, color, pos, r)
                pygame.draw.circle(self.screen, BLACK, pos, r, 1)
    
    def draw_scale_bar(self):
        ppm = self.px_per_m * self.zoom
        if ppm >= 200: m, divs = 0.2, 2
        elif ppm >= 100: m, divs = 0.5, 5
        elif ppm >= 50: m, divs = 1.0, 10
        elif ppm >= 20: m, divs = 2.0, 4
        elif ppm >= 10: m, divs = 5.0, 5
        else: m, divs = 10.0, 10
        
        px_len = m * ppm
        if px_len > 200:
            m /= 2
            divs = max(2, divs//2)
        elif px_len < 50 and m < 10:
            m *= 2
            divs = min(10, divs*2)
        px_len = m * ppm
        
        margin = 20
        start_x = self.width - px_len - margin
        y = self.height - margin - 40
        
        bg_rect = pygame.Rect(start_x-5, y-20, px_len+10, 55)
        pygame.draw.rect(self.screen, LIGHT_BLUE, bg_rect)
        pygame.draw.rect(self.screen, DARK_GRAY, bg_rect, 1)
        
        seg_w = px_len / divs
        label_step = max(1, divs//4)
        for i in range(divs+1):
            x = start_x + i*seg_w
            pygame.draw.line(self.screen, BLACK, (x, y-8), (x, y+8), 2 if i%(divs//2)==0 else 1)
            if i % label_step == 0 or i == divs:
                val = i * m / divs
                txt = self.font_small.render(f"{val:.1f}", True, BLACK)
                self.screen.blit(txt, txt.get_rect(center=(x, y+15)))
        pygame.draw.line(self.screen, BLACK, (start_x, y), (start_x+px_len, y), 3)
        self.screen.blit(self.font_norm.render(f"{m:.1f} m", True, DARK_GREEN), (start_x, y+30))
        self.screen.blit(self.font_small.render(f"1m = {ppm:.1f}px", True, DARK_GRAY), (start_x, y+42))
    
    def draw_ui(self):
        bar = pygame.Rect(0, 0, self.width, 80)
        s = pygame.Surface((self.width, 80), pygame.SRCALPHA)
        s.fill((240, 240, 240, 200))
        self.screen.blit(s, (0,0))
        
        # 标题（支持中英文自动切换）
        if hasattr(self, 'use_english') and self.use_english:
            title_text = "Coverage Path Planning"
            btn_texts = [("Draw", "draw_area"), ("Plan", "plan"), ("Clear", "clear"), ("Reset", "reset")]
            spacing_label = f"Spacing: {self.spacing_m:.2f} m"
            angle_label = f"Angle: {self.angle}°"
            info_text = f"Waypoints: {len(self.waypoints)}   Points: {len(self.path)}"
            full_text = "Fullscreen"
        else:
            title_text = "覆盖路径规划"
            btn_texts = [("绘制区域", "draw_area"), ("规划路径", "plan"), ("清除", "clear"), ("重置视图", "reset")]
            spacing_label = f"间距: {self.spacing_m:.2f} m"
            angle_label = f"角度: {self.angle}°"
            info_text = f"航点: {len(self.waypoints)}  路径点: {len(self.path)}"
            full_text = "全屏"
        
        self.screen.blit(self.font_title.render(title_text, True, DARK_GREEN), (20, 8))
        
        btns = []
        y = 40
        for i, (txt, mode) in enumerate(btn_texts):
            x = 20 + i*110
            rect = pygame.Rect(x, y, 90, 30)
            color = GREEN if self.mode == mode else GRAY
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 2)
            self.screen.blit(self.font_norm.render(txt, True, BLACK), (x+15, y+6))
            btns.append((rect, mode))
        
        param_x = 500
        self.screen.blit(self.font_norm.render(spacing_label, True, BLACK), (param_x, y+5))
        dec_sp = pygame.Rect(param_x+130, y+2, 25, 22)
        inc_sp = pygame.Rect(param_x+165, y+2, 25, 22)
        for r in (dec_sp, inc_sp):
            pygame.draw.rect(self.screen, GRAY, r)
            pygame.draw.rect(self.screen, BLACK, r, 1)
        self.screen.blit(self.font_title.render("-", True, BLACK), (dec_sp.x+8, dec_sp.y))
        self.screen.blit(self.font_title.render("+", True, BLACK), (inc_sp.x+8, inc_sp.y))
        
        self.screen.blit(self.font_norm.render(angle_label, True, BLACK), (param_x+220, y+5))
        dec_ang = pygame.Rect(param_x+340, y+2, 25, 22)
        inc_ang = pygame.Rect(param_x+375, y+2, 25, 22)
        for r in (dec_ang, inc_ang):
            pygame.draw.rect(self.screen, GRAY, r)
            pygame.draw.rect(self.screen, BLACK, r, 1)
        self.screen.blit(self.font_title.render("-", True, BLACK), (dec_ang.x+8, dec_ang.y))
        self.screen.blit(self.font_title.render("+", True, BLACK), (inc_ang.x+8, inc_ang.y))
        
        full_rect = pygame.Rect(self.width-80, 10, 70, 25)
        pygame.draw.rect(self.screen, DARK_GRAY, full_rect)
        pygame.draw.rect(self.screen, BLACK, full_rect, 1)
        self.screen.blit(self.font_small.render(full_text, True, WHITE), (self.width-75, 13))
        
        self.screen.blit(self.font_small.render(info_text, True, DARK_GRAY), (param_x, y+35))
        
        return btns, dec_sp, inc_sp, dec_ang, inc_ang, full_rect
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        dragging = False
        last_mouse = None
        
        while running:
            self.screen.fill(WHITE)
            self.draw_grid()
            self.draw_axes()
            self.draw_work_area()
            self.draw_path()
            btns, dec_sp, inc_sp, dec_ang, inc_ang, full_btn = self.draw_ui()
            self.draw_scale_bar()
            
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                
                elif ev.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.width, self.height = ev.w, ev.h
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    # 重新调整偏移中心（保持视图内容大致不变）
                    self.offset_x = self.width // 2
                    self.offset_y = self.height // 2
                
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    pos = ev.pos
                    handled = False
                    for rect, mode in btns:
                        if rect.collidepoint(pos):
                            if mode == "plan":
                                self.plan_coverage()
                            elif mode == "clear":
                                self.work_area = None
                                self.path, self.waypoints, self.temp_points = [], [], []
                            elif mode == "reset":
                                self.offset_x, self.offset_y = self.width//2, self.height//2
                                self.zoom = 1.0
                            else:
                                self.mode = mode
                                self.temp_points = []
                            handled = True
                            break
                    if handled:
                        continue
                    
                    if dec_sp.collidepoint(pos):
                        self.spacing_m = max(0.1, round(self.spacing_m - 0.05, 2))
                        self.plan_coverage()
                    elif inc_sp.collidepoint(pos):
                        self.spacing_m = min(5.0, round(self.spacing_m + 0.05, 2))
                        self.plan_coverage()
                    elif dec_ang.collidepoint(pos):
                        self.angle = (self.angle - 15) % 180
                        self.plan_coverage()
                    elif inc_ang.collidepoint(pos):
                        self.angle = (self.angle + 15) % 180
                        self.plan_coverage()
                    elif full_btn.collidepoint(pos):
                        self.fullscreen = not self.fullscreen
                        self.init_display()
                        self.offset_x, self.offset_y = self.width//2, self.height//2
                    elif pos[1] < self.height - 80:
                        world = self.screen_to_world(pos)
                        if ev.button == 1 and self.mode == "draw_area":
                            self.temp_points.append(world)
                        elif ev.button == 3 and self.mode == "draw_area" and len(self.temp_points) >= 3:
                            self.work_area = self.temp_points.copy()
                            self.temp_points = []
                            self.plan_coverage()
                        elif ev.button == 4:  # 滚轮向上：放大
                            # 以鼠标为中心缩放
                            mouse_before = self.screen_to_world(pos)
                            self.zoom = min(20.0, self.zoom * 1.1)
                            mouse_after = self.screen_to_world(pos)
                            # 调整偏移量，使鼠标位置对应的世界坐标不变
                            self.offset_x += (mouse_after[0] - mouse_before[0]) * self.px_per_m * self.zoom
                            self.offset_y -= (mouse_after[1] - mouse_before[1]) * self.px_per_m * self.zoom
                        elif ev.button == 5:  # 滚轮向下：缩小
                            mouse_before = self.screen_to_world(pos)
                            self.zoom = max(0.05, self.zoom / 1.1)
                            mouse_after = self.screen_to_world(pos)
                            self.offset_x += (mouse_after[0] - mouse_before[0]) * self.px_per_m * self.zoom
                            self.offset_y -= (mouse_after[1] - mouse_before[1]) * self.px_per_m * self.zoom
                        elif ev.button == 2:
                            dragging, last_mouse = True, pos
                
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 2:
                    dragging = False
                
                elif ev.type == pygame.MOUSEMOTION and dragging and last_mouse:
                    dx = ev.pos[0] - last_mouse[0]
                    dy = ev.pos[1] - last_mouse[1]
                    self.offset_x += dx
                    self.offset_y += dy
                    last_mouse = ev.pos
                
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        self.temp_points = []
                    elif ev.key == pygame.K_RETURN and self.mode == "draw_area" and len(self.temp_points) >= 3:
                        self.work_area = self.temp_points.copy()
                        self.temp_points = []
                        self.plan_coverage()
                    elif ev.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        self.init_display()
                        self.offset_x, self.offset_y = self.width//2, self.height//2
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    pygame.init()
    planner = CoveragePlanner()
    planner.run()
