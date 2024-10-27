import json
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

def load_locations(filename: str) -> Dict[str, Tuple[int, int]]:
    """Cargar localizaciones desde archivo JSON"""
    locations = {}
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            for loc in data['locations']:
                loc_id = loc['Id']
                x, y = map(int, loc['POS'].split(','))
                locations[loc_id] = (x, y)
                logger.info(f"Localización {loc_id} cargada en ({x}, {y})")
    except Exception as e:
        logger.error(f"Error cargando localizaciones: {e}")
        raise
    
    return locations