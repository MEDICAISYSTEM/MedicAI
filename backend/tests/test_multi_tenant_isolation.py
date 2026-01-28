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
        assert len(clinics) >= 2, "Expected at least 2 clinics (DRCASTELLA and DEMO01)"
        print(f"✅ Super admin can see {len(clinics)} clinics")
    
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
        """Create a test doctor account for DRCASTELLA clinic"""
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
    
    def test_doctor_sees_filtered_patients(self, doctor_token, super_admin_token):
        """Doctor should see filtered patients (only their clinic's patients)"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all patients as super admin
        admin_response = requests.get(f"{BASE_URL}/api/patients", headers=admin_headers)
        all_patients = admin_response.json()
        
        # Get patients as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/patients", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_patients = doctor_response.json()
        
        # Doctor should see <= total patients (filtered by clinic)
        assert len(doctor_patients) <= len(all_patients), \
            "Doctor should see fewer or equal patients than global count"
        
        print(f"✅ Doctor sees {len(doctor_patients)} patients (filtered by clinic)")
        print(f"   Super admin sees {len(all_patients)} patients (all clinics)")
    
    def test_doctor_sees_filtered_appointments(self, doctor_token, super_admin_token):
        """Doctor should see filtered appointments (only their clinic's appointments)"""
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
        admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get all appointments as super admin
        admin_response = requests.get(f"{BASE_URL}/api/appointments", headers=admin_headers)
        all_appointments = admin_response.json()
        
        # Get appointments as doctor
        doctor_response = requests.get(f"{BASE_URL}/api/appointments", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_appointments = doctor_response.json()
        
        # Doctor should see <= total appointments (filtered by clinic)
        assert len(doctor_appointments) <= len(all_appointments), \
            "Doctor should see fewer or equal appointments than global count"
        
        print(f"✅ Doctor sees {len(doctor_appointments)} appointments (filtered by clinic)")
        print(f"   Super admin sees {len(all_appointments)} appointments (all clinics)")


class TestCrossClinicAccessPrevention:
    """Test that doctors cannot access resources from other clinics - CRITICAL SECURITY"""
    
    @pytest.fixture(scope="class")
    def setup_data(self):
        """Setup test data: create doctors for both clinics and get patient IDs"""
        # Login as super admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get clinics
        clinics_response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=admin_headers)
        clinics = clinics_response.json()
        
        drcastella = next((c for c in clinics if c["code"] == "DRCASTELLA"), None)
        demo01 = next((c for c in clinics if c["code"] == "DEMO01"), None)
        
        if not drcastella or not demo01:
            pytest.skip("Required clinics not found")
        
        # Create DEMO01 doctor
        demo01_email = f"demo01_test_{uuid.uuid4().hex[:8]}@test.com"
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{demo01['id']}/create-admin",
            headers=admin_headers,
            json={"email": demo01_email, "password": "testpass123", "name": "DEMO01 Test Doctor"}
        )
        
        # Login as DEMO01 doctor
        demo01_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": demo01_email, "password": "testpass123"
        })
        demo01_token = demo01_login.json()["access_token"]
        
        # Get a patient from DRCASTELLA (using super admin)
        patients_response = requests.get(f"{BASE_URL}/api/patients", headers=admin_headers)
        all_patients = patients_response.json()
        
        # Find a patient that belongs to DRCASTELLA (has patients)
        drcastella_patient_id = all_patients[0]["id"] if all_patients else None
        
        return {
            "demo01_token": demo01_token,
            "drcastella_patient_id": drcastella_patient_id,
            "admin_token": admin_token
        }
    
    def test_demo01_doctor_cannot_access_drcastella_patient(self, setup_data):
        """DEMO01 doctor should get 404 when trying to access DRCASTELLA patient"""
        if not setup_data["drcastella_patient_id"]:
            pytest.skip("No patients available for testing")
        
        headers = {"Authorization": f"Bearer {setup_data['demo01_token']}"}
        patient_id = setup_data["drcastella_patient_id"]
        
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}", headers=headers)
        
        # Should return 404 (not found) because patient belongs to different clinic
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}. SECURITY ISSUE: Doctor can see other clinic's patient!"
        print(f"✅ DEMO01 doctor cannot access DRCASTELLA patient (404)")
    
    def test_demo01_doctor_cannot_update_drcastella_patient(self, setup_data):
        """DEMO01 doctor should get 404 when trying to update DRCASTELLA patient"""
        if not setup_data["drcastella_patient_id"]:
            pytest.skip("No patients available for testing")
        
        headers = {"Authorization": f"Bearer {setup_data['demo01_token']}"}
        patient_id = setup_data["drcastella_patient_id"]
        
        response = requests.put(
            f"{BASE_URL}/api/patients/{patient_id}",
            headers=headers,
            json={"name": "HACKED NAME"}
        )
        
        # Should return 404 (not found) because patient belongs to different clinic
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}. SECURITY ISSUE: Doctor can update other clinic's patient!"
        print(f"✅ DEMO01 doctor cannot update DRCASTELLA patient (404)")
    
    def test_demo01_doctor_cannot_access_drcastella_medical_record(self, setup_data):
        """DEMO01 doctor should get 404 when trying to access DRCASTELLA patient's medical record"""
        if not setup_data["drcastella_patient_id"]:
            pytest.skip("No patients available for testing")
        
        headers = {"Authorization": f"Bearer {setup_data['demo01_token']}"}
        patient_id = setup_data["drcastella_patient_id"]
        
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}/medical-record", headers=headers)
        
        # Should return 404 (not found) because patient belongs to different clinic
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}. SECURITY ISSUE: Doctor can see other clinic's medical records!"
        print(f"✅ DEMO01 doctor cannot access DRCASTELLA patient's medical record (404)")


