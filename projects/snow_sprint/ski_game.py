"""Snow Sprint: asset-free Python / Pygame skiing game.

Run: python ski_game.py
Controls: arrows or A/D, Space jump, P pause, R restart, Esc menu.
Original supplied idea: skier + scrolling trees/flags. All artwork is drawn here.
"""
import math
import os
import random
import sys
from dataclasses import dataclass

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
try:
    import pygame
except ImportError:
    raise SystemExit('Install Pygame first: python -m pip install pygame==2.6.1')

# STUDENT SETTINGS / 学生可以先修改这里
WIDTH, HEIGHT = 800, 700
FPS = 60
PLAYER_SPEED = 330       # 横向移动速度，pixels / second
BASE_SPEED = 230         # 雪道初始速度
MAX_SPEED = 440
FLAG_POINTS = 10
TREE_PENALTY = 20
STARTING_LIVES = 3
SPAWN_INTERVAL = 0.85    # 越小障碍物越多
TREE_CHANCE = 0.42       # 树的概率；与石头概率之和不要超过1
ROCK_CHANCE = 0.28       # 石头概率，其余概率生成旗帜
JUMP_DURATION = 1.0      # 跳跃总时长，秒
JUMP_HEIGHT = 78         # 跳跃最高高度，pixels
ROCK_CLEARANCE = 18      # 高于此高度时可以越过石头
PLAYER_COLOR = (237, 108, 77)

INK = (25, 48, 69)
TEAL = (19, 117, 125)
SNOW = (241, 248, 250)


