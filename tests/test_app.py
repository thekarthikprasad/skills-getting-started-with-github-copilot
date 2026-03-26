import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned with correct structure"""
        # Arrange
        expected_activities = ["Chess Club", "Programming Class"]

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert response.status_code == 200
        assert len(data) > 0
        assert all(activity in data for activity in expected_activities)

    def test_get_activities_has_correct_structure(self, client):
        """Test that activities have all required fields"""
        # Arrange
        required_fields = ["description", "schedule", "max_participants", "participants"]

        # Act
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]

        # Assert
        assert response.status_code == 200
        assert all(field in activity for field in required_fields)
        assert isinstance(activity["participants"], list)

    def test_get_activities_participants_are_emails(self, client):
        """Test that participants are stored as email strings"""
        # Arrange
        email_domain = "@mergington.edu"

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert response.status_code == 200
        for activity_name, activity in data.items():
            for participant in activity["participants"]:
                assert isinstance(participant, str)
                assert email_domain in participant


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        # Arrange
        activity_name = "Chess Club"
        new_email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": new_email}
        )

        # Assert
        assert response.status_code == 200
        assert "message" in response.json()
        assert new_email in response.json()["message"]

    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant"""
        # Arrange
        new_email = "newstudent@mergington.edu"
        activity_name = "Chess Club"

        # Act
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": new_email}
        )
        response = client.get("/activities")
        activities = response.json()

        # Assert
        assert new_email in activities[activity_name]["participants"]

    def test_signup_activity_not_found_returns_404(self, client):
        """Test signup fails when activity doesn't exist"""
        # Arrange
        invalid_activity = "NonexistentActivity"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{invalid_activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_signup_rejected(self, client):
        """Test that duplicate signups are rejected"""
        # Arrange
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"

        # Act
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": existing_email}
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_activity_at_capacity_rejected(self, client):
        """Test signup fails when activity is at max capacity"""
        # Arrange
        activity_name = "Basketball Team"
        max_participants = 15
        existing_participants = 1  # Alex is already signed up
        available_spots = max_participants - existing_participants

        # Act - Fill the remaining spots
        for i in range(available_spots):
            email = f"student{i}@mergington.edu"
            client.post(
                "/activities/Basketball%20Team/signup",
                params={"email": email}
            )

        # Try to add one more (should fail)
        response = client.post(
            "/activities/Basketball%20Team/signup",
            params={"email": "lastStudent@mergington.edu"}
        )

        # Assert
        assert response.status_code == 400
        assert "capacity" in response.json()["detail"].lower()


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # Arrange
        activity_name = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        encoded_email = "michael%40mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{encoded_email}"
        )

        # Assert
        assert response.status_code == 200
        assert "message" in response.json()
        assert email_to_remove in response.json()["message"]

    def test_remove_participant_removes_from_activity(self, client):
        """Test that participant is actually removed from activity"""
        # Arrange
        email_to_remove = "michael@mergington.edu"
        encoded_email = "michael%40mergington.edu"

        # Verify participant exists before removal
        response_before = client.get("/activities")
        assert email_to_remove in response_before.json()["Chess Club"]["participants"]

        # Act
        client.delete(
            f"/activities/Chess%20Club/participants/{encoded_email}"
        )

        # Assert
        response_after = client.get("/activities")
        assert email_to_remove not in response_after.json()["Chess Club"]["participants"]

    def test_remove_nonexistent_activity_returns_404(self, client):
        """Test removal fails when activity doesn't exist"""
        # Arrange
        invalid_activity = "NonexistentActivity"
        email = "student%40mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{invalid_activity}/participants/{email}"
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_remove_nonexistent_participant_returns_400(self, client):
        """Test removal fails when participant is not in the activity"""
        # Arrange
        activity_name = "Chess Club"
        nonexistent_email = "notamember%40mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{nonexistent_email}"
        )

        # Assert
        assert response.status_code == 400
        assert "Participant not found" in response.json()["detail"]


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_complete_signup_and_removal_flow(self, client):
        """Test complete flow: signup -> verify -> remove -> verify"""
        # Arrange
        email = "integration@mergington.edu"
        activity_name = "Tennis Club"
        encoded_email = email.replace("@", "%40")

        # Act - Sign up
        signup_response = client.post(
            f"/activities/{activity_name.replace(' ', '%20')}/signup",
            params={"email": email}
        )

        # Assert - Signup successful
        assert signup_response.status_code == 200

        # Act - Verify signup
        verify_signup_response = client.get("/activities")
        assert email in verify_signup_response.json()[activity_name]["participants"]

        # Act - Remove participant
        remove_response = client.delete(
            f"/activities/{activity_name.replace(' ', '%20')}/participants/{encoded_email}"
        )

        # Assert - Removal successful
        assert remove_response.status_code == 200

        # Act - Verify removal
        verify_removal_response = client.get("/activities")

        # Assert - Participant is gone
        assert email not in verify_removal_response.json()[activity_name]["participants"]

    def test_multiple_students_can_signup_for_same_activity(self, client):
        """Test that multiple different students can successfully sign up"""
        # Arrange
        activity_name = "Art Studio"
        students_to_signup = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]

        # Act - Sign up all students
        signup_responses = []
        for email in students_to_signup:
            response = client.post(
                f"/activities/{activity_name.replace(' ', '%20')}/signup",
                params={"email": email}
            )
            signup_responses.append(response)

        # Assert - All signups successful
        assert all(r.status_code == 200 for r in signup_responses)

        # Act - Verify all were added
        activities = client.get("/activities").json()
        participants = activities[activity_name]["participants"]

        # Assert
        assert all(email in participants for email in students_to_signup)
