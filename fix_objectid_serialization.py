#!/usr/bin/env python3
"""
This script fixes the MongoDB ObjectId serialization issue in the ImpNet backend.
It adds a custom JSON encoder to handle ObjectId serialization.
"""

import os
import json
from bson import ObjectId
from fastapi.encoders import jsonable_encoder

# Path to the server.py file
SERVER_FILE = "/app/backend/server.py"

# Custom JSON encoder for ObjectId
CUSTOM_ENCODER_CODE = """
# Custom JSON encoder for MongoDB ObjectId
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

# Custom jsonable_encoder for FastAPI
def custom_jsonable_encoder(obj, *args, **kwargs):
    if hasattr(obj, '_id') and isinstance(obj['_id'], ObjectId):
        obj['id'] = str(obj['_id'])
        del obj['_id']
    return jsonable_encoder(obj, *args, **kwargs)
"""

# Function to convert MongoDB documents to JSON-serializable format
DOCUMENT_CONVERTER_CODE = """
# Helper function to convert MongoDB documents to JSON-serializable format
def convert_mongo_doc(doc):
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [convert_mongo_doc(item) for item in doc]
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == '_id':
                result['id'] = str(value)
            elif isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, (dict, list)):
                result[key] = convert_mongo_doc(value)
            else:
                result[key] = value
        return result
    
    return doc
"""

# Import statement for ObjectId
OBJECTID_IMPORT = "from bson import ObjectId"

# Code to modify the endpoints to use the converter
ENDPOINT_FIXES = [
    # Banking transactions endpoint
    {
        "old": "async def get_transactions(current_user: User = Depends(get_current_user)):\n    transactions = await db.transactions.find({",
        "new": "async def get_transactions(current_user: User = Depends(get_current_user)):\n    transactions = await db.transactions.find({"
    },
    {
        "old": "    }).sort(\"created_at\", -1).to_list(100)\n    return transactions",
        "new": "    }).sort(\"created_at\", -1).to_list(100)\n    return convert_mongo_doc(transactions)"
    },
    
    # Chat messages endpoint
    {
        "old": "async def get_chat_messages(current_user: User = Depends(get_current_user)):\n    messages = await db.chat_messages.find().sort(\"created_at\", -1).limit(100).to_list(100)\n    return messages",
        "new": "async def get_chat_messages(current_user: User = Depends(get_current_user)):\n    messages = await db.chat_messages.find().sort(\"created_at\", -1).limit(100).to_list(100)\n    return convert_mongo_doc(messages)"
    },
    
    # Email inbox endpoint
    {
        "old": "async def get_inbox(current_user: User = Depends(get_current_user)):\n    emails = await db.emails.find({",
        "new": "async def get_inbox(current_user: User = Depends(get_current_user)):\n    emails = await db.emails.find({"
    },
    {
        "old": "    }).sort(\"created_at\", -1).to_list(100)\n    return emails",
        "new": "    }).sort(\"created_at\", -1).to_list(100)\n    return convert_mongo_doc(emails)"
    },
    
    # Email sent endpoint
    {
        "old": "async def get_sent_emails(current_user: User = Depends(get_current_user)):\n    emails = await db.emails.find({",
        "new": "async def get_sent_emails(current_user: User = Depends(get_current_user)):\n    emails = await db.emails.find({"
    },
    {
        "old": "    }).sort(\"created_at\", -1).to_list(100)\n    return emails",
        "new": "    }).sort(\"created_at\", -1).to_list(100)\n    return convert_mongo_doc(emails)"
    },
    
    # Files list endpoint
    {
        "old": "async def get_files(current_user: User = Depends(get_current_user)):\n    files = await db.file_shares.find({\"is_public\": True}).sort(\"created_at\", -1).to_list(100)\n    return files",
        "new": "async def get_files(current_user: User = Depends(get_current_user)):\n    files = await db.file_shares.find({\"is_public\": True}).sort(\"created_at\", -1).to_list(100)\n    return convert_mongo_doc(files)"
    },
    
    # File by ID endpoint
    {
        "old": "async def get_file(file_id: str, current_user: User = Depends(get_current_user)):\n    file = await db.file_shares.find_one({\"id\": file_id})\n    if not file:\n        raise HTTPException(status_code=404, detail=\"File not found\")\n    return file",
        "new": "async def get_file(file_id: str, current_user: User = Depends(get_current_user)):\n    file = await db.file_shares.find_one({\"id\": file_id})\n    if not file:\n        raise HTTPException(status_code=404, detail=\"File not found\")\n    return convert_mongo_doc(file)"
    },
    
    # Search endpoint
    {
        "old": "async def search(query: SearchQuery, current_user: User = Depends(get_current_user)):\n    results = {\"messages\": [], \"files\": [], \"users\": []}",
        "new": "async def search(query: SearchQuery, current_user: User = Depends(get_current_user)):\n    results = {\"messages\": [], \"files\": [], \"users\": []}"
    },
    {
        "old": "        messages = await db.chat_messages.find({\n            \"message\": {\"$regex\": query.query, \"$options\": \"i\"}\n        }).limit(20).to_list(20)\n        results[\"messages\"] = messages",
        "new": "        messages = await db.chat_messages.find({\n            \"message\": {\"$regex\": query.query, \"$options\": \"i\"}\n        }).limit(20).to_list(20)\n        results[\"messages\"] = convert_mongo_doc(messages)"
    },
    {
        "old": "        files = await db.file_shares.find({\n            \"$or\": [\n                {\"filename\": {\"$regex\": query.query, \"$options\": \"i\"}},\n                {\"description\": {\"$regex\": query.query, \"$options\": \"i\"}}\n            ],\n            \"is_public\": True\n        }).limit(20).to_list(20)\n        results[\"files\"] = files",
        "new": "        files = await db.file_shares.find({\n            \"$or\": [\n                {\"filename\": {\"$regex\": query.query, \"$options\": \"i\"}},\n                {\"description\": {\"$regex\": query.query, \"$options\": \"i\"}}\n            ],\n            \"is_public\": True\n        }).limit(20).to_list(20)\n        results[\"files\"] = convert_mongo_doc(files)"
    }
]

