import os
from PIL import Image
import random

class OCRScanner:
    @staticmethod
    def scan_receipt(file_path):
        """
        Simulates OCR scanning of a receipt.
        In a real production environment, this would use Tesseract or EasyOCR.
        """
        if not os.path.exists(file_path):
            return None
        
        # Simulate processing time
        # In a real app, pytesseract.image_to_string(Image.open(file_path)) would be here
        
        # Mock extracted data patterns
        mock_data = [
            {"merchant": "Tech Solutions Inc.", "amount": 1250.00, "type": "Equipment"},
            {"merchant": "Cloud Services", "amount": 89.99, "type": "Subsciption"},
            {"merchant": "Office Depot", "amount": 45.50, "type": "Supplies"},
            {"merchant": "Global Logistics", "amount": 2300.75, "type": "Shipping"},
            {"merchant": "Unknown Vendor", "amount": 15000.00, "type": "Generic"}
        ]
        
        # Choose a random mock result to simulate different receipt totals
        result = random.choice(mock_data)
        
        return {
            "success": True,
            "data": result,
            "raw_text": f"MOCK RECEIPT TEXT\nMERCHANT: {result['merchant']}\nTOTAL: E{result['amount']}\nDATE: {random.randint(1,12)}/2026"
        }
