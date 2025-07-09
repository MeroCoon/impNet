#!/usr/bin/env python3
import requests
import json
import base64
import time
import os
import sys
from datetime import datetime

# Get backend URL from frontend/.env
BACKEND_URL = "https://6417410b-b8cc-4eab-9179-5243dead1364.preview.emergentagent.com/api"

# Test users
TEST_USER1 = {
    "username": f"testuser1_{int(time.time())}",
    "email": f"testuser1_{int(time.time())}@example.com",
    "password": "Password123!",
    "full_name": "Test User One"
}

TEST_USER2 = {
    "username": f"testuser2_{int(time.time())}",
    "email": f"testuser2_{int(time.time())}@example.com",
    "password": "Password123!",
    "full_name": "Test User Two"
}

# Central Bank credentials
CENTRAL_BANK = {
    "username": "central_bank",
    "password": "admin123"
}

# Test results
results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(name, passed, details=None):
    """Log test results"""
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status} - {name}")
    if details and not passed:
        print(f"  Details: {details}")
    
    results["total"] += 1
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details
    })

def make_request(method, endpoint, data=None, token=None, expected_status=200):
    """Make HTTP request to API"""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers)
        elif method.lower() == "post":
            response = requests.post(url, json=data, headers=headers)
        elif method.lower() == "put":
            response = requests.put(url, json=data, headers=headers)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code != expected_status:
            return False, f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
        
        return True, response.json() if response.text else None
    except Exception as e:
        return False, f"Request error: {str(e)}"

def test_auth():
    """Test authentication endpoints"""
    print("\n=== Testing Authentication ===")
    
    # Test registration
    success, data = make_request("post", "/auth/register", TEST_USER1)
    log_test("User Registration - User 1", success, data)
    if not success:
        return None, None
    
    success, data = make_request("post", "/auth/register", TEST_USER2)
    log_test("User Registration - User 2", success, data)
    if not success:
        return None, None
    
    # Test login
    success, data = make_request("post", "/auth/login", {
        "username": TEST_USER1["username"],
        "password": TEST_USER1["password"]
    })
    log_test("User Login - User 1", success, data)
    if not success:
        return None, None
    
    token1 = data["access_token"]
    user1_id = data["user"]["id"]
    
    success, data = make_request("post", "/auth/login", {
        "username": TEST_USER2["username"],
        "password": TEST_USER2["password"]
    })
    log_test("User Login - User 2", success, data)
    if not success:
        return None, None
    
    token2 = data["access_token"]
    user2_id = data["user"]["id"]
    
    # Test get current user
    success, data = make_request("get", "/auth/me", token=token1)
    log_test("Get Current User Info", success, data)
    
    # Login as central bank
    success, data = make_request("post", "/auth/login", {
        "username": CENTRAL_BANK["username"],
        "password": CENTRAL_BANK["password"]
    })
    log_test("Central Bank Login", success, data)
    if success:
        central_bank_token = data["access_token"]
        central_bank_id = data["user"]["id"]
    else:
        central_bank_token = None
        central_bank_id = None
    
    return {
        "user1": {"token": token1, "id": user1_id},
        "user2": {"token": token2, "id": user2_id},
        "central_bank": {"token": central_bank_token, "id": central_bank_id}
    }, None

def test_banking(users):
    """Test banking endpoints"""
    print("\n=== Testing Banking System ===")
    
    # Test get balance
    success, data = make_request("get", "/banking/balance", token=users["user1"]["token"])
    log_test("Get Balance", success, data)
    if success:
        initial_balance = data["balance"]
        log_test("Initial Balance is 100 Ǐ", initial_balance == 100.0, f"Balance: {initial_balance}")
    
    # Test get users for transfer
    success, data = make_request("get", "/banking/users", token=users["user1"]["token"])
    log_test("Get Users for Transfer", success, data)
    
    # Test transfer money
    transfer_amount = 25.0
    success, data = make_request("post", "/banking/transfer", {
        "to_user_id": users["user2"]["id"],
        "amount": transfer_amount,
        "description": "Test transfer"
    }, token=users["user1"]["token"])
    log_test("Transfer Money", success, data)
    
    # Verify balance after transfer
    success, data = make_request("get", "/banking/balance", token=users["user1"]["token"])
    log_test("Balance Updated After Transfer (Sender)", 
             success and data["balance"] == (initial_balance - transfer_amount), 
             f"Expected {initial_balance - transfer_amount}, got {data['balance'] if success else 'N/A'}")
    
    success, data = make_request("get", "/banking/balance", token=users["user2"]["token"])
    log_test("Balance Updated After Transfer (Receiver)", 
             success and data["balance"] == (100.0 + transfer_amount), 
             f"Expected {100.0 + transfer_amount}, got {data['balance'] if success else 'N/A'}")
    
    # Test get transactions
    success, data = make_request("get", "/banking/transactions", token=users["user1"]["token"])
    log_test("Get Transactions", success, data)
    if success:
        log_test("Transaction History Contains Transfer", 
                 len(data) > 0 and any(t["amount"] == transfer_amount for t in data),
                 f"Transactions: {data}")

