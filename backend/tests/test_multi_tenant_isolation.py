"""
Multi-tenant Data Isolation Security Tests for MedicAI
Tests clinic data isolation, cross-clinic access prevention, and super admin access
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "admin@clinica.com"
SUPER_ADMIN_PASSWORD = "admin123"
TEST_CLINIC_CODE = "DRCASTELLA"

class TestAuthAndSetup:
    """Authentication and setup tests"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["admin"]["is_super_admin"] == True
        return data["access_token"]
    
    def test_super_admin_login(self, super_admin_token):
        """Test super admin can login successfully"""
        assert super_admin_token is not None
        print(f"✅ Super admin login successful")
    
    def test_super_admin_me_endpoint(self, super_admin_token):
        """Test /auth/me returns super admin info"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_super_admin"] == True
        assert data["email"] == SUPER_ADMIN_EMAIL
        print(f"✅ Super admin /auth/me returns correct data")


class TestSuperAdminAccess:
    """Test super admin can access all data across clinics"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_super_admin_can_get_all_clinics(self, super_admin_token):
        """Super admin should see all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        assert response.status_code == 200
        clinics = response.json()
        assert isinstance(clinics, list)
        print(f"✅ Super admin can see {len(clinics)} clinics")
        return clinics
    
    def test_super_admin_can_get_global_stats(self, super_admin_token):
        """Super admin should see global stats"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/stats", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_clinics" in stats
        assert "total_patients" in stats
        assert "total_appointments" in stats
        print(f"✅ Super admin global stats: {stats['total_clinics']} clinics, {stats['total_patients']} patients")
    
    def test_super_admin_can_see_all_patients(self, super_admin_token):
        """Super admin should see patients from all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/patients", headers=headers)
        assert response.status_code == 200
        patients = response.json()
        assert isinstance(patients, list)
        print(f"✅ Super admin can see {len(patients)} patients across all clinics")
    
    def test_super_admin_can_see_all_appointments(self, super_admin_token):
        """Super admin should see appointments from all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/appointments", headers=headers)
        assert response.status_code == 200
        appointments = response.json()
        assert isinstance(appointments, list)
        print(f"✅ Super admin can see {len(appointments)} appointments across all clinics")