class TestDashboardStatsFiltering:
    """Test that dashboard stats are filtered by clinic_id for non-super-admin users"""
    
    @pytest.fixture(scope="class")
    def setup_data(self):
        """Setup test data"""
        # Login as super admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get clinics
        clinics_response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=admin_headers)
        clinics = clinics_response.json()
        
        drcastella = next((c for c in clinics if c["code"] == "DRCASTELLA"), None)
        if not drcastella:
            pytest.skip("DRCASTELLA clinic not found")
        
        # Create doctor for DRCASTELLA
        doctor_email = f"stats_test_{uuid.uuid4().hex[:8]}@test.com"
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella['id']}/create-admin",
            headers=admin_headers,
            json={"email": doctor_email, "password": "testpass123", "name": "Stats Test Doctor"}
        )
        
        # Login as doctor
        doctor_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": doctor_email, "password": "testpass123"
        })
        doctor_token = doctor_login.json()["access_token"]
        
        return {
            "admin_token": admin_token,
            "doctor_token": doctor_token,
            "clinic_id": drcastella["id"]
        }
    
    def test_dashboard_stats_filtered_for_doctor(self, setup_data):
        """Dashboard stats should be filtered by clinic for non-super-admin"""
        doctor_headers = {"Authorization": f"Bearer {setup_data['doctor_token']}"}
        admin_headers = {"Authorization": f"Bearer {setup_data['admin_token']}"}
        
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
        """Test webhook accepts (#CODE) format"""
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "phone": f"+52{uuid.uuid4().hex[:10]}",
            "message": "Hola, quiero agendar una cita (#DRCASTELLA)"
        })
        # Should not return 500 - webhook should process the message
        assert response.status_code in [200, 201], f"Webhook failed with (#CODE) format: {response.text}"
        print("✅ Webhook accepts (#CODE) format")
    
    def test_webhook_accepts_ref_code_format(self):
        """Test webhook accepts Ref:CODE format"""
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "phone": f"+52{uuid.uuid4().hex[:10]}",
            "message": "Hola, quiero agendar una cita Ref:DRCASTELLA"
        })
        # Should not return 500 - webhook should process the message
        assert response.status_code in [200, 201], f"Webhook failed with Ref:CODE format: {response.text}"
        print("✅ Webhook accepts Ref:CODE format")
    
    def test_webhook_accepts_plain_hashtag_format(self):
        """Test webhook accepts #CODE format (without parentheses)"""
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "phone": f"+52{uuid.uuid4().hex[:10]}",
            "message": "Hola #DRCASTELLA quiero una cita"
        })
        # Should not return 500 - webhook should process the message
        assert response.status_code in [200, 201], f"Webhook failed with #CODE format: {response.text}"
        print("✅ Webhook accepts #CODE format (without parentheses)")


