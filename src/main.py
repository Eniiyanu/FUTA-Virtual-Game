import pygame
import sys
import os
import json
import random
import asyncio

# Config
ASSET_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')
IMG_DIR = os.path.join(ASSET_DIR, 'images')
ICONS_DIR = os.path.join(ASSET_DIR, 'icons')
AUDIO_DIR = os.path.join(ASSET_DIR, 'audio')
DATA_DIR = os.path.join(ASSET_DIR, 'data')

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Bottom row buttons labels
BOTTOM_BUTTONS = ['Cancel', 'General Knowledge', 'Credits', 'Settings']

# Scenes
SCENE_SPLASH = 'splash'
SCENE_MENU = 'menu'
SCENE_CATEGORY = 'category'
SCENE_INPUT = 'input'
SCENE_QUIZ = 'quiz'
SCENE_CREDITS = 'credits'
SCENE_SETTINGS = 'settings'

# Time limits per difficulty
TIME_LIMITS = {'Easy': 20, 'Medium': 15, 'Hard': 10}

class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 28)

    def draw(self, surf):
        pygame.draw.rect(surf, (50, 50, 50), self.rect)
        txt = self.font.render(self.text, True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, evt):
        if evt.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(evt.pos):
            self.callback()

class SceneBase:
    def __init__(self, game):
        self.game = game
        self.bottom_buttons = []
        btn_w = SCREEN_WIDTH // len(BOTTOM_BUTTONS)
        btn_h = 40
        for i, label in enumerate(BOTTOM_BUTTONS):
            rect = (i * btn_w, SCREEN_HEIGHT - btn_h, btn_w, btn_h)
            self.bottom_buttons.append(Button(rect, label, lambda l=label: game.on_bottom(l)))

    def draw_bottom(self, surf):
        for b in self.bottom_buttons:
            b.draw(surf)

    def handle_event(self, evt):
        if evt.type == pygame.MOUSEBUTTONDOWN and self.game.click_sfx:
            self.game.click_sfx.play()
        for b in self.bottom_buttons:
            b.handle_event(evt)

class SplashScene(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self.start = pygame.time.get_ticks()
        self.img = pygame.image.load(os.path.join(IMG_DIR, 'splash.png')).convert()
        self._play_music('menu_bgm.ogg')

    def _play_music(self, fname):
        path = os.path.join(AUDIO_DIR, fname)
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)

    def update(self):
        if pygame.time.get_ticks() - self.start > 3000:
            self.game.change_scene(SCENE_MENU)

    def draw(self, surf):
        surf.blit(self.img, (0, 0))

