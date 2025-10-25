from ultralytics import YOLO
import cv2
import os
import uuid
from typing import List, Dict, Optional
import numpy as np
import torch
import easyocr

class PlateService:
    def __init__(self):
        self.plate_model = YOLO("app/AI_model/Model_plate.pt")
        self.ocr_model = torch.hub.load('ultralytics/yolov5', 'custom', path='app/AI_model/OCR.pt')
        self.easyocr_reader = easyocr.Reader(['en'], gpu=True)
        self.crops_dir = "app/upload/crops"
        os.makedirs(self.crops_dir, exist_ok=True)
    
    def recognize_text_from_crop(self, crop_image: np.ndarray) -> str:
        # Nhận diện text từ ảnh crop biển số 
        results = self.ocr_model(crop_image)
        bb_list = results.pandas().xyxy[0].values.tolist()
        
        # Validate số lượng ký tự detect được
        if len(bb_list) == 0 or len(bb_list) < 7 or len(bb_list) > 10:
            return "unknown"
        
        # Tính tọa độ center của mỗi ký tự
        center_list = []
        y_sum = 0
        
        for bb in bb_list:
            x_c = (bb[0] + bb[2]) / 2
            y_c = (bb[1] + bb[3]) / 2
            y_sum += y_c
            center_list.append([x_c, y_c, bb[-1]])
        
        # Tính y trung bình để chia 2 dòng
        y_mean = int(y_sum / len(bb_list))
        
        # Chia ký tự thành 2 dòng dựa trên y_mean
        line_1 = []
        line_2 = []
        
        for c in center_list:
            if int(c[1]) > y_mean:
                line_2.append(c)
            else:
                line_1.append(c)
        
        # Sắp xếp ký tự theo tọa độ x và ghép thành chuỗi
        license_plate = ""
        for l1 in sorted(line_1, key=lambda x: x[0]):
            license_plate += str(l1[2])
        license_plate += "-"
        for l2 in sorted(line_2, key=lambda x: x[0]):
            license_plate += str(l2[2])
        
        return license_plate
     
    def detect_and_recognize(self, image: np.ndarray, timestamp: Optional[float] = None, frame_number: Optional[int] = None) -> List[Dict]:
        # Detect biển số từ ảnh và nhận diện text
        results = self.plate_model(image, verbose=False)
        detected_plates = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Lấy tọa độ bbox và confidence
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                
                # Crop vùng biển số
                crop = image[y1:y2, x1:x2]
                
                # Lưu crop vào thư mục
                crop_filename = f"{uuid.uuid4()}.jpg"
                crop_path = os.path.join(self.crops_dir, crop_filename)
                cv2.imwrite(crop_path, crop)
                
                # Nhận diện text từ crop
                plate_text = self.recognize_text_from_crop(crop)
                
                # Tạo dict chứa thông tin biển số
                plate_data = {
                    "plate_number": plate_text,
                    "confidence": confidence,
                    "crop_path": crop_path.replace("\\", "/"),
                    "bbox": [x1, y1, x2, y2],
                    "timestamp": timestamp,
                    "frame_number": frame_number
                }
                
                detected_plates.append(plate_data)
        
        return detected_plates
    
    def get_unique_plates(self, detected_plates: List[Dict]) -> List[Dict]:
        # Lọc biển số trùng lặp, giữ biển có confidence cao nhất
        unique_plates_dict = {}
        
        for plate in detected_plates:
            plate_number = plate["plate_number"]
            if not plate_number:
                continue
            
            # Nếu biển số chưa có, thêm vào dict
            if plate_number not in unique_plates_dict:
                unique_plates_dict[plate_number] = plate
            else:
                # Nếu đã có, so sánh confidence và giữ cái cao hơn
                if plate["confidence"] > unique_plates_dict[plate_number]["confidence"]:
                    unique_plates_dict[plate_number] = plate
        
        return list(unique_plates_dict.values())

