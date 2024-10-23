import time
import threading
import json
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta

class ResilienceManager:
    """
    Gestor de resiliencia del sistema.
    Maneja las desconexiones, reconexiones y estado de los componentes.
    """
    def __init__(self):
        self.components = {}
        self.timeouts = {
            'taxi': 10,      # 10 segundos para taxis
            'sensor': 5,     # 5 segundos para sensores
            'customer': 15   # 15 segundos para clientes
        }
        self.callbacks = {
            'taxi': {},
            'sensor': {},
            'customer': {}
        }
        self.lock = threading.Lock()
        self.monitor_thread = threading.Thread(target=self._monitor_components, daemon=True)
        self.monitor_thread.start()

    def register_component(self, component_type: str, component_id: str, initial_state: Dict = None):
        """Registra un nuevo componente en el sistema"""
        with self.lock:
            self.components[f"{component_type}_{component_id}"] = {
                'type': component_type,
                'id': component_id,
                'state': initial_state or {},
                'last_seen': time.time(),
                'status': 'ACTIVE',
                'reconnect_attempts': 0
            }
            print(f"Componente registrado: {component_type} {component_id}")

    def update_component(self, component_type: str, component_id: str, state: Dict = None):
        """Actualiza el estado de un componente"""
        key = f"{component_type}_{component_id}"
        with self.lock:
            if key in self.components:
                self.components[key]['last_seen'] = time.time()
                self.components[key]['status'] = 'ACTIVE'
                if state:
                    self.components[key]['state'].update(state)
                self.components[key]['reconnect_attempts'] = 0

    def register_callback(self, component_type: str, event: str, callback: Callable):
        """Registra un callback para eventos de componentes"""
        if component_type not in self.callbacks:
            self.callbacks[component_type] = {}
        self.callbacks[component_type][event] = callback

    def _monitor_components(self):
        """Monitoriza el estado de los componentes"""
        while True:
            current_time = time.time()
            with self.lock:
                for comp_key, comp_info in self.components.items():
                    if comp_info['status'] != 'INACTIVE':
                        timeout = self.timeouts.get(comp_info['type'], 10)
                        if current_time - comp_info['last_seen'] > timeout:
                            self._handle_component_timeout(comp_key, comp_info)
            time.sleep(1)

    def _handle_component_timeout(self, comp_key: str, comp_info: Dict):
        """Maneja el timeout de un componente"""
        comp_type = comp_info['type']
        comp_id = comp_info['id']
        
        # Actualizar estado
        self.components[comp_key]['status'] = 'INACTIVE'
        self.components[comp_key]['reconnect_attempts'] += 1

        # Ejecutar callbacks registrados
        if comp_type in self.callbacks and 'timeout' in self.callbacks[comp_type]:
            try:
                self.callbacks[comp_type]['timeout'](comp_id, comp_info['state'])
            except Exception as e:
                print(f"Error en callback de timeout para {comp_type} {comp_id}: {e}")

    def is_component_active(self, component_type: str, component_id: str) -> bool:
        """Verifica si un componente está activo"""
        key = f"{component_type}_{component_id}"
        return self.components.get(key, {}).get('status') == 'ACTIVE'

    def get_component_state(self, component_type: str, component_id: str) -> Optional[Dict]:
        """Obtiene el estado actual de un componente"""
        key = f"{component_type}_{component_id}"
        return self.components.get(key, {}).get('state')

    def handle_component_recovery(self, component_type: str, component_id: str):
        """Maneja la recuperación de un componente"""
        key = f"{component_type}_{component_id}"
        if key in self.components:
            with self.lock:
                if self.components[key]['status'] == 'INACTIVE':
                    self.components[key]['status'] = 'ACTIVE'
                    self.components[key]['last_seen'] = time.time()
                    self.components[key]['reconnect_attempts'] = 0
                    
                    # Ejecutar callbacks de recuperación
                    if component_type in self.callbacks and 'recovery' in self.callbacks[component_type]:
                        try:
                            self.callbacks[component_type]['recovery'](component_id, self.components[key]['state'])
                        except Exception as e:
                            print(f"Error en callback de recuperación para {component_type} {component_id}: {e}")

    def get_inactive_components(self, component_type: Optional[str] = None) -> Dict:
        """Obtiene lista de componentes inactivos"""
        inactive = {}
        with self.lock:
            for key, info in self.components.items():
                if info['status'] == 'INACTIVE':
                    if not component_type or info['type'] == component_type:
                        inactive[key] = info
        return inactive