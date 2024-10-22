from confluent_kafka import Producer, Consumer
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class SystemTester:
    def __init__(self):
        self.base_url = 'http://localhost:8000'
        self.kafka_config = {'bootstrap.servers': 'localhost:9092'}
        
        # Configurar sesión de requests con reintentos
        self.session = requests.Session()
        retries = Retry(total=5,
                       backoff_factor=0.1,
                       status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))

    def make_request(self, endpoint):
        try:
            response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            return None

    def test_service_health(self):
        try:
            response = self.make_request('/health')
            if response and response.get('status') == 'OK':
                print(f"Health check: {response}")
                return True
            return False
        except Exception as e:
            print(f"Error checking health: {e}")
            return False

    def test_map(self):
        try:
            response = self.make_request('/map')
            if response:
                print(f"Map response: {response}")
                return True
            return False
        except Exception as e:
            print(f"Error checking map: {e}")
            return False

    def test_system_status(self):
        try:
            response = self.make_request('/system/status')
            if response:
                print(f"System status: {response}")
                return True
            return False
        except Exception as e:
            print(f"Error checking system status: {e}")
            return False

    def send_customer_request(self):
        producer = Producer(self.kafka_config)
        request = {
            'customer_id': '1',
            'destination': [10, 10],
            'timestamp': time.time()
        }
        
        producer.produce('customerrequests', json.dumps(request).encode('utf-8'))
        producer.flush()
        print(f"Sent customer request: {request}")
        return True

    def test_taxi_status(self):
        producer = Producer(self.kafka_config)
        status = {
            'taxi_id': '1',
            'position': [1, 1],
            'state': 'IDLE'
        }
        
        producer.produce('taxi_status', json.dumps(status).encode('utf-8'))
        producer.flush()
        print(f"Sent taxi status: {status}")
        
        # Esperar a que el estado se actualice
        time.sleep(2)
        try:
            response = self.make_request('/taxis')
            if response:
                print(f"Taxis status: {response}")
                return True
            return False
        except Exception as e:
            print(f"Error checking taxis: {e}")
            return False

    def listen_for_response(self):
        consumer = Consumer({
            **self.kafka_config,
            'group.id': 'test-consumer',
            'auto.offset.reset': 'earliest'
        })
        consumer.subscribe(['centralresponses'])
        
        timeout = time.time() + 10
        while time.time() < timeout:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            try:
                response = json.loads(msg.value().decode('utf-8'))
                print(f"Received central response: {response}")
                return True
            except Exception as e:
                print(f"Error processing response: {e}")
        
        print("Timeout waiting for response")
        return False

    def run_tests(self):
        print("\n=== Starting System Tests ===\n")
        
        tests = [
            ("Service Health", self.test_service_health),
            ("Map Service", self.test_map),
            ("System Status", self.test_system_status),
            ("Taxi Status", self.test_taxi_status),
            ("Customer Request", self.send_customer_request),
            ("Central Response", self.listen_for_response)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\nTesting {test_name}...")
            time.sleep(1)  # Pequeña pausa entre tests
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        
        print("\n=== Test Results Summary ===")
        print(f"Total tests: {len(tests)}")
        passed = sum(1 for _, success in results if success)
        print(f"Passed: {passed}")
        print(f"Failed: {len(tests) - passed}")
        
        if passed == len(tests):
            print("\n🎉 All Tests Completed Successfully 🎉")
        else:
            print("\n❌ Some Tests Failed")
            print("\nFailed Tests:")
            for name, success in results:
                if not success:
                    print(f"- {name}")

def main():
    tester = SystemTester()
    tester.run_tests()

if __name__ == "__main__":
    main()  