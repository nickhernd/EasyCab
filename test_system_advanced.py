from confluent_kafka import Producer, Consumer
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

class AdvancedSystemTester:
    def __init__(self):
        self.base_url = 'http://localhost:8000'
        self.kafka_config = {'bootstrap.servers': 'localhost:9092'}
        self.session = self.setup_session()

    def setup_session(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1)
        session.mount('http://', HTTPAdapter(max_retries=retries))
        return session

    def test_multiple_taxis(self):
        """Prueba el sistema con múltiples taxis moviéndose simultáneamente"""
        producer = Producer(self.kafka_config)
        positions = [
            ([1, 1], 'IDLE'),
            ([5, 5], 'MOVING'),
            ([10, 10], 'IDLE')
        ]
        
        for i, (pos, state) in enumerate(positions):
            status = {
                'taxi_id': str(i),
                'position': pos,
                'state': state
            }
            producer.produce('taxi_status', json.dumps(status).encode('utf-8'))
        producer.flush()
        
        time.sleep(2)
        response = self.session.get(f"{self.base_url}/system/status")
        return response.json()

    def test_concurrent_requests(self):
        """Prueba múltiples solicitudes de clientes concurrentes"""
        producer = Producer(self.kafka_config)
        requests = [
            {'customer_id': str(i), 'destination': [i*2, i*2]} 
            for i in range(5)
        ]
        
        for req in requests:
            producer.produce('customerrequests', 
                           json.dumps(req).encode('utf-8'))
        producer.flush()
        
        time.sleep(2)
        return len(requests)

    def test_taxi_movement(self):
        """Prueba el movimiento de taxis en el mapa"""
        producer = Producer(self.kafka_config)
        movements = [
            ([1, 1], 'IDLE'),
            ([1, 2], 'MOVING'),
            ([2, 2], 'MOVING'),
            ([2, 3], 'MOVING'),
            ([3, 3], 'IDLE')
        ]
        
        taxi_id = '1'
        results = []
        
        for pos, state in movements:
            status = {
                'taxi_id': taxi_id,
                'position': pos,
                'state': state
            }
            producer.produce('taxi_status', json.dumps(status).encode('utf-8'))
            producer.flush()
            time.sleep(1)
            
            response = self.session.get(f"{self.base_url}/taxis/{taxi_id}")
            results.append(response.json())
        
        return results

    def test_system_load(self):
        """Prueba el sistema bajo carga"""
        def send_requests():
            producer = Producer(self.kafka_config)
            for i in range(10):
                request = {
                    'customer_id': f'load_test_{i}',
                    'destination': [i, i],
                    'timestamp': time.time()
                }
                producer.produce('customerrequests', 
                               json.dumps(request).encode('utf-8'))
                time.sleep(0.1)
            producer.flush()

        threads = [
            threading.Thread(target=send_requests)
            for _ in range(5)
        ]
        
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        end_time = time.time()
        
        return end_time - start_time

    def run_advanced_tests(self):
        print("\n=== Starting Advanced System Tests ===\n")
        
        tests = [
            ("Multiple Taxis", self.test_multiple_taxis),
            ("Concurrent Requests", self.test_concurrent_requests),
            ("Taxi Movement", self.test_taxi_movement),
            ("System Load", self.test_system_load)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\nRunning {test_name} test...")
            try:
                result = test_func()
                success = True
                print(f"Result: {result}")
            except Exception as e:
                success = False
                print(f"Error: {e}")
            
            results.append((test_name, success))
            print(f"{'✅' if success else '❌'} {test_name} test completed")

        print("\n=== Advanced Test Results ===")
        for name, success in results:
            print(f"{name}: {'✅' if success else '❌'}")

if __name__ == "__main__":
    tester = AdvancedSystemTester()
    tester.run_advanced_tests()