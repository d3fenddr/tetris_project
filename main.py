import os
import csv
import sys
import pygame
import random
import requests
from io import StringIO
from datetime import datetime

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1bFY8FxdE8gl1qFj3jQm7bta9Pizw_yqkSpm-CqRr2JE/export?format=csv&gid=469714189"

pygame.mixer.init()
pygame.display.init()
pygame.font.init()

MENU_MUSIC = resource_path("menu-music.mp3")
GAME_MUSIC = resource_path("game-music.mp3")
BACKGROUND = resource_path("background.png")
FIRST_PAGE = resource_path("first_page.png")

# Music volume
BASE_MAX_VOLUME = 0.07
volume_percent = 100
music_enabled = True


def apply_volume():
    if music_enabled:
        actual = (volume_percent / 100) * BASE_MAX_VOLUME
    else:
        actual = 0
    pygame.mixer.music.set_volume(actual)


# Window
WIDTH, HEIGHT = 350, 700
ROWS, COLS = 20, 10
BLOCK_SIZE = WIDTH // COLS
FPS = 60


WHITE = (255, 255, 255)
GRAY = (50, 50, 50)
BLUE = (0, 150, 255)
RED = (255, 0, 0)
DARK_RED = (115, 0, 0)
BLACK = (0, 0, 0)

player_name = ""

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris")
clock = pygame.time.Clock()
background_img = pygame.image.load(BACKGROUND).convert()
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))
first_page_img = pygame.image.load(FIRST_PAGE).convert()

# Google Forms
GOOGLE_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSd1IqHQhAawskKNluN1Be9Ey2ULny0OGeUkJ2XP3aFjD0rR-Q/formResponse"
)
FIELD_NAME = "entry.1969811371"
FIELD_SCORE = "entry.1726351225"

# SHAPES
SHAPES = [
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1], [1, 1]],  # O
    [[0, 1, 1], [1, 1, 0]],  # Z
    [[1, 1, 0], [0, 1, 1]],  # S
    [[1, 1, 1, 1]],  # I
    [[1, 0, 1, 1, 1],  # 88
     [1, 0, 1, 0, 0],
     [1, 1, 1, 1, 1],
     [0, 0, 1, 0, 1],
     [1, 1, 1, 0, 1]],
    [[1, 0],  # L
     [1, 0],
     [1, 1]],
    [[0, 1],  # J
     [0, 1],
     [1, 1]]
]

SHAPE_WEIGHTS = [100, 100, 100, 100, 100, 35, 100, 100]


def create_grid(locked=None):
    locked = locked or {}
    grid = [[0] * COLS for _ in range(ROWS)]
    for (x, y), v in locked.items():
        if 0 <= x < COLS and 0 <= y < ROWS:
            grid[y][x] = v
    return grid


class Piece:
    def __init__(self):
        idx = random.choices(range(len(SHAPES)), weights=SHAPE_WEIGHTS, k=1)[0]
        self.shape = SHAPES[idx]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def draw(self):
        for i, row in enumerate(self.shape):
            for j, c in enumerate(row):
                if c:
                    r = pygame.Rect((self.x + j) * BLOCK_SIZE,
                                    (self.y + i) * BLOCK_SIZE,
                                    BLOCK_SIZE, BLOCK_SIZE)
                    pygame.draw.rect(screen, WHITE, r)
                    pygame.draw.rect(screen, BLACK, r, 1)

    def get_cells(self):
        return [
            (self.x + j, self.y + i)
            for i, row in enumerate(self.shape)
            for j, c in enumerate(row) if c
        ]

    def valid_move(self, dx, dy, grid):
        for x, y in self.get_cells():
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= COLS or ny >= ROWS:
                return False
            if ny >= 0 and grid[ny][nx]:
                return False
        return True

    def rotate(self, grid):
        new_shape = [list(r) for r in zip(*self.shape[::-1])]
        old = self.shape
        self.shape = new_shape
        if not self.valid_move(0, 0, grid):
            self.shape = old


