#!/usr/bin/env python3
"""
MedicAI Backend API Testing Suite
Tests all backend endpoints for functionality and integration
"""

import requests
import sys
import json
from datetime import datetime, timedelta
import uuid

class MedicAITester:
    def __init__(self, base_url="https://clinicchat.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.admin_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", expected_status=None, actual_status=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            if expected_status and actual_status:
                print(f"   Expected: {expected_status}, Got: {actual_status}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.log_test(name, True)
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                self.log_test(name, False, f"Status code mismatch", expected_status, response.status_code)
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text[:200]}")
                return False, {}

        except requests.exceptions.RequestException as e:
            self.log_test(name, False, f"Request failed: {str(e)}")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Unexpected error: {str(e)}")
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        self.run_test("Root Endpoint", "GET", "", 200)
        
        # Test health check
        self.run_test("Health Check", "GET", "health", 200)

    def test_auth_flow(self):
        """Test authentication flow"""
        print("\n🔍 Testing Authentication Flow...")
        
        # Generate unique test admin
        timestamp = datetime.now().strftime('%H%M%S')
        test_email = f"test_admin_{timestamp}@medicai.com"
        test_password = "TestPass123!"
        test_name = f"Test Admin {timestamp}"
        
        # Test registration
        register_data = {
            "email": test_email,
            "password": test_password,
            "name": test_name
        }
        
        success, response = self.run_test("Admin Registration", "POST", "auth/register", 200, register_data)
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.admin_id = response['admin']['id']
            print(f"   Registered admin: {test_email}")
        else:
            print("❌ Registration failed, cannot continue with auth tests")
            return False
        
        # Test login with same credentials
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, login_data)
        
        if success and 'access_token' in response:
            self.token = response['access_token']  # Update token
            print(f"   Login successful for: {test_email}")
        
        # Test get current user
        self.run_test("Get Current Admin", "GET", "auth/me", 200)
        
        # Test invalid login
        invalid_login = {
            "email": "invalid@test.com",
            "password": "wrongpass"
        }
        self.run_test("Invalid Login", "POST", "auth/login", 401, invalid_login)
        
        return True

    def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        print("\n🔍 Testing Dashboard Endpoints...")
        
        if not self.token:
            print("❌ No auth token, skipping dashboard tests")
            return
        
        # Test dashboard stats
        self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    def test_patients_endpoints(self):
        """Test patients endpoints"""
        print("\n🔍 Testing Patients Endpoints...")
        
        if not self.token:
            print("❌ No auth token, skipping patients tests")
            return
        
        # Test get all patients
        self.run_test("Get All Patients", "GET", "patients", 200)
        
        # Test get specific patient (should return 404 for non-existent)
        fake_id = str(uuid.uuid4())
        self.run_test("Get Non-existent Patient", "GET", f"patients/{fake_id}", 404)

    def test_appointments_endpoints(self):
        """Test appointments endpoints"""
        print("\n🔍 Testing Appointments Endpoints...")
        
        if not self.token:
            print("❌ No auth token, skipping appointments tests")
            return
        
        # Test get all appointments
        self.run_test("Get All Appointments", "GET", "appointments", 200)
        
        # Test get appointments with date filter
        today = datetime.now().strftime('%Y-%m-%d')
        self.run_test("Get Appointments by Date", "GET", f"appointments?date={today}", 200)
        
        # Test get appointments with status filter
        self.run_test("Get Appointments by Status", "GET", "appointments?status=confirmed", 200)

    def test_availability_endpoints(self):
        """Test availability endpoints"""
        print("\n🔍 Testing Availability Endpoints...")
        
        if not self.token:
            print("❌ No auth token, skipping availability tests")
            return
        
        # Test get availability
        self.run_test("Get Availability", "GET", "availability", 200)
        
        # Test create availability slot
        slot_data = {
            "day_of_week": 1,  # Monday
            "start_time": "10:00",
            "end_time": "11:00",
            "is_available": True
        }
        
        success, response = self.run_test("Create Availability Slot", "POST", "availability", 200, slot_data)
        
        if success and 'id' in response:
            slot_id = response['id']
            
            # Test update availability slot
            update_data = {
                "day_of_week": 1,
                "start_time": "10:30",
                "end_time": "11:30",
                "is_available": True
            }
            self.run_test("Update Availability Slot", "PUT", f"availability/{slot_id}", 200, update_data)
            
            # Test delete availability slot
            self.run_test("Delete Availability Slot", "DELETE", f"availability/{slot_id}", 200)

    def test_conversations_endpoints(self):
        """Test conversations endpoints"""
        print("\n🔍 Testing Conversations Endpoints...")
        
        if not self.token:
            print("❌ No auth token, skipping conversations tests")
            return
        
        # Test get all conversations
        self.run_test("Get All Conversations", "GET", "conversations", 200)
        
        # Test get specific conversation (should return 404 for non-existent)
        fake_id = str(uuid.uuid4())
        self.run_test("Get Non-existent Conversation", "GET", f"conversations/{fake_id}", 404)

    def test_alerts_endpoints(self):
        """Test alerts endpoints"""
        print("\n🔍 Testing Alerts Endpoints...")
        
        if not self.token:
            print("❌ No auth token, skipping alerts tests")
            return
        
        # Test get all alerts
        self.run_test("Get All Alerts", "GET", "alerts", 200)
        
        # Test get alerts with status filter
        self.run_test("Get Pending Alerts", "GET", "alerts?status=pending", 200)

    def test_webhook_endpoint(self):
        """Test webhook endpoint (no auth required)"""
        print("\n🔍 Testing Webhook Endpoint...")
        
        # Test WhatsApp webhook (should accept POST without auth)
        webhook_data = {
            "phone": "+1234567890",
            "message": "Hola, necesito una cita",
            "timestamp": datetime.now().isoformat()
        }
        
        # Note: This might fail if Supabase tables don't exist, but we test the endpoint
        success, response = self.run_test("WhatsApp Webhook", "POST", "webhook/whatsapp", 200, webhook_data)
        
        if not success:
            # Try without auth token to see if it's an auth issue
            temp_token = self.token
            self.token = None
            self.run_test("WhatsApp Webhook (No Auth)", "POST", "webhook/whatsapp", 200, webhook_data)
            self.token = temp_token

    def test_protected_routes(self):
        """Test that protected routes require authentication"""
        print("\n🔍 Testing Protected Routes...")
        
        # Temporarily remove token
        temp_token = self.token
        self.token = None
        
        # Test that protected endpoints return 401 without token
        protected_endpoints = [
            ("dashboard/stats", "GET"),
            ("patients", "GET"),
            ("appointments", "GET"),
            ("availability", "GET"),
            ("conversations", "GET"),
            ("alerts", "GET"),
            ("auth/me", "GET")
        ]
        
        for endpoint, method in protected_endpoints:
            self.run_test(f"Protected Route: {endpoint}", method, endpoint, 401)
        
        # Restore token
        self.token = temp_token

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting MedicAI Backend API Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run test suites
        self.test_health_endpoints()
        
        auth_success = self.test_auth_flow()
        if auth_success:
            self.test_dashboard_endpoints()
            self.test_patients_endpoints()
            self.test_appointments_endpoints()
            self.test_availability_endpoints()
            self.test_conversations_endpoints()
            self.test_alerts_endpoints()
        
        self.test_webhook_endpoint()
        self.test_protected_routes()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Return success if most tests passed
        success_rate = (self.tests_passed / self.tests_run) * 100
        return success_rate >= 70  # 70% success rate threshold

def main():
    """Main test runner"""
    tester = MedicAITester()
    
    try:
        success = tester.run_all_tests()
        
        # Save detailed results
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "failed_tests": tester.tests_run - tester.tests_passed,
            "success_rate": (tester.tests_passed / tester.tests_run) * 100,
            "test_details": tester.test_results
        }
        
        with open('/app/backend_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())