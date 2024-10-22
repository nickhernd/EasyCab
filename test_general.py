import time
import json
import threading
from confluent_kafka import Producer, Consumer
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class EasyCabTestSuite:
    def __init__(self):
        self.base_url = 'http://localhost:8000'
        self.kafka_broker = 'kafka:9092'
        self.test_results = {}
        
        # Configure requests session with retries
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1)
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        
        # Configure Kafka producer
        self.producer_config = {
            'bootstrap.servers': self.kafka_broker,
            'client.id': 'test-suite'
        }
        
        # Configure Kafka consumer
        self.consumer_config = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': 'test-suite',
            'auto.offset.reset': 'earliest'
        }

    def test_central_api(self):
        """Test all Central API endpoints"""
        print("\n=== Testing Central API ===")
        
        endpoints = {
            'health': '/health',
            'map': '/map',
            'system_status': '/system/status',
            'taxis': '/taxis',
            'active_rides': '/rides/active',
            'queue_status': '/queue/status'
        }
        
        for name, endpoint in endpoints.items():
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                response.raise_for_status()
                print(f"✅ {name}: {response.status_code}")
                self.test_results[f'api_{name}'] = True
            except Exception as e:
                print(f"❌ {name}: {str(e)}")
                self.test_results[f'api_{name}'] = False

    def test_kafka_topics(self):
        """Test Kafka topics existence and connectivity"""
        print("\n=== Testing Kafka Topics ===")
        
        topics = [
            'customerrequests',
            'centralresponses',
            'taxistatus',
            'taxiinstructions'
        ]
        
        producer = Producer(self.producer_config)
        
        for topic in topics:
            try:
                # Try to produce a test message
                producer.produce(
                    topic,
                    json.dumps({'test': 'message'}).encode('utf-8')
                )
                producer.flush()
                print(f"✅ Topic {topic} is accessible")
                self.test_results[f'kafka_topic_{topic}'] = True
            except Exception as e:
                print(f"❌ Topic {topic} test failed: {str(e)}")
                self.test_results[f'kafka_topic_{topic}'] = False

    def test_taxi_workflow(self):
        """Test complete taxi service workflow"""
        print("\n=== Testing Taxi Workflow ===")
        
        producer = Producer(self.producer_config)
        consumer = Consumer(self.consumer_config)
        consumer.subscribe(['centralresponses'])
        
        # Send customer request
        request = {
            'customer_id': 'test_customer',
            'destination': [10, 10],
            'pickup_position': [1, 1],
            'timestamp': time.time()
        }
        
        try:
            # Send request
            producer.produce(
                'customerrequests',
                json.dumps(request).encode('utf-8')
            )
            producer.flush()
            print("✅ Customer request sent")
            
            # Wait for response
            start_time = time.time()
            response_received = False
            
            while time.time() - start_time < 10:  # 10 second timeout
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    continue
                    
                response = json.loads(msg.value().decode('utf-8'))
                print(f"✅ Received response: {response}")
                response_received = True
                break
            
            if not response_received:
                print("❌ No response received from central")
            
            self.test_results['workflow_test'] = response_received
            
        except Exception as e:
            print(f"❌ Workflow test failed: {str(e)}")
            self.test_results['workflow_test'] = False
        
        finally:
            consumer.close()

    def test_taxi_sensor_integration(self):
        """Test taxi sensor data flow"""
        print("\n=== Testing Sensor Integration ===")
        
        producer = Producer(self.producer_config)
        
        # Simulate sensor data
        sensor_data = {
            'taxi_id': 'test_taxi',
            'timestamp': time.time(),
            'sensors': {
                'lidar': {'status': 'OK', 'range': 100},
                'camera': {'status': 'OK', 'visibility': 100},
                'proximity': {'status': 'OK', 'distance': 100},
            }
        }
        
        try:
            # Send sensor data
            producer.produce(
                'taxistatus',
                json.dumps(sensor_data).encode('utf-8')
            )
            producer.flush()
            print("✅ Sensor data sent successfully")
            
            # Verify taxi status update
            time.sleep(2)  # Wait for processing
            response = self.session.get(f"{self.base_url}/taxis/test_taxi")
            
            if response.status_code == 200:
                print("✅ Taxi status updated in central")
                self.test_results['sensor_integration'] = True
            else:
                print("❌ Failed to verify taxi status update")
                self.test_results['sensor_integration'] = False
                
        except Exception as e:
            print(f"❌ Sensor integration test failed: {str(e)}")
            self.test_results['sensor_integration'] = False

    def run_all_tests(self):
        """Run all system tests"""
        print("\n=== Starting EasyCab System Tests ===\n")
        
        tests = [
            self.test_central_api,
            self.test_kafka_topics,
            self.test_taxi_workflow,
            self.test_taxi_sensor_integration
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(2)  # Pause between tests
            except Exception as e:
                print(f"❌ Test suite error: {str(e)}")
        
        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        print("\n=== Test Summary ===")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            print(f"{test_name}: {'✅' if result else '❌'}")

def main():
    tester = EasyCabTestSuite()
    tester.run_all_tests()

if __name__ == "__main__":
    main()