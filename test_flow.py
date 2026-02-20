import pytest
import requests
import websockets
import json

API_URL = "http://127.0.0.1:8080/api/v1"
WS_URL = "ws://127.0.0.1:8080/ws"

@pytest.fixture(scope="module")
def setup_users():
    # 1. Signup Users
    user1_data = {"email": "alice_test@example.com", "username": "alice_test", "password": "password123"}
    user2_data = {"email": "bob_test@example.com", "username": "bob_test", "password": "password123"}
    
    requests.post(f"{API_URL}/auth/signup", json=user1_data)
    requests.post(f"{API_URL}/auth/signup", json=user2_data)

    # 2. Login User 1 (Alice)
    r_login1 = requests.post(f"{API_URL}/auth/login", data={"username": "alice_test", "password": "password123"})
    token1 = r_login1.json()["access_token"]
    
    # 3. Login User 2 (Bob)
    r_login2 = requests.post(f"{API_URL}/auth/login", data={"username": "bob_test", "password": "password123"})
    token2 = r_login2.json()["access_token"]
    
    # Needs Bob's actual User ID to add him to the project. Let's make a quick temporary hack using a raw sqlite query to get his ID for this test since we didn't expose GET /users/me
    import sqlite3
    conn = sqlite3.connect("peroxia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username='bob_test'")
    bob_id = cursor.fetchone()[0]
    conn.close()

    # Get Alice's Token for auth headers
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    # 4. Create Project
    project_data = {"name": "Test Project", "description": "Testing project"}
    r_proj = requests.post(f"{API_URL}/projects/", json=project_data, headers=headers1)
    project_id = r_proj.json()["id"]
    
    # 5. Add Bob to Project
    member_data = {"user_id": bob_id} 
    requests.post(f"{API_URL}/projects/{project_id}/members", json=member_data, headers=headers1)

    return {"project_id": project_id, "token1": token1, "token2": token2, "bob_id": bob_id}

def test_rest_flow(setup_users):
    assert setup_users["project_id"] is not None
    assert setup_users["token1"] is not None

@pytest.mark.asyncio
async def test_websocket_flow(setup_users):
    project_id = setup_users["project_id"]
    token1 = setup_users["token1"]
    token2 = setup_users["token2"]
    
    ws_endpoint = f"{WS_URL}/projects/{project_id}?token={token2}"
    
    async with websockets.connect(ws_endpoint) as ws:
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Action 1: Create Task
        task_data = {"title": "Design Database Schema", "description": "Needs to be robust and scalable"}
        r_task = requests.post(f"{API_URL}/projects/{project_id}/tasks", json=task_data, headers=headers1)
        assert r_task.status_code == 201
        task_id = r_task.json()["id"]
        
        # Receive event
        event1 = json.loads(await ws.recv())
        assert event1["event"] == "task_created"

        # Action 2: Update Task Status
        status_data = {"status": "in_progress"}
        r_status = requests.patch(f"{API_URL}/tasks/{task_id}/status", json=status_data, headers=headers1)
        assert r_status.status_code == 200
        
        # Receive event
        event2 = json.loads(await ws.recv())
        assert event2["event"] == "status_changed"
        assert event2["data"]["status"] == "in_progress"
        
        # Action 3: Assign Task
        update_data = {"assignee_id": 2}
        r_update = requests.put(f"{API_URL}/tasks/{task_id}", json=update_data, headers=headers1)
        assert r_update.status_code == 200
        
        # Receive event
        event3 = json.loads(await ws.recv())
        assert event3["event"] == "task_updated"
        assert event3["data"]["assignee_id"] == 2

