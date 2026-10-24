import sys, math, time, asyncio
import pygame
from game_map import game_map, MAP_W, MAP_H, WALL_COLORS, SPAWNS

# ---------- Config ----------
WIDTH, HEIGHT = 640, 400
HALF_HEIGHT = HEIGHT // 2
FPS = 60
FOV = math.pi / 3
NUM_RAYS = 160          # lower = faster on phones
COLUMN_WIDTH = WIDTH // NUM_RAYS
MAX_DEPTH = 25
MOVE_SPEED = 3.0
ROT_SPEED = 2.5
MOUSE_SENS = 0.0025

# Joystick position (bottom-left)
JOY_CX, JOY_CY, JOY_R = 90, HEIGHT - 90, 60

# ---------- Player ----------
player = {"x": SPAWNS[0][0], "y": SPAWNS[0][1], "angle": SPAWNS[0][2]}
joy_vec = [0.0, 0.0]
touch = {"joy": None, "look": None, "last_x": 0}

# ---------- Physics ----------
def is_wall(x, y):
    mx, my = int(x), int(y)
    if 0 <= mx < MAP_W and 0 <= my < MAP_H:
        return game_map[my][mx] > 0
    return True

def can_stand(x, y, r=0.2):
    return not (is_wall(x-r, y-r) or is_wall(x+r, y-r) or
                is_wall(x-r, y+r) or is_wall(x+r, y+r))

# ---------- Raycaster ----------
def cast_ray(px, py, ra):
    sin_a, cos_a = math.sin(ra), math.cos(ra)
    if abs(cos_a) < 1e-6: cos_a = 1e-6 if cos_a >= 0 else -1e-6
    if abs(sin_a) < 1e-6: sin_a = 1e-6 if sin_a >= 0 else -1e-6
    mx, my = int(px), int(py)
    ddx, ddy = abs(1/cos_a), abs(1/sin_a)
    if cos_a < 0: sx, sdx = -1, (px-mx)*ddx
    else:         sx, sdx = 1,  (mx+1-px)*ddx
    if sin_a < 0: sy, sdy = -1, (py-my)*ddy
    else:         sy, sdy = 1,  (my+1-py)*ddy
    side, w = 0, 0
    for _ in range(64):
        if sdx < sdy:
            sdx += ddx; mx += sx; side = 0
        else:
            sdy += ddy; my += sy; side = 1
        if not (0 <= mx < MAP_W and 0 <= my < MAP_H):
            w = 1; break
        if game_map[my][mx] > 0:
            w = game_map[my][mx]; break
    if w == 0: return MAX_DEPTH, 0, 1
    dist = (sdx-ddx) if side == 0 else (sdy-ddy)
    return max(dist, 0.001), side, w

def shade(c, f):
    return tuple(max(0, min(255, int(v*f))) for v in c)

def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for i in range(HALF_HEIGHT):
        f = i / HALF_HEIGHT; s = int(20 + 30*f)
        pygame.draw.line(bg, (s, s, s+10), (0, i), (WIDTH, i))
        s2 = int(30 + 20*f)
        pygame.draw.line(bg, (s2+10, s2, s2-10), (0, HALF_HEIGHT+i), (WIDTH, HALF_HEIGHT+i))
    return bg

# ---------- Render ----------
def render(screen, bg, font):
    screen.blit(bg, (0, 0))
    for i in range(NUM_RAYS):
        ra = player["angle"] - FOV/2 + (i/NUM_RAYS)*FOV
        dist, side, w = cast_ray(player["x"], player["y"], ra)
        perp = max(dist * math.cos(ra - player["angle"]), 0.01)
        wall_h = min(int(HEIGHT/perp), HEIGHT*4)
        top = HALF_HEIGHT - wall_h//2
        f = max(0.15, 1.0 - perp/MAX_DEPTH) * (0.7 if side == 1 else 1.0)
        screen.fill(shade(WALL_COLORS.get(w, (128,128,128)), f),
                    (i*COLUMN_WIDTH, top, COLUMN_WIDTH, wall_h))

    # Crosshair
    cx, cy = WIDTH//2, HEIGHT//2
    pygame.draw.line(screen, (255,255,255), (cx-8,cy), (cx+8,cy), 1)
    pygame.draw.line(screen, (255,255,255), (cx,cy-8), (cx,cy+8), 1)

    # Joystick
    pygame.draw.circle(screen, (80,80,80), (JOY_CX, JOY_CY), JOY_R, 2)
    kx = JOY_CX + int(joy_vec[0] * JOY_R)
    ky = JOY_CY + int(joy_vec[1] * JOY_R)
    pygame.draw.circle(screen, (200,200,200), (kx, ky), 22)

    # HUD
    screen.blit(font.render("The Met", True, (255,220,100)), (WIDTH-110, 8))

# ---------- Input ----------
def handle_touch(events):
    for e in events:
        if e.type == pygame.FINGERDOWN:
            x, y = e.x * WIDTH, e.y * HEIGHT
            if math.hypot(x-JOY_CX, y-JOY_CY) < JOY_R * 1.6:
                touch["joy"] = e.finger_id
            elif x > WIDTH // 2:
                touch["look"] = e.finger_id
                touch["last_x"] = x
        elif e.type == pygame.FINGERMOTION:
            x, y = e.x * WIDTH, e.y * HEIGHT
            if e.finger_id == touch["joy"]:
                dx, dy = x - JOY_CX, y - JOY_CY
                m = math.hypot(dx, dy) or 1
                dx, dy = dx/m, dy/m
                mag = min(1.0, m / JOY_R)
                joy_vec[0], joy_vec[1] = dx*mag, dy*mag
            elif e.finger_id == touch["look"]:
                player["angle"] += (x - touch["last_x"]) * 0.006
                touch["last_x"] = x
        elif e.type == pygame.FINGERUP:
            if e.finger_id == touch["joy"]:
                touch["joy"] = None
                joy_vec[0] = joy_vec[1] = 0.0
            if e.finger_id == touch["look"]:
                touch["look"] = None

# ---------- Main ----------
async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Met Wolf")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 22)
    bg = make_background()

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False
            elif e.type == pygame.MOUSEMOTION:
                player["angle"] += e.rel[0] * MOUSE_SENS

        handle_touch(events)

        # Combine keyboard + joystick
        keys = pygame.key.get_pressed()
        kfwd = (keys[pygame.K_w] or keys[pygame.K_UP]) - (keys[pygame.K_s] or keys[pygame.K_DOWN])
        kstr = keys[pygame.K_d] - keys[pygame.K_a]
        krot = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]

        fwd = kfwd - joy_vec[1]
        strafe = kstr + joy_vec[0]
        if fwd and strafe:
            n = 1/math.sqrt(2); fwd *= n; strafe *= n

        player["angle"] = (player["angle"] + krot*ROT_SPEED*dt) % (2*math.pi)

        ca, sa = math.cos(player["angle"]), math.sin(player["angle"])
        dx = (ca*fwd - sa*strafe) * MOVE_SPEED * dt
        dy = (sa*fwd + ca*strafe) * MOVE_SPEED * dt
        if can_stand(player["x"]+dx, player["y"]): player["x"] += dx
        if can_stand(player["x"], player["y"]+dy): player["y"] += dy

        render(screen, bg, font)
        pygame.display.flip()
        await asyncio.sleep(0)   # required by pygbag

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
