import pygame
import sys
import os
import random
import glob
import math

pygame.init()

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
            pixel_x = monster.grid_x * TILE_SIZE
            pixel_y = monster.grid_y * TILE_SIZE
            self.screen.blit(monster.image, (pixel_x, pixel_y))
    
    def draw_player(self):
        pixel_x = self.player_grid_x * TILE_SIZE
        pixel_y = self.player_grid_y * TILE_SIZE
        self.screen.blit(self.player_image, (pixel_x, pixel_y))
    
    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self.player_grid_x > 0:
                self.player_grid_x -= 1
        
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self.player_grid_x < GRID_WIDTH - 1:
                self.player_grid_x += 1
        
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if self.player_grid_y > 0:
                self.player_grid_y -= 1
        
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            if self.player_grid_y < GRID_HEIGHT - 1:
                self.player_grid_y += 1

    
    def run(self):
        running = True
    
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:  
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.spawn_monsters()
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
                    angle, distance = self.get_mouse_angle_and_distance()
                    if distance > 10:
                        self.shoot_bullet(angle, distance)
        
            self.update_bullets()
            self.update_hit_tiles()
            self.screen.fill(WHITE)
            self.draw_grid()
            self.draw_hit_tiles()
            self.draw_monsters()
            self.draw_player()
            self.draw_aim_line()
            self.draw_bullets()
        
            pygame.display.flip()
            self.clock.tick(30)  


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

if __name__ == "__main__":
    game = Game()
    game.run()
