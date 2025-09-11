import pygame
import sys
import os
import random
import glob
import math
import cv2
import threading
from hand_controller import *

pygame.init()
pygame.font.init()
font = pygame.font.SysFont('Comic Sans MS', 30)

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
TILE_SIZE = 80
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

class Monster:
    def __init__(self, grid_x, grid_y, image):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.image = image
        self.health = 1
        self.max_health = 1


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Game")
        self.clock = pygame.time.Clock()
        
        self.player_grid_x = GRID_WIDTH - 1
        self.player_grid_y = GRID_HEIGHT - 1
        self.bullets = []
        self.max_shoot_range = 5
        self.hit_tiles = []
        self.load_player_image()
        self.load_monsters()
        self.spawn_monsters()
        self.show_help_window = False
        # Hand Controller
        self.hand_controller = HandGestureController()
        self.camera_manager = CameraManager()
        self.camera_thread = None
        self.use_hand_control = False

        self.level_completed = False

    def update_monsters(self, move_prob=0.02):
        directions = [(1,0), (-1,0), (0,1), (0,-1)]
        
        occupied = {(m.grid_x, m.grid_y) for m in self.monsters}
        player_pos = (self.player_grid_x, self.player_grid_y)
        
        for monster in self.monsters:
            if random.random() < move_prob:
                random.shuffle(directions)  
                for dx, dy in directions:
                    nx = monster.grid_x + dx
                    ny = monster.grid_y + dy
                    if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                        continue
                    if (nx, ny) == player_pos:
                        continue
                    if (nx, ny) in occupied:
                        continue
                    occupied.remove((monster.grid_x, monster.grid_y))
                    monster.grid_x = nx
                    monster.grid_y = ny
                    occupied.add((nx, ny))
                    break 
   
    def toggle_hand_control(self):
        if self.use_hand_control:
            self.stop_hand_control()
        else:
            self.start_hand_control()
    
    def start_hand_control(self):
        if self.camera_manager.start_camera():
            self.use_hand_control = True
            self.camera_thread = threading.Thread(target=self.hand_control_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            print("Hand control activated!")
            return True
        else:
            print("Cannot start camera!")
            return False
    
    def stop_hand_control(self):
        self.use_hand_control = False
        self.camera_manager.stop_camera()
        print("Hand control deactivated!")
    
    def hand_control_loop(self):
        while self.use_hand_control:
            frame = self.camera_manager.get_frame()
            if frame is None:
                continue
            
            processed_frame, results, shoot_command, shoot_angle = self.hand_controller.process_frame(frame)
            
            if shoot_command:
                game_angle = math.radians(shoot_angle)
                distance = 200  
                self.shoot_bullet(-1*game_angle, distance)
            
            cv2.imshow('Hand Control - Press ESC to close', processed_frame)
            
            if cv2.waitKey(1) & 0xFF == 27:
                self.stop_hand_control()
                break
    

    def draw_ui_icons(self):
        help = pygame.image.load('assets/icons/help.png')
        help = pygame.transform.scale(help, (30, 30))
        self.screen.blit(help, (10, 10)) 
        pygame.draw.rect(self.screen, BLACK, pygame.Rect(10, 10, 30, 50), 2)
        text_surface = font.render('H',0,(0, 0, 0))
        self.screen.blit(text_surface, (15,30))
        cam = pygame.image.load('assets/icons/camera.png')
        cam = pygame.transform.scale(cam, (30, 30))
        self.screen.blit(cam, (50, 10))
        pygame.draw.rect(self.screen, BLACK, pygame.Rect(50, 10, 30, 50), 2)
        text_surface = font.render('C',0,(0, 0, 0))
        self.screen.blit(text_surface, (55,30))


        
    def load_player_image(self):
        player_path = "assets/characters/player.png"
        
        try:
            if os.path.exists(player_path):
                self.player_image = pygame.image.load(player_path)
                self.player_image = pygame.transform.scale(self.player_image, (TILE_SIZE, TILE_SIZE))
            else:
                print(f"File {player_path} not found. Using red square.")
                self.player_image = pygame.Surface((TILE_SIZE, TILE_SIZE))
                self.player_image.fill(RED)
                
        except pygame.error as e:
            print(f"Error loading image: {e}")
            self.player_image = pygame.Surface((TILE_SIZE, TILE_SIZE))
            self.player_image.fill(RED)
    
    def load_monsters(self):
        self.monster_images = []
        monster_folder = "assets/monsters"
        
        if os.path.exists(monster_folder):
            image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
            monster_files = []
            
            for extension in image_extensions:
                monster_files.extend(glob.glob(os.path.join(monster_folder, extension)))
            
            for monster_file in monster_files:
                try:
                    monster_image = pygame.image.load(monster_file)
                    monster_image = pygame.transform.scale(monster_image, (TILE_SIZE, TILE_SIZE))
                    self.monster_images.append(monster_image)
                    print(f"Loaded monster: {os.path.basename(monster_file)}")
                except pygame.error as e:
                    print(f"Error loading monster {monster_file}: {e}")
        
        if not self.monster_images:
            print("No monster images found. Creating default blue squares.")
            default_monster = pygame.Surface((TILE_SIZE, TILE_SIZE))
            default_monster.fill(BLUE)
            self.monster_images.append(default_monster)
    
    def spawn_monsters(self):
        self.monsters = []
        
        if not self.monster_images:
            return
        
        monster_count = random.randint(5, 15)
        occupied_positions = {(self.player_grid_x, self.player_grid_y)}
        
        for _ in range(monster_count):
            attempts = 0
            while attempts < 100:
                grid_x = random.randint(0, GRID_WIDTH - 1)
                grid_y = random.randint(0, GRID_HEIGHT - 1)
                
                if (grid_x, grid_y) not in occupied_positions:
                    monster_image = random.choice(self.monster_images)
                    monster = Monster(grid_x, grid_y, monster_image)
                    

                    monster.max_health = random.randint(1, 6)
                    monster.health = monster.max_health
                    print(monster.max_health)
                    
                    self.monsters.append(monster)
                    occupied_positions.add((grid_x, grid_y))
                    break
                
                attempts += 1
        
        print(f"Spawned {len(self.monsters)} monsters")

    
    def draw_grid(self):
        for x in range(0, SCREEN_WIDTH + 1, TILE_SIZE):
            pygame.draw.line(self.screen, GRAY, (x, 0), (x, SCREEN_HEIGHT))
        
        for y in range(0, SCREEN_HEIGHT + 1, TILE_SIZE):
            pygame.draw.line(self.screen, GRAY, (0, y), (SCREEN_WIDTH, y))
    
    def draw_monsters(self):
        for monster in self.monsters:
            px = monster.grid_x * TILE_SIZE
            py = monster.grid_y * TILE_SIZE
            self.screen.blit(monster.image, (px, py))
            ratio = monster.health / monster.max_health
            bar_w = TILE_SIZE
            bar_h = 6
            pygame.draw.rect(self.screen, (60, 0, 0), (px, py - 8, bar_w, bar_h))
            pygame.draw.rect(self.screen, (180, 0, 0), (px, py - 8, int(bar_w * ratio), bar_h))
            pygame.draw.rect(self.screen, BLACK, (px, py - 8, bar_w, bar_h), 1)
    
    def draw_player(self):
        pixel_x = self.player_grid_x * TILE_SIZE
        pixel_y = self.player_grid_y * TILE_SIZE
        self.screen.blit(self.player_image, (pixel_x, pixel_y))
    
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_h:
                        self.show_help_window = not self.show_help_window
                    elif event.key == pygame.K_c:  
                        self.toggle_hand_control()
                    elif event.key == pygame.K_r:
                        self.spawn_monsters()
                        self.level_completed = False
                    elif event.key == pygame.K_u:
                        self.change_player_character()
                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        if self.player_grid_x > 0:
                            self.player_grid_x -= 1
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        if self.player_grid_x < GRID_WIDTH - 1:
                            self.player_grid_x += 1
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        if self.player_grid_y > 0:
                            self.player_grid_y -= 1
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        if self.player_grid_y < GRID_HEIGHT - 1:
                            self.player_grid_y += 1
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if not self.show_help_window:
                            if not self.use_hand_control:
                                angle, distance = self.get_mouse_angle_and_distance()
                                if distance > 10:
                                    self.shoot_bullet(angle, distance)
        
            self.update_bullets()
            self.update_hit_tiles()
            self.update_monsters(move_prob=0.02)
            self.screen.fill(WHITE)
            self.draw_grid()
            if not self.show_help_window :
                self.draw_ui_icons()
            self.draw_hit_tiles()
            self.draw_monsters()
            self.draw_player()
            self.draw_aim_line()
            self.draw_bullets()
            self.draw_help_window()

            if self.level_completed:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                overlay.set_alpha(180)
                overlay.fill(BLACK)
                self.screen.blit(overlay, (0, 0))

                text1 = font.render("Well Done!", True, WHITE)
                text2 = font.render("Press R to continue", True, WHITE)

                self.screen.blit(text1, (SCREEN_WIDTH//2 - text1.get_width()//2, SCREEN_HEIGHT//2 - 40))
                self.screen.blit(text2, (SCREEN_WIDTH//2 - text2.get_width()//2, SCREEN_HEIGHT//2 + 10))

            pygame.display.flip()
            self.clock.tick(30)  

        if self.use_hand_control:
            self.stop_hand_control()
        self.hand_controller.close()
        pygame.quit()

    def get_mouse_angle_and_distance(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
    
        player_pixel_x = self.player_grid_x * TILE_SIZE + TILE_SIZE // 2
        player_pixel_y = self.player_grid_y * TILE_SIZE + TILE_SIZE // 2
    
        dx = mouse_x - player_pixel_x
        dy = mouse_y - player_pixel_y
    
        distance = (dx**2 + dy**2)**0.5
    
        if distance > 0:
            angle = math.atan2(dy, dx)
            return angle, distance
        return 0, 0

    def shoot_bullet(self, angle, power):
        import math
    
        speed = min(power / 20, 10) 
    
        bullet = {
        'x': self.player_grid_x * TILE_SIZE + TILE_SIZE // 2,
        'y': self.player_grid_y * TILE_SIZE + TILE_SIZE // 2,
        'dx': math.cos(angle) * speed,
        'dy': math.sin(angle) * speed,
        'range_left': self.max_shoot_range * TILE_SIZE
        }
    
        self.bullets.append(bullet)

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['dx']
            bullet['y'] += bullet['dy']
            bullet['range_left'] -= abs(bullet['dx']) + abs(bullet['dy'])
            
            if (bullet['range_left'] <= 0 or 
                bullet['x'] < 0 or bullet['x'] > SCREEN_WIDTH or
                bullet['y'] < 0 or bullet['y'] > SCREEN_HEIGHT):
                self.bullets.remove(bullet)
                continue
            
            bullet_grid_x = int(bullet['x'] // TILE_SIZE)
            bullet_grid_y = int(bullet['y'] // TILE_SIZE)
            
            for monster in self.monsters[:]:
                if monster.grid_x == bullet_grid_x and monster.grid_y == bullet_grid_y:
                    
                    damage = 1
                    monster.health -= damage
                        
                    self.hit_tiles.append({
                            'x': monster.grid_x,
                            'y': monster.grid_y,
                            'timer': 30  
                        })
                        
                    if monster.health <= 0:
                            self.monsters.remove(monster)
                            print(f"Monster destroyed at ({bullet_grid_x}, {bullet_grid_y}) with {damage} damage")
                    else:
                            print(f"Monster hit! Health: {monster.health}/{monster.max_health}")
                    
                    self.bullets.remove(bullet)
                    break
            if not self.monsters:
                self.level_completed = True


    def draw_bullets(self):
        for bullet in self.bullets:
            pygame.draw.circle(self.screen, BLACK, (int(bullet['x']), int(bullet['y'])), 3)

    def draw_aim_line(self):
        if pygame.mouse.get_pressed()[0]:  
            mouse_x, mouse_y = pygame.mouse.get_pos()
            player_pixel_x = self.player_grid_x * TILE_SIZE + TILE_SIZE // 2
            player_pixel_y = self.player_grid_y * TILE_SIZE + TILE_SIZE // 2
        
            distance = ((mouse_x - player_pixel_x)**2 + (mouse_y - player_pixel_y)**2)**0.5
            max_distance = self.max_shoot_range * TILE_SIZE
        
            if distance > max_distance:
                ratio = max_distance / distance
                end_x = player_pixel_x + (mouse_x - player_pixel_x) * ratio
                end_y = player_pixel_y + (mouse_y - player_pixel_y) * ratio
            else:
                end_x, end_y = mouse_x, mouse_y
        
            pygame.draw.line(self.screen, RED, (player_pixel_x, player_pixel_y), (end_x, end_y), 2)
    def update_hit_tiles(self):
        for hit_tile in self.hit_tiles[:]:
            hit_tile['timer'] -= 1
            if hit_tile['timer'] <= 0:
                self.hit_tiles.remove(hit_tile)
    def draw_hit_tiles(self):
        for hit_tile in self.hit_tiles:
            pixel_x = hit_tile['x'] * TILE_SIZE
            pixel_y = hit_tile['y'] * TILE_SIZE
            
            red_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            red_surface.set_alpha(100)  #
            red_surface.fill(RED)
            self.screen.blit(red_surface, (pixel_x, pixel_y))

    def draw_help_window(self):
        if not self.show_help_window:
            return
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        window_width = 350
        window_height = 280
        window_x = (SCREEN_WIDTH - window_width) // 2
        window_y = (SCREEN_HEIGHT - window_height) // 2
        
        window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        pygame.draw.rect(self.screen, WHITE, window_rect)
        pygame.draw.rect(self.screen, BLACK, window_rect, 3)
        
        title_text = font.render("GAME CONTROLS", True, BLACK)
        title_rect = title_text.get_rect(center=(window_x + window_width//2, window_y + 25))
        self.screen.blit(title_text, title_rect)
        
        pygame.draw.line(self.screen, BLACK, 
                        (window_x + 20, window_y + 45), 
                        (window_x + window_width - 20, window_y + 45), 2)
        
        font_text = pygame.font.Font(None, 22)
        help_lines = [
    "WASD / Arrow Keys  -  Move Player",
    "Mouse Click        -  Shoot",
    "C                  -  Toggle Hand Control",
    "R                  -  Respawn Monsters", 
    "U                  -  Change Character",
    "H                  -  Toggle Help",
    "ESC                -  Exit Game",
    "",
    "HAND CONTROL:",
    "• Point with index finger",
    "• Make gun gesture (thumb + index)",
    "• Release gesture to shoot",
    "",
    "Press H again to close"
                    ]

        y_offset = 65
        for line in help_lines:
            if line.startswith("GAMEPLAY:"):
                text_surface = pygame.font.Font(None, 24).render(line, True, BLUE)
            elif line.startswith("•"):
                text_surface = font_text.render(line, True, (50, 50, 50))
            elif line.startswith("Press H"):
                text_surface = pygame.font.Font(None, 20).render(line, True, RED)
            elif line and not line.startswith("•"):
                text_surface = font_text.render(line, True, BLACK)
            else:
                y_offset += 15
                continue
                
            if line:
                self.screen.blit(text_surface, (window_x + 20, window_y + y_offset))
            y_offset += 20

    def change_player_character(self):
        character_folder = "assets/characters"
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
        character_files = []

        for ext in image_extensions:
            character_files.extend(glob.glob(os.path.join(character_folder, ext)))

        if character_files:
            new_character_file = random.choice(character_files)
            try:
                new_image = pygame.image.load(new_character_file)
                new_image = pygame.transform.scale(new_image, (TILE_SIZE, TILE_SIZE+10))
                self.player_image = new_image
                print(f"Player character changed to {os.path.basename(new_character_file)}")
            except pygame.error as e:
                print(f"Error loading character {new_character_file}: {e}")

if __name__ == "__main__":
    game = Game()
    game.run()