def read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

def write_file(file_path, content):
    with open(file_path, 'w') as f:
        f.write(content)

def add_objectid_import(content):
    # Check if ObjectId is already imported
    if "from bson import ObjectId" not in content:
        # Add import after the first import statement
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                lines.insert(i + 1, OBJECTID_IMPORT)
                break
        return '\n'.join(lines)
    return content

def insert_after_imports(content):
    # Find the last import statement
    import_lines = [i for i, line in enumerate(content.split('\n')) if line.startswith('import ') or line.startswith('from ')]
    last_import_line = max(import_lines) if import_lines else 0
    
    # Split the content at the last import line
    lines = content.split('\n')
    before = '\n'.join(lines[:last_import_line + 1])
    after = '\n'.join(lines[last_import_line + 1:])
    
    # Insert the custom encoder code after the imports
    return before + '\n\n' + DOCUMENT_CONVERTER_CODE + '\n' + after

def apply_endpoint_fixes(content):
    for fix in ENDPOINT_FIXES:
        content = content.replace(fix["old"], fix["new"])
    return content

def main():
    print("Fixing MongoDB ObjectId serialization issue in ImpNet backend...")
    
    # Read the server.py file
    content = read_file(SERVER_FILE)
    
    # Add ObjectId import
    content = add_objectid_import(content)
    
    # Insert the document converter function after imports
    content = insert_after_imports(content)
    
    # Apply endpoint fixes
    content = apply_endpoint_fixes(content)
    
    # Write the modified content back to the file
    write_file(SERVER_FILE, content)
    
    print("Fix applied successfully!")
    print("Restart the backend to apply the changes:")
    print("  sudo supervisorctl restart backend")

if __name__ == "__main__":
    main()