def test_chat(users):
    """Test chat endpoints"""
    print("\n=== Testing Chat System ===")
    
    # Test send message
    message_text = f"Test message from {TEST_USER1['username']} at {datetime.now().isoformat()}"
    success, data = make_request("post", "/chat/message", {
        "message": message_text,
        "message_type": "text"
    }, token=users["user1"]["token"])
    log_test("Send Chat Message", success, data)
    
    # Test get messages
    success, data = make_request("get", "/chat/messages", token=users["user1"]["token"])
    log_test("Get Chat Messages", success, data)
    if success:
        log_test("Chat History Contains Sent Message", 
                 len(data) > 0 and any(m["message"] == message_text for m in data),
                 f"Messages: {data[:2]}")

def test_email(users):
    """Test email endpoints"""
    print("\n=== Testing Email System ===")
    
    # Test send email
    email_subject = f"Test email from {TEST_USER1['username']}"
    email_body = f"This is a test email sent at {datetime.now().isoformat()}"
    success, data = make_request("post", "/email/send", {
        "to_user_id": users["user2"]["id"],
        "subject": email_subject,
        "body": email_body
    }, token=users["user1"]["token"])
    log_test("Send Email", success, data)
    
    # Test get sent emails
    success, data = make_request("get", "/email/sent", token=users["user1"]["token"])
    log_test("Get Sent Emails", success, data)
    if success:
        log_test("Sent Emails Contains Test Email", 
                 len(data) > 0 and any(e["subject"] == email_subject for e in data),
                 f"Emails: {data[:2]}")
    
    # Test get inbox
    success, data = make_request("get", "/email/inbox", token=users["user2"]["token"])
    log_test("Get Inbox", success, data)
    if success:
        log_test("Inbox Contains Received Email", 
                 len(data) > 0 and any(e["subject"] == email_subject for e in data),
                 f"Emails: {data[:2]}")
        
        # Test mark as read
        if len(data) > 0:
            email_id = next((e["id"] for e in data if e["subject"] == email_subject), None)
            if email_id:
                success, data = make_request("put", f"/email/{email_id}/read", token=users["user2"]["token"])
                log_test("Mark Email as Read", success, data)

def test_files(users):
    """Test file system endpoints"""
    print("\n=== Testing File System ===")
    
    # Create a small test file in base64
    test_content = "This is a test file content for ImpNet file system."
    file_data = base64.b64encode(test_content.encode()).decode()
    
    # Test upload file
    success, data = make_request("post", "/files/upload", {
        "filename": "test_file.txt",
        "file_data": file_data,
        "file_type": "text/plain",
        "file_size": len(test_content),
        "description": "Test file upload",
        "is_public": True
    }, token=users["user1"]["token"])
    log_test("Upload File", success, data)
    
    # Test get files list
    success, data = make_request("get", "/files/list", token=users["user1"]["token"])
    log_test("Get Files List", success, data)
    if success:
        log_test("Files List Contains Uploaded File", 
                 len(data) > 0 and any(f["filename"] == "test_file.txt" for f in data),
                 f"Files: {data[:2]}")
        
        # Test get specific file
        if len(data) > 0:
            file_id = next((f["id"] for f in data if f["filename"] == "test_file.txt"), None)
            if file_id:
                success, file_data = make_request("get", f"/files/{file_id}", token=users["user1"]["token"])
                log_test("Get Specific File", success, file_data)

def test_search(users):
    """Test search endpoints"""
    print("\n=== Testing Search System ===")
    
    # Test search for messages
    success, data = make_request("post", "/search", {
        "query": "Test message",
        "search_type": "messages"
    }, token=users["user1"]["token"])
    log_test("Search Messages", success, data)
    
    # Test search for files
    success, data = make_request("post", "/search", {
        "query": "test_file",
        "search_type": "files"
    }, token=users["user1"]["token"])
    log_test("Search Files", success, data)
    
    # Test search for users
    success, data = make_request("post", "/search", {
        "query": "Test User",
        "search_type": "users"
    }, token=users["user1"]["token"])
    log_test("Search Users", success, data)
    
    # Test search all
    success, data = make_request("post", "/search", {
        "query": "test",
        "search_type": "all"
    }, token=users["user1"]["token"])
    log_test("Search All Content", success, data)

def main():
    print(f"Testing ImpNet Backend API at {BACKEND_URL}")
    print("=" * 50)
    
    # Test authentication
    users, error = test_auth()
    if not users:
        print(f"Authentication tests failed: {error}")
        return
    
    # Test other endpoints
    test_banking(users)
    test_chat(users)
    test_email(users)
    test_files(users)
    test_search(users)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"SUMMARY: {results['passed']}/{results['total']} tests passed")
    if results['failed'] > 0:
        print(f"Failed tests: {results['failed']}")
        for test in results['tests']:
            if not test['passed']:
                print(f"  - {test['name']}: {test['details']}")
    else:
        print("All tests passed successfully!")

if __name__ == "__main__":
    main()