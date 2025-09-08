import re
import random
from typing import Dict

class DataAnonymizer:
    def anonymize_personal_info(self, text: str) -> str:
        """Replace names, locations, and specific numbers with placeholders."""
        # Replace names (simple example, refine regex as needed)
        text = re.sub(r'\b[A-Z][a-z]+\b', 'NAME', text)
        # Replace locations
        text = re.sub(r'\b(?:New York|Los Angeles|Cairo)\b', 'LOCATION', text)
        # Replace specific numbers
        text = re.sub(r'\b\d+\b', 'NUMBER', text)
        return text
    
    def add_noise_to_metadata(self, data: Dict) -> Dict:
        """Add random noise to metadata fields."""
        noisy_data = data.copy()
        for key, value in noisy_data.items():
            if isinstance(value, (int, float)):
                # Add random noise to numerical values
                noise = random.uniform(-0.1, 0.1) * value
                noisy_data[key] = value + noise
            elif isinstance(value, str):
                # Add noise to string fields by shuffling characters
                noisy_data[key] = ''.join(random.sample(value, len(value)))
        return noisy_data 