def draw_grid(grid):
    screen.blit(background_img, (0, 0))
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x]:
                pygame.draw.rect(screen, DARK_RED,
                                 (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
    for y in range(ROWS + 1):
        pygame.draw.line(screen, GRAY,
                         (0, y * BLOCK_SIZE), (WIDTH, y * BLOCK_SIZE), 1)
    for x in range(COLS + 1):
        pygame.draw.line(screen, GRAY,
                         (x * BLOCK_SIZE, 0), (x * BLOCK_SIZE, HEIGHT), 1)
    pygame.draw.rect(screen, GRAY, (0, 0, WIDTH, HEIGHT), 2)


def draw_text(text, size, color, x, y):
    font = pygame.font.SysFont("comicsans", size)
    label = font.render(text, True, color)
    rect = label.get_rect(center=(x, y))
    screen.blit(label, rect)


def show_loading_screen(text="Loading..."):
    screen.fill(BLACK)
    draw_text(text, 28, WHITE, WIDTH // 2, HEIGHT // 2)
    pygame.display.update()


def record_score(score):
    try:
        update_google_sheet(player_name, score)
    except Exception as e:
        print("Ошибка отправки в Google Sheet:", e)


def popup_time(date_str):
    dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")
    time_text = dt.strftime("%H:%M")
    date_text = dt.strftime("%d %B %Y")
    while True:
        for e in pygame.event.get():
            if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        screen.fill(BLACK)
        draw_text(time_text, 40, WHITE, WIDTH // 2, HEIGHT // 2 - 20)
        draw_text(date_text, 28, RED, WIDTH // 2, HEIGHT // 2 + 30)
        pygame.display.update()
        clock.tick(FPS)


def get_player_history(name):
    response = requests.get(GOOGLE_SHEET_CSV_URL)
    response.encoding = 'utf-8'
    f = StringIO(response.text)
    reader = csv.DictReader(f)

    history = []
    for row in reader:
        row_name = row.get("Player Name") or row.get("name")
        if row_name and row_name.strip().lower() == name.strip().lower():
            score = int(row.get("Score") or row.get("score") or 0)
            date = row.get("Date") or row.get("date") or ""
            history.append({
                "score": score,
                "date": date
            })

    history.sort(key=lambda x: x["date"], reverse=True)  # по убыванию
    return history


def show_history():
    per_page = 8
    page = 0
    sort_mode = "date"
    ascending = False
    global player_name

    def apply_filters_and_sort(data):
        if sort_mode == "date":
            def key(r):
                try:
                    return datetime.strptime(r["date"], "%d.%m.%Y %H:%M:%S")
                except:
                    return datetime.min
        else:
            key = lambda r: r["score"]
        sorted_data = sorted(data, key=key, reverse=not ascending)
        return sorted_data

    show_loading_screen("Loading...")
    pygame.event.pump()
    history = get_player_history(player_name)

    # Постоянная сортировка по дате для нумерации
    try:
        history_by_date = sorted(history, key=lambda r: datetime.strptime(r["date"], "%d.%m.%Y %H:%M:%S"))
    except:
        history_by_date = history

    # Создаём отображение: {id(rec): номер_игры_по_времени}
    game_index_map = {id(rec): i + 1 for i, rec in enumerate(history_by_date)}

    while True:
        filtered = apply_filters_and_sort(history)
        pages = (len(filtered) + per_page - 1) // per_page
        display = filtered[page * per_page:(page + 1) * per_page]

        screen.fill(BLACK)
        draw_text(f"History: Page {page + 1}/{pages}", 28, WHITE, WIDTH // 2, 30)
        draw_text(f"Total Games: {len(history)}", 20, GRAY, WIDTH // 2, 60)

        for idx, rec in enumerate(display):
            y = 100 + idx * 60
            game_number = game_index_map.get(id(rec), page * per_page + idx + 1)

            draw_text(f"Game {game_number}", 22, WHITE, WIDTH // 2 - 100, y)
            draw_text(f"Score: {rec['score']}", 20, WHITE, WIDTH // 2 - 100, y + 25)

            try:
                dt = datetime.strptime(rec["date"], "%d.%m.%Y %H:%M:%S")
                date_str = dt.strftime("%d.%m.%y")
                time_str = dt.strftime("%H:%M")
            except:
                date_str = "???"
                time_str = ""

            draw_text(date_str, 18, GRAY, WIDTH // 2 + 60, y + 5)
            draw_text(time_str, 16, GRAY, WIDTH // 2 + 60, y + 25)

        draw_text("LEFT / RIGHT: Page", 20, GRAY, WIDTH // 2, HEIGHT - 80)
        draw_text(f"S — Sort with: {sort_mode}", 20, GRAY, WIDTH // 2, HEIGHT - 55)
        draw_text(f"F — Order: {'Up' if ascending else 'Down'}", 20, GRAY, WIDTH // 2, HEIGHT - 35)
        draw_text("ESC to return", 20, GRAY, WIDTH // 2, HEIGHT - 15)

        pygame.display.update()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return
                elif e.key == pygame.K_RIGHT and page < pages - 1:
                    page += 1
                elif e.key == pygame.K_LEFT and page > 0:
                    page -= 1
                elif e.key == pygame.K_s:
                    sort_mode = "score" if sort_mode == "date" else "date"
                elif e.key == pygame.K_f:
                    ascending = not ascending


def countdown():
    for i in range(3, 0, -1):
        screen.fill(BLACK)
        draw_text(str(i), 60, WHITE, WIDTH // 2, HEIGHT // 2)
        pygame.display.update()
        pygame.time.delay(1000)


def game_over_screen(score):
    while True:
        screen.fill(BLACK)
        draw_text("GAME OVER", 45, RED, WIDTH // 2, HEIGHT // 3)
        draw_text(f"Score: {score}", 28, WHITE, WIDTH // 2, HEIGHT // 3 + 60)
        pr = pygame.Rect(WIDTH // 2 - 75, HEIGHT // 2, 150, 40)
        mr = pygame.Rect(WIDTH // 2 - 75, HEIGHT // 2 + 60, 150, 40)
        pygame.draw.rect(screen, GRAY, pr)
        pygame.draw.rect(screen, GRAY, mr)
        draw_text("Play Again", 30, BLACK, pr.centerx, pr.centery)
        draw_text("Main Menu", 30, BLACK, mr.centerx, mr.centery)
        pygame.display.update()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = e.pos
                if pr.collidepoint(mx, my): return True
                if mr.collidepoint(mx, my): return False


def settings_menu():
    global volume_percent, music_enabled
    selected = 0
    options = ["Music Volume", "Toggle Music", "Back"]
    while True:
        screen.fill(BLACK)
        draw_text("Settings", 36, WHITE, WIDTH // 2, 80)
        draw_text(f"Music Volume: {volume_percent}%", 28, WHITE, WIDTH // 2, 200)
        draw_text("LEFT/RIGHT to adjust", 20, GRAY, WIDTH // 2, 235)
        draw_text(f"Music: {'On' if music_enabled else 'Off'} (Press M)", 28, WHITE, WIDTH // 2, 300)
        draw_text("ESC to return", 20, GRAY, WIDTH // 2, HEIGHT - 20)
        pygame.display.update()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:
                    volume_percent = max(0, volume_percent - 10)
                    apply_volume()
                elif e.key == pygame.K_RIGHT:
                    volume_percent = min(100, volume_percent + 10)
                    apply_volume()
                elif e.key == pygame.K_m:
                    music_enabled = not music_enabled
                    apply_volume()
                elif e.key == pygame.K_ESCAPE:
                    return


def confirm_exit_mouse():
    yes_rect = no_rect = None

    while True:
        screen.fill(BLACK)
        draw_text("Exit without saving?", 26, WHITE, WIDTH // 2, HEIGHT // 2 - 30)

        mx, my = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()

        font = pygame.font.SysFont("comicsans", 24)

        yes_surf = font.render("Yes", True, RED if my in range(HEIGHT // 2, HEIGHT // 2 + 30) and mx < WIDTH // 2 else WHITE)
        no_surf = font.render("No", True, RED if my in range(HEIGHT // 2, HEIGHT // 2 + 30) and mx > WIDTH // 2 else WHITE)

        yes_rect = yes_surf.get_rect(center=(WIDTH // 2 - 80, HEIGHT // 2 + 20))
        no_rect = no_surf.get_rect(center=(WIDTH // 2 + 80, HEIGHT // 2 + 20))

        screen.blit(yes_surf, yes_rect)
        screen.blit(no_surf, no_rect)

        pygame.display.update()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if yes_rect.collidepoint(mx, my):
                    return True
                elif no_rect.collidepoint(mx, my):
                    return False

def countdown_overlay(grid, score):
    for i in range(3, 0, -1):
        draw_grid(grid)
        draw_text(f"Score: {score}", 24, WHITE, WIDTH // 2, 20)
        draw_text(str(i), 100, RED, WIDTH // 2, HEIGHT // 2)
        pygame.display.update()
        pygame.time.delay(1000)

def pause_menu(grid, score):
    options = [("Continue", "continue"), ("Settings", "settings"), ("Exit Game", "exit")]
    buttons = []

    pygame.mixer.music.pause()

    while True:
        draw_grid(grid)
        draw_text(f"Score: {score}", 24, WHITE, WIDTH // 2, 20)

        mx, my = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()

        buttons.clear()
        for i, (label, action) in enumerate(options):
            y = HEIGHT // 2 + i * 50
            font = pygame.font.SysFont("comicsans", 26)
            text_surf = font.render(label, True, RED if abs(my - y) < 20 else WHITE)
            rect = text_surf.get_rect(center=(WIDTH // 2, y))
            screen.blit(text_surf, rect)
            buttons.append((rect, action))

        pygame.display.update()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for rect, action in buttons:
                    if rect.collidepoint(mx, my):
                        if action == "continue":
                            pygame.mixer.music.unpause()
                            return
                        elif action == "settings":
                            settings_menu()
                        elif action == "exit":
                            if confirm_exit_mouse():
                                pygame.mixer.music.stop()
                                return "exit"

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.mixer.music.unpause()
                    return


def get_leaderboard():
    response = requests.get(GOOGLE_SHEET_CSV_URL)
    response.encoding = 'utf-8'

    f = StringIO(response.text)
    reader = csv.DictReader(f)

    scores = {}
    for row in reader:
        name = row.get("Player Name") or row.get("name")
        score = int(row.get("Score") or row.get("score") or 0)
        if name:
            date = row.get("Date") or row.get("date") or ""
            prev = scores.get(name)
            if not prev or score > prev[0]:
                scores[name] = (score, date)

    return sorted(scores.items(), key=lambda x: x[1][0], reverse=True)


def show_leaderboard():
    show_loading_screen("Loading...")
    pygame.event.pump()
    lb = get_leaderboard()

    COLORS = [
        (255, 215, 0),  # Gold
        (192, 192, 192),  # Silver
        (205, 127, 50)  # Bronze
    ]

    SIZES = [28, 26, 24]

    while True:
        screen.fill(BLACK)
        draw_text("Leaderboard", 36, WHITE, WIDTH // 2, 30)

        for idx, (name, (score, date)) in enumerate(lb[:10]):
            try:
                dt = datetime.strptime(date, "%d.%m.%Y %H:%M:%S")
                date_str = dt.strftime("%d.%m.%y")
                time_str = dt.strftime("%H:%M")
            except:
                date_str = "??.??.??"
                time_str = "??:??"

            y = 80 + idx * 70
            color = COLORS[idx] if idx < 3 else WHITE
            size = SIZES[idx] if idx < 3 else 22
            draw_text(f"{idx + 1}. {name}: {score}", size, color, WIDTH // 2, y)
            draw_text(f"{date_str} {time_str}", 16, GRAY, WIDTH // 2, y + 20)

        draw_text("ESC to return", 20, GRAY, WIDTH // 2, HEIGHT - 20)
        pygame.display.update()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return


def update_google_sheet(name, score):
    payload = {
        FIELD_NAME: name,
        FIELD_SCORE: score
    }
    requests.post(GOOGLE_FORM_URL, data=payload)


def main_game():
    while True:
        countdown()
        pygame.mixer.music.load(GAME_MUSIC)
        apply_volume()
        pygame.mixer.music.play(-1)

        locked = {}
        fall_time = move_delay = 0
        fall_speed = 1.0
        score = 0
        piece = Piece()
        running = True

        while running:
            dt = clock.tick(FPS)
            fall_time += dt;
            move_delay += dt
            grid = create_grid(locked)

            # Soft drop
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN] and move_delay > 50:
                if piece.valid_move(0, 1, grid): piece.y += 1
                move_delay = 0

            # Авто-падение
            if fall_time / 1000 >= fall_speed:
                if piece.valid_move(0, 1, grid):
                    piece.y += 1
                else:
                    for x, y in piece.get_cells():
                        locked[(x, y)] = 1
                    grid = create_grid(locked)
                    full = [y for y in range(ROWS)
                            if all(grid[y][x] for x in range(COLS))]
                    if full:
                        for row in full:
                            for x in range(COLS):
                                locked.pop((x, row), None)
                        new_locked = {}
                        for (x, y), v in locked.items():
                            shift = sum(1 for fy in full if y < fy)
                            new_locked[(x, y + shift)] = v
                        locked = new_locked
                        score += len(full) * 100
                    piece = Piece()
                    grid = create_grid(locked)
                    if not piece.valid_move(0, 0, grid):
                        running = False
                fall_time = 0

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit();
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_LEFT and piece.valid_move(-1, 0, grid):
                        piece.x -= 1
                    elif e.key == pygame.K_RIGHT and piece.valid_move(1, 0, grid):
                        piece.x += 1
                    elif e.key == pygame.K_UP:
                        piece.rotate(grid)
                    elif e.key == pygame.K_ESCAPE:
                        result = pause_menu(grid, score)
                        if result == "exit":
                            return

            draw_grid(grid)
            piece.draw()
            draw_text(f"Score: {score}", 24, WHITE, WIDTH // 2, 20)
            pygame.display.update()

        pygame.mixer.music.stop()
        record_score(score)
        if not game_over_screen(score):
            break


def main_menu():
    global player_name

    # Ввод ника
    entering = True
    while entering:
        screen.blit(first_page_img, (0, 0))
        draw_text("Enter name:", 30, WHITE, WIDTH // 2, HEIGHT // 3)
        draw_text(player_name or "_", 30, RED, WIDTH // 2, HEIGHT // 2)
        pygame.display.update()
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN and player_name.strip():
                    entering = False
                elif e.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    ch = e.unicode
                    if ch.isalnum() and len(player_name) < 12:
                        player_name += ch

    pygame.mixer.music.load(MENU_MUSIC)
    apply_volume()
    pygame.mixer.music.play(-1)

    # Настройка кнопок
    button_labels = ["Play", "History", "Settings", "Leaderboard", "Exit"]
    font_size = 32
    spacing = 70
    total_height = len(button_labels) * spacing

    # Сдвигаем ниже, отступ от верхней части экрана
    start_y = HEIGHT // 2 - total_height // 2 + 100

    buttons = [
        (label, font_size, WIDTH // 2, start_y + i * spacing)
        for i, label in enumerate(button_labels)
    ]

    while True:
        screen.blit(background_img, (0, 0))
        draw_text(f"Hello, {player_name}", 28, WHITE, WIDTH // 2, HEIGHT // 4)
        draw_text("Use arrows to move", 20, WHITE, WIDTH // 2, HEIGHT // 4 + 40)

        mx, my = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()

        for label, size, cx, cy in buttons:
            font = pygame.font.SysFont("comicsans", size)
            text_width, text_height = font.size(label)
            hovered = abs(mx - cx) < text_width // 2 and abs(my - cy) < text_height // 2
            color = RED if hovered else WHITE
            text_surf = font.render(label, True, color)
            rect = text_surf.get_rect(center=(cx, cy))
            screen.blit(text_surf, rect)

            if hovered and click[0]:
                pygame.time.delay(150)
                if label == "Play":
                    pygame.mixer.music.stop()
                    main_game()
                    pygame.mixer.music.load(MENU_MUSIC)
                    apply_volume()
                    pygame.mixer.music.play(-1)
                elif label == "History":
                    show_history()
                elif label == "Settings":
                    settings_menu()
                elif label == "Leaderboard":
                    show_leaderboard()
                elif label == "Exit":
                    pygame.quit()
                    sys.exit()

        pygame.display.update()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()


if __name__ == "__main__":
    main_menu()
