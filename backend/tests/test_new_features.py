"""
Tests for MedicAI new features - Iteration 4
- DELETE /api/patients/{id} endpoint with cascade delete
- Appointments with colored status badges (backend status verification)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://medicai-preview.preview.emergentagent.com')

# Test credentials
DOCTOR_EMAIL = "isma200034@outlook.com"
DOCTOR_PASSWORD = "123456"
SUPER_ADMIN_EMAIL = "admin@clinica.com"
SUPER_ADMIN_PASSWORD = "admin123"


class TestDeletePatientEndpoint:
    """Tests for DELETE /api/patients/{patient_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get doctor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Doctor auth failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Super admin auth failed: {response.status_code} - {response.text}")
    
    def test_delete_patient_requires_auth(self):
        """Test that DELETE /api/patients/{id} requires authentication"""
        response = requests.delete(f"{BASE_URL}/api/patients/some-fake-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ DELETE patient requires authentication")
    
    def test_delete_nonexistent_patient_returns_404(self, auth_token):
        """Test deleting a non-existent patient returns 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.delete(
            f"{BASE_URL}/api/patients/nonexistent-patient-id-12345",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ DELETE non-existent patient returns 404")
    
    def test_get_patients_list_for_delete_test(self, auth_token):
        """Verify patients exist for potential delete testing"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/patients", headers=headers)
        
        assert response.status_code == 200, f"Failed to get patients: {response.status_code}"
        patients = response.json()
        print(f"✓ Found {len(patients)} patients in the system")
        assert len(patients) > 0, "No patients found - cannot test delete"


class TestAppointmentStatusEndpoints:
    """Tests for appointment status - verify status field exists and is correct"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get doctor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Doctor auth failed: {response.status_code}")
    
    def test_appointments_have_status_field(self, auth_token):
        """Test that appointments include status field for colored badges"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/appointments", headers=headers)
        
        assert response.status_code == 200, f"Failed to get appointments: {response.status_code}"
        appointments = response.json()
        
        if len(appointments) > 0:
            first_apt = appointments[0]
            assert "status" in first_apt, "Appointment missing 'status' field"
            # Valid statuses for colored badges
            valid_statuses = ["pending", "confirmed", "cancelled", "completed", "no_show"]
            assert first_apt["status"] in valid_statuses, f"Invalid status: {first_apt['status']}"
            print(f"✓ Appointments have status field. First appointment status: {first_apt['status']}")
        else:
            print("✓ No appointments to verify status (endpoint works)")
    
    def test_appointments_filter_by_date(self, auth_token):
        """Test filtering appointments by date for dashboard date picker"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/appointments",
            headers=headers,
            params={"date": today}
        )
        
        assert response.status_code == 200, f"Failed to filter by date: {response.status_code}"
        appointments = response.json()
        
        # Verify all returned appointments are for today
        for apt in appointments:
            assert apt["date"] == today, f"Appointment date {apt['date']} != {today}"
        
        print(f"✓ Date filter works - {len(appointments)} appointments for {today}")


class TestAvailabilityEndpoints:
    """Tests for availability slot endpoints - for day preselection feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get doctor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Doctor auth failed: {response.status_code}")
    
    def test_get_availability_slots(self, auth_token):
        """Test getting availability slots"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/availability", headers=headers)
        
        assert response.status_code == 200, f"Failed to get availability: {response.status_code}"
        slots = response.json()
        
        if len(slots) > 0:
            first_slot = slots[0]
            assert "day_of_week" in first_slot, "Missing day_of_week field"
            assert "start_time" in first_slot, "Missing start_time field"
            assert "end_time" in first_slot, "Missing end_time field"
            assert "is_available" in first_slot, "Missing is_available field"
            print(f"✓ Availability slots found: {len(slots)} slots")
        else:
            print("✓ No availability slots configured (endpoint works)")
    
    def test_create_and_delete_availability_slot(self, auth_token):
        """Test creating and deleting availability slot with specific day"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create a test slot for Wednesday (day 3)
        test_slot = {
            "day_of_week": 3,
            "start_time": "10:00",
            "end_time": "11:00",
            "is_available": True
        }
        
        # Create
        create_response = requests.post(
            f"{BASE_URL}/api/availability",
            headers=headers,
            json=test_slot
        )
        
        assert create_response.status_code == 200, f"Failed to create slot: {create_response.status_code}"
        created_slot = create_response.json()
        assert created_slot["day_of_week"] == 3, "day_of_week not preserved"
        print(f"✓ Created availability slot for day 3 (Wednesday)")
        
        # Delete the test slot
        slot_id = created_slot["id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/availability/{slot_id}",
            headers=headers
        )
        
        assert delete_response.status_code == 200, f"Failed to delete slot: {delete_response.status_code}"
        print(f"✓ Deleted test availability slot {slot_id}")


class TestDashboardStats:
    """Tests for dashboard stats endpoint - verify stats for date picker view"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get doctor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DOCTOR_EMAIL,
            "password": DOCTOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Doctor auth failed: {response.status_code}")
    
    def test_dashboard_stats_endpoint(self, auth_token):
        """Test dashboard stats returns all required fields"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200, f"Failed to get stats: {response.status_code}"
        stats = response.json()
        
        required_fields = [
            "total_patients",
            "total_appointments_today",
            "total_appointments_week",
            "pending_alerts",
            "confirmed_appointments",
            "cancelled_appointments"
        ]
        
        for field in required_fields:
            assert field in stats, f"Missing field: {field}"
        
        print(f"✓ Dashboard stats complete: {stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