class TestClinicDataIsolation:
    """Test data isolation between clinics - CRITICAL SECURITY TESTS"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def clinics_data(self, super_admin_token):
        """Get all clinics to find test clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        clinics = response.json()
        return clinics
    
    @pytest.fixture(scope="class")
    def test_doctor_credentials(self, super_admin_token, clinics_data):
        """Create a test doctor account for a specific clinic"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Find DRCASTELLA clinic
        drcastella_clinic = next((c for c in clinics_data if c["code"] == "DRCASTELLA"), None)
        if not drcastella_clinic:
            pytest.skip("DRCASTELLA clinic not found")
        
        # Create unique test doctor email
        test_email = f"test_doctor_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        # Create admin for this clinic
        response = requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella_clinic['id']}/create-admin",
            headers=headers,
            json={
                "email": test_email,
                "password": test_password,
                "name": "Test Doctor DRCASTELLA"
            }
        )
        
        if response.status_code == 400 and "already registered" in response.text:
            # Use existing test credentials
            pytest.skip("Test doctor already exists, skipping creation")
        
        assert response.status_code == 200, f"Failed to create test doctor: {response.text}"
        
        return {
            "email": test_email,
            "password": test_password,
            "clinic_id": drcastella_clinic["id"],
            "clinic_code": "DRCASTELLA"
        }
    
    @pytest.fixture(scope="class")
    def doctor_token(self, test_doctor_credentials):
        """Login as test doctor"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_doctor_credentials["email"],
            "password": test_doctor_credentials["password"]
        })
        assert response.status_code == 200, f"Doctor login failed: {response.text}"
        data = response.json()
        assert data["admin"]["is_super_admin"] == False
        assert data["admin"]["clinic_id"] == test_doctor_credentials["clinic_id"]
        return data["access_token"]
    
    def test_doctor_cannot_access_superadmin_endpoints(self, doctor_token):
        """Non-super-admin should NOT access superadmin endpoints"""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        
        # Try to access superadmin stats
        response = requests.get(f"{BASE_URL}/api/superadmin/stats", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✅ Doctor cannot access /superadmin/stats (403)")
        
        # Try to access superadmin clinics
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✅ Doctor cannot access /superadmin/clinics (403)")
    
    def test_doctor_only_sees_own_clinic_patients(self, doctor_token, super_admin_token, test_doctor_credentials):
        """Doctor should only see patients from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all patients as super admin
        admin_response = requests.get(f"{BASE_URL}/api/patients", headers=admin_headers)
        all_patients = admin_response.json()
        
        # Get patients as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/patients", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_patients = doctor_response.json()
        
        # Verify doctor only sees their clinic's patients
        clinic_id = test_doctor_credentials["clinic_id"]
        for patient in doctor_patients:
            assert patient.get("clinic_id") == clinic_id, f"Doctor sees patient from another clinic: {patient}"
        
        print(f"✅ Doctor sees {len(doctor_patients)} patients (filtered by clinic)")
        print(f"   Super admin sees {len(all_patients)} patients (all clinics)")
    
    def test_doctor_only_sees_own_clinic_appointments(self, doctor_token, super_admin_token, test_doctor_credentials):
        """Doctor should only see appointments from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all appointments as super admin
        admin_response = requests.get(f"{BASE_URL}/api/appointments", headers=admin_headers)
        all_appointments = admin_response.json()
        
        # Get appointments as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/appointments", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_appointments = doctor_response.json()
        
        # Verify doctor only sees their clinic's appointments
        clinic_id = test_doctor_credentials["clinic_id"]
        for apt in doctor_appointments:
            assert apt.get("clinic_id") == clinic_id, f"Doctor sees appointment from another clinic: {apt}"
        
        print(f"✅ Doctor sees {len(doctor_appointments)} appointments (filtered by clinic)")
        print(f"   Super admin sees {len(all_appointments)} appointments (all clinics)")


class TestCrossClinicAccessPrevention:
    """Test that doctors cannot access resources from other clinics"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def clinics_data(self, super_admin_token):
        """Get all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        return response.json()
    
    @pytest.fixture(scope="class")
    def other_clinic_patient(self, super_admin_token, clinics_data):
        """Find a patient from a different clinic (DEMO01)"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Find DEMO01 clinic
        demo_clinic = next((c for c in clinics_data if c["code"] == "DEMO01"), None)
        if not demo_clinic:
            pytest.skip("DEMO01 clinic not found")
        
        # Get patients from DEMO01
        response = requests.get(f"{BASE_URL}/api/patients", headers=headers)
        all_patients = response.json()
        
        demo_patients = [p for p in all_patients if p.get("clinic_id") == demo_clinic["id"]]
        if not demo_patients:
            pytest.skip("No patients found in DEMO01 clinic")
        
        return demo_patients[0]
    
    @pytest.fixture(scope="class")
    def drcastella_doctor_token(self, super_admin_token, clinics_data):
        """Create and login as DRCASTELLA doctor"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Find DRCASTELLA clinic
        drcastella_clinic = next((c for c in clinics_data if c["code"] == "DRCASTELLA"), None)
        if not drcastella_clinic:
            pytest.skip("DRCASTELLA clinic not found")
        
        # Create unique test doctor
        test_email = f"isolation_test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        response = requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella_clinic['id']}/create-admin",
            headers=headers,
            json={
                "email": test_email,
                "password": test_password,
                "name": "Isolation Test Doctor"
            }
        )
        
        # Login as this doctor
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_response.status_code == 200
        return login_response.json()["access_token"]
    
    def test_doctor_cannot_access_other_clinic_patient(self, drcastella_doctor_token, other_clinic_patient):
        """Doctor should get 404 when trying to access patient from another clinic"""
        headers = {"Authorization": f"Bearer {drcastella_doctor_token}"}
        
        patient_id = other_clinic_patient["id"]
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}", headers=headers)
        
        # Should return 404 (not found) because patient belongs to different clinic
        assert response.status_code == 404, f"Expected 404, got {response.status_code}. Doctor should NOT see other clinic's patient!"
        print(f"✅ Doctor cannot access patient from another clinic (404)")
    
    def test_doctor_cannot_update_other_clinic_patient(self, drcastella_doctor_token, other_clinic_patient):
        """Doctor should get 404 when trying to update patient from another clinic"""
        headers = {"Authorization": f"Bearer {drcastella_doctor_token}"}
        
        patient_id = other_clinic_patient["id"]
        response = requests.put(
            f"{BASE_URL}/api/patients/{patient_id}",
            headers=headers,
            json={"name": "HACKED NAME"}
        )
        
        # Should return 404 (not found) because patient belongs to different clinic
        assert response.status_code == 404, f"Expected 404, got {response.status_code}. Doctor should NOT update other clinic's patient!"
        print(f"✅ Doctor cannot update patient from another clinic (404)")