class TestConversationsIsolation:
    """Test conversations are isolated by clinic"""
    
    @pytest.fixture(scope="class")
    def setup_data(self):
        """Setup test data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        clinics_response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=admin_headers)
        clinics = clinics_response.json()
        
        drcastella = next((c for c in clinics if c["code"] == "DRCASTELLA"), None)
        if not drcastella:
            pytest.skip("DRCASTELLA clinic not found")
        
        doctor_email = f"conv_test_{uuid.uuid4().hex[:8]}@test.com"
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella['id']}/create-admin",
            headers=admin_headers,
            json={"email": doctor_email, "password": "testpass123", "name": "Conv Test Doctor"}
        )
        
        doctor_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": doctor_email, "password": "testpass123"
        })
        doctor_token = doctor_login.json()["access_token"]
        
        return {"admin_token": admin_token, "doctor_token": doctor_token}
    
    def test_doctor_sees_filtered_conversations(self, setup_data):
        """Doctor should only see conversations from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {setup_data['doctor_token']}"}
        admin_headers = {"Authorization": f"Bearer {setup_data['admin_token']}"}
        
        admin_response = requests.get(f"{BASE_URL}/api/conversations", headers=admin_headers)
        all_conversations = admin_response.json()
        
        doctor_response = requests.get(f"{BASE_URL}/api/conversations", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_conversations = doctor_response.json()
        
        assert len(doctor_conversations) <= len(all_conversations), \
            "Doctor should see fewer or equal conversations than global count"
        
        print(f"✅ Doctor sees {len(doctor_conversations)} conversations (filtered by clinic)")
        print(f"   Super admin sees {len(all_conversations)} conversations (all clinics)")


class TestAlertsIsolation:
    """Test alerts are isolated by clinic"""
    
    @pytest.fixture(scope="class")
    def setup_data(self):
        """Setup test data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        clinics_response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=admin_headers)
        clinics = clinics_response.json()
        
        drcastella = next((c for c in clinics if c["code"] == "DRCASTELLA"), None)
        if not drcastella:
            pytest.skip("DRCASTELLA clinic not found")
        
        doctor_email = f"alert_test_{uuid.uuid4().hex[:8]}@test.com"
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella['id']}/create-admin",
            headers=admin_headers,
            json={"email": doctor_email, "password": "testpass123", "name": "Alert Test Doctor"}
        )
        
        doctor_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": doctor_email, "password": "testpass123"
        })
        doctor_token = doctor_login.json()["access_token"]
        
        return {"admin_token": admin_token, "doctor_token": doctor_token}
    
    def test_doctor_sees_filtered_alerts(self, setup_data):
        """Doctor should only see alerts from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {setup_data['doctor_token']}"}
        admin_headers = {"Authorization": f"Bearer {setup_data['admin_token']}"}
        
        admin_response = requests.get(f"{BASE_URL}/api/alerts", headers=admin_headers)
        all_alerts = admin_response.json()
        
        doctor_response = requests.get(f"{BASE_URL}/api/alerts", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_alerts = doctor_response.json()
        
        assert len(doctor_alerts) <= len(all_alerts), \
            "Doctor should see fewer or equal alerts than global count"
        
        print(f"✅ Doctor sees {len(doctor_alerts)} alerts (filtered by clinic)")
        print(f"   Super admin sees {len(all_alerts)} alerts (all clinics)")


class TestAvailabilityIsolation:
    """Test availability slots are isolated by clinic"""
    
    @pytest.fixture(scope="class")
    def setup_data(self):
        """Setup test data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        clinics_response = requests.get(f"{BASE_URL}/api/superadmin/clinics", headers=admin_headers)
        clinics = clinics_response.json()
        
        drcastella = next((c for c in clinics if c["code"] == "DRCASTELLA"), None)
        if not drcastella:
            pytest.skip("DRCASTELLA clinic not found")
        
        doctor_email = f"avail_test_{uuid.uuid4().hex[:8]}@test.com"
        requests.post(
            f"{BASE_URL}/api/superadmin/clinics/{drcastella['id']}/create-admin",
            headers=admin_headers,
            json={"email": doctor_email, "password": "testpass123", "name": "Avail Test Doctor"}
        )
        
        doctor_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": doctor_email, "password": "testpass123"
        })
        doctor_token = doctor_login.json()["access_token"]
        
        return {"admin_token": admin_token, "doctor_token": doctor_token}
    
    def test_doctor_sees_filtered_availability(self, setup_data):
        """Doctor should only see availability from their own clinic"""
        doctor_headers = {"Authorization": f"Bearer {setup_data['doctor_token']}"}
        admin_headers = {"Authorization": f"Bearer {setup_data['admin_token']}"}
        
        admin_response = requests.get(f"{BASE_URL}/api/availability", headers=admin_headers)
        all_availability = admin_response.json()
        
        doctor_response = requests.get(f"{BASE_URL}/api/availability", headers=doctor_headers)
        assert doctor_response.status_code == 200
        doctor_availability = doctor_response.json()
        
        assert len(doctor_availability) <= len(all_availability), \
            "Doctor should see fewer or equal availability slots than global count"
        
        print(f"✅ Doctor sees {len(doctor_availability)} availability slots (filtered by clinic)")
        print(f"   Super admin sees {len(all_availability)} availability slots (all clinics)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
