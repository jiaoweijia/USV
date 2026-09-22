# 覆盖路径规划模块类，负责根据指定区域和参数生成覆盖路径和
# 用于根据区域和参数生成覆盖路径和航点
import math


class CoveragePathPlanner:
    """覆盖路径规划类"""
    
    def __init__(self, spacing=0.5, angle=0):
        """
        初始化覆盖路径规划器
        
        参数:
            spacing: 航线间距（米）
            angle: 覆盖角度（度）
        """
        self.spacing = spacing
        self.angle = angle
        self.coverage_area = []  # 覆盖区域顶点
        self.coverage_path = []  # 覆盖路径点
        self.coverage_waypoints = []  # 覆盖路径航点
    
    def set_coverage_area(self, area):
        """
        设置覆盖区域
        
        参数:
            area: 多边形顶点列表，每个顶点为(x, y)元组
        """
        self.coverage_area = area
    
    def set_parameters(self, spacing=None, angle=None):
        """
        设置规划参数
        
        参数:
            spacing: 航线间距（米）
            angle: 覆盖角度（度）
        """
        if spacing is not None:
            self.spacing = spacing
        if angle is not None:
            self.angle = angle
    
    def generate_coverage_path(self):
        """
        生成覆盖路径
        
        返回:
            path: 覆盖路径点列表
            waypoints: 覆盖路径航点列表
        """
        if not self.coverage_area or len(self.coverage_area) < 3:
            return [], []
        
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        
        def rot(p, inv=False):
            x, y = p
            if inv:
                return (x*cos_a + y*sin_a, -x*sin_a + y*cos_a)
            return (x*cos_a - y*sin_a, x*sin_a + y*cos_a)
        
        rot_area = [rot(p) for p in self.coverage_area]
        xs = [p[0] for p in rot_area]
        ys = [p[1] for p in rot_area]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        
        path = []
        y = min_y + self.spacing / 2
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
            y += self.spacing
            direction *= -1
        
        self.coverage_path = path
        self.coverage_waypoints = []
        for i, p in enumerate(path):
            is_turn = (i>0 and i<len(path)-1 and
                      abs(p[1]-path[i-1][1]) > self.spacing*0.5 and
                      abs(path[i+1][1]-p[1]) > self.spacing*0.5)
            self.coverage_waypoints.append({'pos': p, 'turn': is_turn})
        
        # 反转路径和航迹点的顺序，确保路径是正确的顺序
        path.reverse()
        self.coverage_waypoints.reverse()
        return path, self.coverage_waypoints
    
    def get_coverage_path(self):
        """
        获取覆盖路径
        
        返回:
            coverage_path: 覆盖路径点列表
        """
        return self.coverage_path
    
    def get_coverage_waypoints(self):
        """
        获取覆盖路径航点
        
        返回:
            coverage_waypoints: 覆盖路径航点列表
        """
        return self.coverage_waypoints