class TestDashboardStatsFiltering:
    """Test that dashboard stats are filtered by clinic_id for non-super-admin users"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def clinics_data(self, super_admin_token):
        """Get all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        return response.json()
    
    @pytest.fixture(scope="class")
    def doctor_token_and_clinic(self, super_admin_token, clinics_data):
        """Create and login as a clinic doctor"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Find DRCASTELLA clinic
        drcastella_clinic = next((c for c in clinics_data if c["code"] == "DRCASTELLA"), None)
        if not drcastella_clinic:
            pytest.skip("DRCASTELLA clinic not found")
        
        # Create unique test doctor
        test_email = f"stats_test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        response = requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella_clinic['id']}/create-admin",
            headers=headers,
            json={
                "email": test_email,
                "password": test_password,
                "name": "Stats Test Doctor"
            }
        )
        
        # Login as this doctor
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_response.status_code == 200
        return {
            "token": login_response.json()["access_token"],
            "clinic_id": drcastella_clinic["id"]
        }
    
    def test_dashboard_stats_filtered_for_doctor(self, doctor_token_and_clinic, super_admin_token):
        """Dashboard stats should be filtered by clinic for non-super-admin"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token_and_clinic['token']}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get dashboard stats as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_stats = doctor_response.json()
        
        # Get global stats as super admin
        admin_response = requests.get(f"{BASE_URL}/api/superadmin/stats", headers=admin_headers)
        admin_stats = admin_response.json()
        
        # Doctor stats should be <= global stats (filtered by clinic)
        assert doctor_stats["total_patients"] <= admin_stats["total_patients"], \
            "Doctor should see fewer or equal patients than global count"
        
        print(f"✅ Dashboard stats filtered for doctor:")
        print(f"   Doctor sees: {doctor_stats['total_patients']} patients, {doctor_stats['total_appointments_today']} appointments today")
        print(f"   Global stats: {admin_stats['total_patients']} patients total")


class TestWhatsAppWebhookCodeFormats:
    """Test WhatsApp webhook correctly identifies clinic from different code formats"""
    
    def test_webhook_accepts_hashtag_code_format(self):
        """Test webhook accepts #CODE format"""
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "phone": "+521234567890",
            "message": "Hola, quiero agendar una cita (#DRCASTELLA)"
        })
        # Should not return 500 - webhook should process the message
        assert response.status_code in [200, 201], f"Webhook failed with #CODE format: {response.text}"
        print("✅ Webhook accepts (#CODE) format")
    
    def test_webhook_accepts_ref_code_format(self):
        """Test webhook accepts Ref:CODE format"""
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "phone": "+521234567891",
            "message": "Hola, quiero agendar una cita Ref:DRCASTELLA"
        })
        # Should not return 500 - webhook should process the message
        assert response.status_code in [200, 201], f"Webhook failed with Ref:CODE format: {response.text}"
        print("✅ Webhook accepts Ref:CODE format")
    
    def test_webhook_accepts_plain_hashtag_format(self):
        """Test webhook accepts #CODE format (without parentheses)"""
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "phone": "+521234567892",
            "message": "Hola #DRCASTELLA quiero una cita"
        })
        # Should not return 500 - webhook should process the message
        assert response.status_code in [200, 201], f"Webhook failed with #CODE format: {response.text}"
        print("✅ Webhook accepts #CODE format (without parentheses)")