class MenuScene(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self._play_music('menu_bgm.ogg')
        self.icons = []  # list of (image, label, key)
        skip = {
            "settings",
            "general_knowledge",
            "credits_bg",
            "learn_futa's_history",
        }
        for fname in sorted(os.listdir(ICONS_DIR)):
            if fname.lower().endswith('.png'):
                key = os.path.splitext(fname)[0].lower()
                if key in skip:
                    continue
                img = pygame.image.load(os.path.join(ICONS_DIR, fname)).convert_alpha()
                label = key.replace('_', ' ').title()
                self.icons.append((img, label, key))

    def _play_music(self, fname):
        path = os.path.join(AUDIO_DIR, fname)
        if os.path.exists(path) and not pygame.mixer.music.get_busy():
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)

    def draw(self, surf):
        surf.fill((0, 0, 0))
        cols = 4
        rows = max(1, (len(self.icons) + cols - 1) // cols)
        cell_w = SCREEN_WIDTH / cols
        cell_h = (SCREEN_HEIGHT - 40) / rows
        self.icon_rects = []
        for idx, (img, label, key) in enumerate(self.icons):
            r, c = divmod(idx, cols)
            scale = (min(cell_w, cell_h) * 0.5) / max(img.get_width(), img.get_height())
            img_s = pygame.transform.smoothscale(
                img,
                (int(img.get_width() * scale), int(img.get_height() * scale))
            )
            x = c * cell_w + (cell_w - img_s.get_width()) / 2
            y = r * cell_h + cell_h * 0.1
            rect = img_s.get_rect(topleft=(x, y))
            surf.blit(img_s, rect)
            txt = pygame.font.Font(None, 20).render(label, True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(midtop=(rect.centerx, rect.bottom + 5)))
            self.icon_rects.append((rect, label, key))
        self.draw_bottom(surf)

    def handle_event(self, evt):
        if evt.type == pygame.MOUSEBUTTONDOWN:
            for rect, label, key in self.icon_rects:
                if rect.collidepoint(evt.pos):
                    if label == 'Cancel':
                        self.game.change_scene(SCENE_MENU)
                    else:
                        self.game.selected_school = label
                        self.game.selected_key = key
                        self.game.change_scene(SCENE_CATEGORY)
        super().handle_event(evt)

class CategoryScene(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        bg_file = f"{game.selected_key}_bg.png"
        path = os.path.join(IMG_DIR, bg_file)
        if not os.path.exists(path):
            path = os.path.join(IMG_DIR, f"{game.selected_key}.png")
        if os.path.exists(path):
            self.bg = pygame.image.load(path).convert()
        else:
            self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.bg.fill((0, 0, 128))
        self._play_music('calm_bgm.ogg')
        self.buttons = []
        w, h, g = 200, 60, 20
        for i, diff in enumerate(['Easy', 'Medium', 'Hard']):
            x = SCREEN_WIDTH/2 - ((w*3 + g*2)/2) + i*(w+g)
            y = SCREEN_HEIGHT/2
            self.buttons.append(Button((x, y, w, h), diff, lambda d=diff: game.start_quiz(d)))

    def _play_music(self, fname):
        path = os.path.join(AUDIO_DIR, fname)
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        title = f"{self.game.selected_school} - Select Difficulty"
        surf.blit(pygame.font.Font(None, 48).render(title, True, (255, 255, 255)), (100, 100))
        for b in self.buttons:
            b.draw(surf)
        self.draw_bottom(surf)

    def handle_event(self, evt):
        for b in self.buttons:
            b.handle_event(evt)
        super().handle_event(evt)

class InputScene(SceneBase):
    def __init__(self, game, difficulty):
        super().__init__(game)
        self.diff = difficulty
        self.text = ''
        self.font = pygame.font.Font(None, 36)

    def draw(self, surf):
        surf.fill((30, 30, 30))
        surf.blit(self.font.render('Enter your name:', True, (255, 255, 255)), (100, 200))
        surf.blit(self.font.render(self.text, True, (255, 255, 255)), (100, 250))
        self.draw_bottom(surf)

    def handle_event(self, evt):
        if evt.type == pygame.KEYDOWN:
            if evt.key == pygame.K_RETURN:
                self.game.player_name = self.text
                self.game.change_scene(SCENE_QUIZ)
            elif evt.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += evt.unicode
        super().handle_event(evt)

class QuizScene(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        prefix = game.selected_key
        bg_file = f"{prefix}_bg.png"
        path = os.path.join(IMG_DIR, bg_file)
        if not os.path.exists(path):
            path = os.path.join(IMG_DIR, f"{prefix}.png")
        if os.path.exists(path):
            self.bg = pygame.image.load(path).convert()
        else:
            self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.bg.fill((0, 0, 128))
        self._play_music('game.mp3')
        score_path = os.path.join(AUDIO_DIR, 'score.wav')
        self.score_sfx = pygame.mixer.Sound(score_path) if os.path.exists(score_path) else None
        q_file = f"{prefix}_question.json"
        file_path = os.path.join(DATA_DIR, q_file)
        data = []
        if os.path.exists(file_path):
            with open(file_path) as f:
                data = json.load(f)
        self.qs = [q for q in data if q.get('difficulty') == game.selected_difficulty]
        random.shuffle(self.qs)
        self.qs = self.qs[:10]
        self.idx = 0
        self.score = 0
        self.limit = TIME_LIMITS.get(game.selected_difficulty, 10)
        self.start = pygame.time.get_ticks()
        self.feedback = False
        self.sel = None
        self.finished = False
        self.opts = []
        if self.qs:
            for i, opt in enumerate(self.qs[0]['options']):
                rect = (100, 200 + i*80, SCREEN_WIDTH - 200, 60)
                self.opts.append(Button(rect, opt, lambda idx=i: self.select(idx)))

    def _play_music(self, fname):
        path = os.path.join(AUDIO_DIR, fname)
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)

    def select(self, idx):
        if self.feedback or self.finished:
            return
        correct = self.qs[self.idx]['answerIndex']
        self.feedback = True
        self.sel = idx
        if idx == correct:
            self.score += 1
        self.feed_time = pygame.time.get_ticks()

    def update(self):
        now = pygame.time.get_ticks()
        if not self.feedback and not self.finished:
            elapsed = (now - self.start) / 1000
            if elapsed >= self.limit:
                self.select(-1)
        if self.feedback and not self.finished and now - self.feed_time > 1500:
            self.idx += 1
            if self.idx >= len(self.qs):
                self.finished = True
                if self.score_sfx:
                    self.score_sfx.play()
                return
            self.start = now
            self.feedback = False
            self.sel = None
            for btn, opt in zip(self.opts, self.qs[self.idx]['options']):
                btn.text = opt

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        if self.finished:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surf.blit(overlay, (0, 0))
            score_txt = pygame.font.Font(None, 64).render(f"Final Score: {self.score}/{len(self.qs)}", True, (255, 255, 0))
            surf.blit(score_txt, score_txt.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50)))
            prompt = pygame.font.Font(None, 48).render("Click to return to menu", True, (255, 255, 255))
            surf.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 50)))
        else:
            if self.qs and self.idx < len(self.qs):
                qtxt = pygame.font.Font(None, 36).render(self.qs[self.idx]['question'], True, (255, 255, 255))
                surf.blit(qtxt, (100, 100))
                pct = max(0, (self.limit - ((pygame.time.get_ticks() - self.start) / 1000)) / self.limit)
                bar_w, bar_h = SCREEN_WIDTH * 0.8, 20
                bar_x, bar_y = (SCREEN_WIDTH - bar_w) / 2, 150
                pygame.draw.rect(surf, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surf, (50, 200, 50), (bar_x, bar_y, bar_w * pct, bar_h))
                for b in self.opts:
                    b.draw(surf)
                if self.feedback:
                    corr = self.qs[self.idx]['answerIndex']
                    for i, b in enumerate(self.opts):
                        if i == corr:
                            pygame.draw.rect(surf, (50, 200, 50), b.rect, 4)
                        elif i == self.sel:
                            pygame.draw.rect(surf, (200, 50, 50), b.rect, 4)
            else:
                msg = pygame.font.Font(None, 48).render('No Questions Available', True, (255, 0, 0))
                surf.blit(msg, (100, 100))
        self.draw_bottom(surf)

    def handle_event(self, evt):
        if self.finished and evt.type == pygame.MOUSEBUTTONDOWN:
            self.game.change_scene(SCENE_MENU)
            return
        for b in self.opts:
            b.handle_event(evt)
        super().handle_event(evt)