def text(surface, words, size, pos, color=INK, center=False, bold=False):
    f = pygame.font.Font(None, size)
    f.set_bold(bold)
    img = f.render(str(words), True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surface.blit(img, rect)


def tree_surface():
    s = pygame.Surface((76, 100), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (196, 215, 222, 140), (8, 81, 65, 15))
    pygame.draw.rect(s, (120, 83, 65), (33, 64, 11, 24), border_radius=3)
    for y, half in [(10, 20), (27, 28), (45, 35)]:
        pygame.draw.polygon(s, (34, 108, 100), [(38, y), (38-half, y+35), (38+half, y+35)])
        pygame.draw.polygon(s, (219, 240, 237), [(38, y), (38-half*.52, y+18), (38+half*.52, y+18)])
    return s


def flag_surface():
    s = pygame.Surface((48, 76), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (204, 221, 229, 150), (3, 61, 41, 10))
    pygame.draw.line(s, INK, (13, 8), (13, 65), 4)
    pygame.draw.polygon(s, (245, 173, 58), [(15, 8), (43, 12), (35, 29), (15, 26)])
    pygame.draw.line(s, (255, 224, 145), (20, 13), (35, 16), 3)
    return s


def rock_surface():
    s = pygame.Surface((64, 44), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (195, 212, 221, 150), (4, 30, 57, 11))
    pygame.draw.polygon(s, (109, 128, 145), [(7,31),(15,13),(30,6),(47,12),(58,31),(47,37),(16,37)])
    pygame.draw.polygon(s, (159, 176, 188), [(15,13),(30,6),(36,22),(7,31)])
    pygame.draw.polygon(s, (225, 237, 242), [(15,13),(30,6),(44,11),(36,17),(25,14),(19,21)])
    return s


def skier_surface(direction=0, fallen=False):
    s = pygame.Surface((90, 104), pygame.SRCALPHA)
    if fallen:
        pygame.draw.line(s, TEAL, (10, 75), (80, 40), 8)
        pygame.draw.line(s, TEAL, (15, 43), (78, 84), 8)
        pygame.draw.ellipse(s, PLAYER_COLOR, (24, 47, 45, 27))
        pygame.draw.circle(s, (255, 208, 167), (30, 39), 13)
        pygame.draw.circle(s, INK, (27, 34), 13, 4)
        return s
    lean = direction * 6
    for dx in [-14, 14]:
        pygame.draw.line(s, TEAL, (45+dx+direction*5, 64), (45+dx-direction*7, 94), 7)
        pygame.draw.line(s, INK, (45+lean+dx//2, 55), (45+dx, 79), 8)
    pygame.draw.line(s, INK, (20+lean, 45), (10, 86), 3)
    pygame.draw.line(s, INK, (68+lean, 45), (80, 86), 3)
    pygame.draw.line(s, PLAYER_COLOR, (32+lean, 39), (18+lean, 52), 10)
    pygame.draw.line(s, PLAYER_COLOR, (56+lean, 39), (71+lean, 52), 10)
    pygame.draw.rect(s, PLAYER_COLOR, (29+lean, 30, 32, 34), border_radius=11)
    pygame.draw.line(s, (255, 198, 133), (45+lean, 37), (45+lean, 60), 2)
    pygame.draw.circle(s, (255, 208, 167), (45+lean, 24), 16)
    pygame.draw.circle(s, INK, (45+lean, 18), 17)
    pygame.draw.rect(s, (102, 204, 219), (30+lean, 18, 30, 12), border_radius=5)
    pygame.draw.line(s, (221, 249, 255), (35+lean, 21), (44+lean, 21), 2)
    return s


class Skier(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.frames = {n: skier_surface(n) for n in (-1, 0, 1)}
        self.fall_image = skier_surface(fallen=True)
        self.x = WIDTH / 2
        self.y = 235
        self.direction = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.fall_timer = 0.0
        self.invincible = 0.0
        self.jump_elapsed = None

    @property
    def jump_height(self):
        if self.jump_elapsed is None:
            return 0.0
        # 抛物线：起跳与落地高度为0，中点达到最高处。
        progress = self.jump_elapsed / JUMP_DURATION
        return 4 * JUMP_HEIGHT * progress * (1-progress)

    def jump(self):
        if self.jump_elapsed is None and self.fall_timer <= 0:
            self.jump_elapsed = 0.0

    @property
    def hitbox(self):
        return pygame.Rect(round(self.x)-17, round(self.y)-20, 34, 54)

    def update(self, dt, steering):
        self.fall_timer = max(0, self.fall_timer-dt)
        self.invincible = max(0, self.invincible-dt)
        if self.jump_elapsed is not None:
            self.jump_elapsed += dt
            if self.jump_elapsed >= JUMP_DURATION:
                self.jump_elapsed = None
        self.direction = steering if self.fall_timer <= 0 else 0
        self.x = max(85, min(WIDTH-85, self.x+self.direction*PLAYER_SPEED*dt))
        self.image = self.fall_image if self.fall_timer > 0 else self.frames[self.direction]
        # 碰撞仍使用地面位置；只把画面上的人物向上抬起。
        self.rect = self.image.get_rect(center=(round(self.x), round(self.y-self.jump_height)))


class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, y, kind, art):
        super().__init__()
        self.kind = kind
        self.image = art[kind]
        self.x, self.y = float(x), float(y)
        self.rect = self.image.get_rect(center=(x, y))
        self.passed = False

    @property
    def hitbox(self):
        if self.kind == 'tree':
            return pygame.Rect(round(self.x)-21, round(self.y)-18, 42, 51)
        if self.kind == 'rock':
            return pygame.Rect(round(self.x)-23, round(self.y)-10, 46, 23)
        return self.rect.inflate(-10, -12)

    def update(self, dt, speed):
        self.y -= speed*dt
        self.rect.centery = round(self.y)
        if self.rect.bottom < -20:
            self.kill()


@dataclass
class Popup:
    words: str
    x: float
    y: float
    color: tuple
    life: float = 0.9


class Game:
    def __init__(self, seed=None):
        # No mixer/audio initialization: works without speakers or music files.
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Snow Sprint | Fife Python Club')
        self.clock = pygame.time.Clock()
        self.rng = random.Random(seed)
        self.art = {'tree': tree_surface(), 'flag': flag_surface(), 'rock': rock_surface()}
        self.best = 0  # Best score for this running session only.
        self.running = True
        self.reset()
        self.state = 'menu'

    def reset(self):
        self.skier = Skier()
        self.obstacles = pygame.sprite.Group()
        self.popups = []
        self.score = 0
        self.lives = STARTING_LIVES
        self.distance = 0.0
        self.elapsed = 0.0
        self.spawn_timer = .35
        self.scroll = 0.0
        self.state = 'playing'

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == 'menu':
                    self.running = False
                else:
                    self.state = 'menu'
            elif event.key == pygame.K_r:
                self.reset()
            elif event.key == pygame.K_RETURN and self.state in ('menu', 'over'):
                self.reset()
            elif event.key == pygame.K_SPACE and self.state == 'playing':
                self.skier.jump()
            elif event.key == pygame.K_p:
                if self.state == 'playing':
                    self.state = 'paused'
                elif self.state == 'paused':
                    self.state = 'playing'
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == 'playing':
            self.state = 'paused'

    def spawn(self):
        # At most one tree per row, leaving ample horizontal room to dodge.
        lane = self.rng.randrange(7)
        x = 130 + lane*90
        choice = self.rng.random()
        kind = ('tree' if choice < TREE_CHANCE else
                'rock' if choice < TREE_CHANCE+ROCK_CHANCE else 'flag')
        self.obstacles.add(Obstacle(x, HEIGHT+65, kind, self.art))
        if kind == 'tree' and self.rng.random() < .55:
            free = [n for n in range(7) if abs(n-lane) >= 2]
            self.obstacles.add(Obstacle(130+self.rng.choice(free)*90, HEIGHT+65, 'flag', self.art))

    def resolve_collisions(self):
        for obstacle in list(self.obstacles):
            if obstacle.passed or not self.skier.hitbox.colliderect(obstacle.hitbox):
                continue
            if obstacle.kind == 'rock' and self.skier.jump_height >= ROCK_CLEARANCE:
                obstacle.passed = True
                self.popups.append(Popup('CLEARED!', self.skier.x, self.skier.y-105, TEAL))
                continue
            if obstacle.kind == 'flag':
                self.score += FLAG_POINTS
                self.popups.append(Popup('+'+str(FLAG_POINTS), self.skier.x, self.skier.y-65, TEAL))
                obstacle.kill()
            elif self.skier.invincible <= 0:
                self.lives -= 1
                self.score = max(0, self.score-TREE_PENALTY)
                self.skier.fall_timer = .65
                self.skier.jump_elapsed = None
                self.skier.invincible = 1.8
                obstacle.passed = True
                self.popups.append(Popup('OUCH!', self.skier.x, self.skier.y-65, (199, 74, 53)))
                if self.lives <= 0:
                    self.state = 'over'
                    break
        self.best = max(self.best, self.score)

    def update(self, dt, steering=0):
        if self.state != 'playing':
            return
        self.elapsed += dt
        self.skier.update(dt, steering)
        speed = min(MAX_SPEED, BASE_SPEED+self.elapsed*2)
        if self.skier.fall_timer > 0:
            speed *= .35
        self.distance += speed*dt/10
        self.scroll = (self.scroll+speed*dt) % 140
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn()
            self.spawn_timer += SPAWN_INTERVAL
        self.obstacles.update(dt, speed)
        self.resolve_collisions()
        for popup in self.popups:
            popup.life -= dt
            popup.y -= 35*dt
        self.popups = [p for p in self.popups if p.life > 0]

    def background(self):
        s = self.screen
        s.fill(SNOW)
        pygame.draw.polygon(s, (222, 236, 240), [(0,0),(110,0),(65,HEIGHT),(0,HEIGHT)])
        pygame.draw.polygon(s, (222, 236, 240), [(WIDTH-110,0),(WIDTH,0),(WIDTH,HEIGHT),(WIDTH-65,HEIGHT)])
        for i in range(-1, 7):
            y = int(i*140-self.scroll)
            for x in (48, WIDTH-48):
                pygame.draw.line(s, (151, 185, 194), (x,y), (x,y+40), 3)
            pygame.draw.line(s, (225, 237, 241), (235,y+40),(229,y+65), 3)
            pygame.draw.line(s, (225, 237, 241), (555,y+80),(549,y+105), 3)

    def panel(self, title, subtitle, lines):
        veil = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        veil.fill((23,47,66,105))
        self.screen.blit(veil,(0,0))
        box = pygame.Rect(110,190,580,330)
        pygame.draw.rect(self.screen, (255,255,255), box, border_radius=25)
        text(self.screen,title,58,(WIDTH//2,245),center=True,bold=True)
        text(self.screen,subtitle,26,(WIDTH//2,296),TEAL,center=True)
        for i,line in enumerate(lines):
            text(self.screen,line,25,(WIDTH//2,350+i*36),center=True)
        text(self.screen,'FIFE  /  PYTHON CLUB',20,(WIDTH//2,488),TEAL,center=True)

    def draw(self):
        self.background()
        self.obstacles.draw(self.screen)
        shadow_width = int(68-self.skier.jump_height*.3)
        pygame.draw.ellipse(self.screen,(192,213,223),
                            (round(self.skier.x-shadow_width/2),self.skier.y+34,shadow_width,12))
        if not (self.skier.invincible > 0 and int(self.elapsed*12) % 2):
            self.screen.blit(self.skier.image,self.skier.rect)
        for popup in self.popups:
            text(self.screen,popup.words,30,(int(popup.x),int(popup.y)),popup.color,center=True,bold=True)
        pygame.draw.rect(self.screen, (255,255,255), (18,16,WIDTH-36,76), border_radius=18)
        text(self.screen,'SNOW SPRINT',27,(36,29),TEAL,bold=True)
        text(self.screen,f'{int(self.distance)} m  |  Best {self.best}',20,(36,61))
        text(self.screen,f'SCORE  {self.score}',34,(320,40),bold=True)
        text(self.screen,f'LIVES  {self.lives}',30,(620,42),(199,74,53),bold=True)
        pygame.draw.rect(self.screen,(255,255,255),(135,HEIGHT-38,530,28),border_radius=10)
        text(self.screen,'A D / ARROWS: steer   SPACE: jump   P: pause   R: restart',19,(WIDTH//2,HEIGHT-24),center=True)
        if self.state == 'playing':
            status = 'AIRBORNE' if self.skier.jump_elapsed is not None else 'SPACE: JUMP'
            text(self.screen,status,21,(WIDTH-130,112),TEAL,center=True,bold=True)
        if self.state == 'menu':
            self.panel('SNOW SPRINT','Dodge trees. Jump over rocks. Collect flags.',
                       ['Hold LEFT / RIGHT or A / D to steer.',
                        'SPACE: jump over rocks  |  P: pause',
                        'Press ENTER to hit the slopes!'])
        elif self.state == 'paused':
            self.panel('TAKE A BREATHER','Your run is paused.',
                       ['Press P to resume.', 'Press R for a fresh run.', 'Press ESC to return to the menu.'])
        elif self.state == 'over':
            self.panel('NICE RUN!',f'Score {self.score}   /   Distance {int(self.distance)} m',
                       [f'Session best: {self.best}', 'Press ENTER or R to try again.', 'Can you collect one more flag?'])
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS)/1000, .05)
            for event in pygame.event.get():
                self.handle_event(event)
            keys = pygame.key.get_pressed()
            steering = int(keys[pygame.K_RIGHT] or keys[pygame.K_d])-int(keys[pygame.K_LEFT] or keys[pygame.K_a])
            self.update(dt,steering)
            self.draw()
        pygame.quit()


if __name__ == '__main__':
    Game().run()
