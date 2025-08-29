import cv2
import mediapipe as mp
import time
import math
import numpy as np

class HandGestureSettings:
    POSITION_HISTORY_SIZE = 5
    MOVEMENT_THRESHOLD = 50
    DIRECTION_HOLD_TIME = 0.1
    CENTER_ZONE = 50
    MIN_DETECTION_CONFIDENCE = 0.7
    MIN_TRACKING_CONFIDENCE = 0.5
    

    SHOOT_GESTURE_THRESHOLD = 30  
    SHOOT_COOLDOWN = 500  

class CameraSettings:
    WIDTH = 640
    HEIGHT = 480
    FPS = 30


class HandGestureController:
    def __init__(self):
        self.last_positions = []
        self.position_history_size = HandGestureSettings.POSITION_HISTORY_SIZE
        self.movement_threshold = HandGestureSettings.MOVEMENT_THRESHOLD
        self.last_direction = (0, 0)
        self.direction_hold_time = HandGestureSettings.DIRECTION_HOLD_TIME
        self.last_direction_time = 0
        self.center_zone = HandGestureSettings.CENTER_ZONE
        
        self.is_ready_to_shoot = False
        self.shoot_angle = 0
        self.finger_angle = 0
        self.last_shoot_time = 0
        self.shoot_cooldown = HandGestureSettings.SHOOT_COOLDOWN
        
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=HandGestureSettings.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=HandGestureSettings.MIN_TRACKING_CONFIDENCE
        )
        
    def add_position(self, x, y):
        self.last_positions.append((x, y))
        if len(self.last_positions) > self.position_history_size:
            self.last_positions.pop(0)
    
    def get_smoothed_position(self):
        if not self.last_positions:
            return None
        
        avg_x = sum(pos[0] for pos in self.last_positions) / len(self.last_positions)
        avg_y = sum(pos[1] for pos in self.last_positions) / len(self.last_positions)
        return avg_x, avg_y
    
    def calculate_angle_between_points(self, point1, point2, point3):
        v1 = np.array([point1[0] - point2[0], point1[1] - point2[1]])
        v2 = np.array([point3[0] - point2[0], point3[1] - point2[1]])
        
        dot_product = np.dot(v1, v2)
        norms = np.linalg.norm(v1) * np.linalg.norm(v2)
        
        if norms == 0:
            return 0
            
        cos_angle = dot_product / norms
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)
        return math.degrees(angle)
    
    def get_direction_angle(self, point1, point2):
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        
        angle_rad = math.atan2(-dy, dx)  
        angle_deg = math.degrees(angle_rad)
        
        if angle_deg < 0:
            angle_deg += 360
            
        return angle_deg
    
    def is_shoot_gesture(self, hand_landmarks, frame_width, frame_height):
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        thumb_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_MCP]
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        index_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
        middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        middle_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
        
        wrist_px = [int(wrist.x * frame_width), int(wrist.y * frame_height)]
        thumb_tip_px = [int(thumb_tip.x * frame_width), int(thumb_tip.y * frame_height)]
        thumb_mcp_px = [int(thumb_mcp.x * frame_width), int(thumb_mcp.y * frame_height)]
        index_tip_px = [int(index_tip.x * frame_width), int(index_tip.y * frame_height)]
        index_mcp_px = [int(index_mcp.x * frame_width), int(index_mcp.y * frame_height)]
        index_pip_px = [int(index_pip.x * frame_width), int(index_pip.y * frame_height)]
        
        index_straight = index_tip.y < index_pip.y
        
        middle_bent = middle_tip.y > middle_pip.y
        
        self.finger_angle = self.calculate_angle_between_points(
            thumb_tip_px, wrist_px, index_tip_px
        )
        
        self.shoot_angle = self.get_direction_angle(index_mcp_px, index_tip_px)
        
        distance = math.sqrt((thumb_tip_px[0] - index_tip_px[0])**2 + 
                           (thumb_tip_px[1] - index_tip_px[1])**2)
        
        angle_ok = 60 < self.finger_angle < 120  
        distance_ok = distance > 60
        
        return (index_straight and middle_bent and angle_ok and distance_ok)
    
    def draw_angle_info(self, frame, thumb_pos, index_pos, wrist_pos):
        h, w = frame.shape[:2]
        
        cv2.line(frame, tuple(wrist_pos), tuple(thumb_pos), (255, 0, 255), 2)
        cv2.line(frame, tuple(wrist_pos), tuple(index_pos), (255, 0, 255), 2)
        cv2.line(frame, tuple(thumb_pos), tuple(index_pos), (0, 255, 255), 2)
        
        cv2.circle(frame, tuple(wrist_pos), 8, (255, 255, 255), -1)
        cv2.circle(frame, tuple(thumb_pos), 10, (255, 0, 0), -1)
        cv2.circle(frame, tuple(index_pos), 10, (0, 0, 255), -1)
        
        shoot_length = 120
        end_x = int(index_pos[0] + shoot_length * math.cos(math.radians(self.shoot_angle)))
        end_y = int(index_pos[1] - shoot_length * math.sin(math.radians(self.shoot_angle)))
        cv2.arrowedLine(frame, tuple(index_pos), (end_x, end_y), (0, 255, 0), 4, tipLength=0.3)
        
        info_y = 30
        cv2.putText(frame, f"Finger Angle: {self.finger_angle:.1f}°", 
                   (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Shoot Direction: {self.shoot_angle:.1f}°", 
                   (10, info_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        status = "READY TO SHOOT!" if self.is_ready_to_shoot else "AIM..."
        color = (0, 255, 0) if self.is_ready_to_shoot else (0, 255, 255)
        cv2.putText(frame, status, (10, info_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        cv2.putText(frame, "Make L-shape: Index straight, thumb up, others bent", 
                   (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, "Release gesture to shoot", 
                   (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def get_direction(self, results, frame_width, frame_height):
        if not results.multi_hand_landmarks:
            return 0, 0
        
        current_time = time.time()
        
        for hand_landmarks in results.multi_hand_landmarks:
            index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            x = int(index_tip.x * frame_width)
            y = int(index_tip.y * frame_height)
            
            self.add_position(x, y)
            
            smoothed_pos = self.get_smoothed_position()
            if not smoothed_pos:
                return 0, 0
            
            smooth_x, smooth_y = smoothed_pos
            
            center_x, center_y = frame_width // 2, frame_height // 2
            
            dx = smooth_x - center_x
            dy = smooth_y - center_y
            
            if abs(dx) < self.center_zone and abs(dy) < self.center_zone:
                return 0, 0
            
            new_direction = (0, 0)
            
            if abs(dx) > abs(dy): 
                if abs(dx) > self.movement_threshold:
                    new_direction = (1 if dx > 0 else -1, 0)
            else:
                if abs(dy) > self.movement_threshold:
                    new_direction = (0, 1 if dy > 0 else -1)
            
            if (new_direction != self.last_direction and 
                current_time - self.last_direction_time < self.direction_hold_time):
                return self.last_direction
            
            if new_direction != (0, 0):
                self.last_direction = new_direction
                self.last_direction_time = current_time
            
            return new_direction
        
        return 0, 0
    
    def process_frame(self, frame):
        frame = cv2.flip(frame, 1)
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        shoot_command = False
        shoot_angle = 0
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                h, w, _ = frame.shape
                
                self.mp_drawing.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(100, 100, 100), thickness=1, circle_radius=1),
                    self.mp_drawing.DrawingSpec(color=(150, 150, 150), thickness=1)
                )
                
                wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
                thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                
                wrist_px = [int(wrist.x * w), int(wrist.y * h)]
                thumb_px = [int(thumb_tip.x * w), int(thumb_tip.y * h)]
                index_px = [int(index_tip.x * w), int(index_tip.y * h)]
                
                if self.is_shoot_gesture(hand_landmarks, w, h):
                    if not self.is_ready_to_shoot:
                        self.is_ready_to_shoot = True
                    
                    self.draw_angle_info(frame, thumb_px, index_px, wrist_px)
                    
                else:
                    if self.is_ready_to_shoot:
                        current_time = time.time() * 1000
                        if current_time - self.last_shoot_time > self.shoot_cooldown:
                            shoot_command = True
                            shoot_angle = self.shoot_angle
                            self.last_shoot_time = current_time
                            
                            cv2.putText(frame, "SHOOT!", (w//2 - 50, h//2), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
                    
                    self.is_ready_to_shoot = False
                    
                    cv2.circle(frame, tuple(index_px), 8, (255, 255, 0), -1)
                    cv2.circle(frame, tuple(thumb_px), 6, (255, 255, 0), -1)
                
                center_x, center_y = w // 2, h // 2
                cv2.rectangle(frame, 
                             (center_x - self.center_zone, center_y - self.center_zone), 
                             (center_x + self.center_zone, center_y + self.center_zone), 
                             (100, 100, 100), 1)
        
        return frame, results, shoot_command, shoot_angle
    
    def close(self):
        self.hands.close()


class CameraManager:
    def __init__(self):
        self.cap = None
        self.is_active = False
        
    def start_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CameraSettings.WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CameraSettings.HEIGHT)
                self.cap.set(cv2.CAP_PROP_FPS, CameraSettings.FPS)
                self.is_active = True
                return True
            else:
                self.cap = None
                return False
        except Exception as e:
            print(f"Error starting camera: {e}")
            self.cap = None
            return False
            
    def stop_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_active = False
        cv2.destroyAllWindows()
        
    def get_frame(self):
        if not self.is_active or not self.cap:
            return None
            
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
        
    def toggle_camera(self):
        if self.is_active:
            self.stop_camera()
            return False
        else:
            return self.start_camera()
            
    def __del__(self):
        if self.cap:
            self.cap.release()