class CreditsScene(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg.fill((20, 20, 60))
        self.lines = [
            "FUTA Virtual Game",
            "Developed by FUTA Team",
            "Thank you for playing!",
        ]

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        for i, line in enumerate(self.lines):
            txt = pygame.font.Font(None, 48).render(line, True, (255, 255, 255))
            rect = txt.get_rect(center=(SCREEN_WIDTH/2, 200 + i*60))
            surf.blit(txt, rect)
        self.draw_bottom(surf)

class SettingsScene(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg.fill((60, 20, 20))
        self.volume = pygame.mixer.music.get_volume()
        self.font = pygame.font.Font(None, 36)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        txt = self.font.render("Music Volume", True, (255, 255, 255))
        surf.blit(txt, (100, 200))
        bar_width = 400
        bar_rect = pygame.Rect(100, 250, bar_width, 20)
        pygame.draw.rect(surf, (100, 100, 100), bar_rect)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_width * self.volume)
        pygame.draw.rect(surf, (200, 200, 0), fill_rect)
        self.draw_bottom(surf)

    def handle_event(self, evt):
        if evt.type == pygame.KEYDOWN:
            if evt.key == pygame.K_LEFT:
                self.volume = max(0.0, self.volume - 0.1)
                pygame.mixer.music.set_volume(self.volume)
            elif evt.key == pygame.K_RIGHT:
                self.volume = min(1.0, self.volume + 0.1)
                pygame.mixer.music.set_volume(self.volume)
        super().handle_event(evt)

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        click_path = os.path.join(AUDIO_DIR, 'click.wav')
        self.click_sfx = pygame.mixer.Sound(click_path) if os.path.exists(click_path) else None
        if self.click_sfx:
            self.click_sfx.set_volume(0.7)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Encounter FUTA')
        self.clock = pygame.time.Clock()
        self.scenes = {
            SCENE_SPLASH: SplashScene(self),
            SCENE_MENU: MenuScene(self)
        }
        self.scene = None
        self.selected_school = None
        self.selected_key = None
        self.selected_difficulty = None
        self.player_name = None
        self.running = True
        self.change_scene(SCENE_SPLASH)

    def change_scene(self, name):
        if name == SCENE_CATEGORY:
            self.scenes[name] = CategoryScene(self)
        elif name == SCENE_INPUT:
            self.scenes[name] = InputScene(self, self.selected_difficulty)
        elif name == SCENE_QUIZ:
            self.scenes[name] = QuizScene(self)
        elif name == SCENE_CREDITS:
            self.scenes[name] = CreditsScene(self)
        elif name == SCENE_SETTINGS:
            self.scenes[name] = SettingsScene(self)
        else:
            if name not in self.scenes:
                if name == SCENE_MENU:
                    self.scenes[name] = MenuScene(self)
                elif name == SCENE_SPLASH:
                    self.scenes[name] = SplashScene(self)
        self.scene = self.scenes[name]

    def on_bottom(self, label):
        if label == 'Cancel':
            self.change_scene(SCENE_MENU)
        elif label == 'Credits':
            self.change_scene(SCENE_CREDITS)
        elif label == 'Settings':
            self.change_scene(SCENE_SETTINGS)

    def start_quiz(self, difficulty):
        self.selected_difficulty = difficulty
        self.change_scene(SCENE_INPUT)

    async def run(self):
        while self.running:
            for evt in pygame.event.get():
                if evt.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.handle_event(evt)
            if hasattr(self.scene, 'update'):
                self.scene.update()
            self.scene.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
            await asyncio.sleep(0)
        pygame.quit()

if __name__ == '__main__':
    asyncio.run(Game().run())