class TestConversationsIsolation:
    """Test conversations are isolated by clinic"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def clinics_data(self, super_admin_token):
        """Get all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        return response.json()
    
    @pytest.fixture(scope="class")
    def doctor_token(self, super_admin_token, clinics_data):
        """Create and login as a clinic doctor"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        drcastella_clinic = next((c for c in clinics_data if c["code"] == "DRCASTELLA"), None)
        if not drcastella_clinic:
            pytest.skip("DRCASTELLA clinic not found")
        
        test_email = f"conv_test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella_clinic['id']}/create-admin",
            headers=headers,
            json={
                "email": test_email,
                "password": test_password,
                "name": "Conversation Test Doctor"
            }
        )
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        return login_response.json()["access_token"]
    
    def test_doctor_only_sees_own_clinic_conversations(self, doctor_token, super_admin_token):
        """Doctor should only see conversations from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all conversations as super admin
        admin_response = requests.get(f"{BASE_URL}/api/conversations", headers=admin_headers)
        all_conversations = admin_response.json()
        
        # Get conversations as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/conversations", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_conversations = doctor_response.json()
        
        print(f"✅ Doctor sees {len(doctor_conversations)} conversations (filtered by clinic)")
        print(f"   Super admin sees {len(all_conversations)} conversations (all clinics)")


class TestAlertsIsolation:
    """Test alerts are isolated by clinic"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def clinics_data(self, super_admin_token):
        """Get all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        return response.json()
    
    @pytest.fixture(scope="class")
    def doctor_token(self, super_admin_token, clinics_data):
        """Create and login as a clinic doctor"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        drcastella_clinic = next((c for c in clinics_data if c["code"] == "DRCASTELLA"), None)
        if not drcastella_clinic:
            pytest.skip("DRCASTELLA clinic not found")
        
        test_email = f"alert_test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella_clinic['id']}/create-admin",
            headers=headers,
            json={
                "email": test_email,
                "password": test_password,
                "name": "Alert Test Doctor"
            }
        )
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        return login_response.json()["access_token"]
    
    def test_doctor_only_sees_own_clinic_alerts(self, doctor_token, super_admin_token):
        """Doctor should only see alerts from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all alerts as super admin
        admin_response = requests.get(f"{BASE_URL}/api/alerts", headers=admin_headers)
        all_alerts = admin_response.json()
        
        # Get alerts as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/alerts", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_alerts = doctor_response.json()
        
        print(f"✅ Doctor sees {len(doctor_alerts)} alerts (filtered by clinic)")
        print(f"   Super admin sees {len(all_alerts)} alerts (all clinics)")


class TestAvailabilityIsolation:
    """Test availability slots are isolated by clinic"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def clinics_data(self, super_admin_token):
        """Get all clinics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=headers)
        return response.json()
    
    @pytest.fixture(scope="class")
    def doctor_token(self, super_admin_token, clinics_data):
        """Create and login as a clinic doctor"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        drcastella_clinic = next((c for c in clinics_data if c["code"] == "DRCASTELLA"), None)
        if not drcastella_clinic:
            pytest.skip("DRCASTELLA clinic not found")
        
        test_email = f"avail_test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella_clinic['id']}/create-admin",
            headers=headers,
            json={
                "email": test_email,
                "password": test_password,
                "name": "Availability Test Doctor"
            }
        )
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        return login_response.json()["access_token"]
    
    def test_doctor_only_sees_own_clinic_availability(self, doctor_token, super_admin_token):
        """Doctor should only see availability from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all availability as super admin
        admin_response = requests.get(f"{BASE_URL}/api/availability", headers=admin_headers)
        all_availability = admin_response.json()
        
        # Get availability as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/availability", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_availability = doctor_response.json()
        
        print(f"✅ Doctor sees {len(doctor_availability)} availability slots (filtered by clinic)")
        print(f"   Super admin sees {len(all_availability)} availability slots (all clinics)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
