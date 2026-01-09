import asyncio
import httpx

API_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjlkZmYwYjAzLTZlYmItNGQxYi05NDI0LTMxMTY2NGEzODYzOCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3FtanB6Z2hhaHBjZG91YWxyZWx2LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI2ZjRlYzM2MS1lMTI5LTQ4ZDgtODk2OC1kNzYwMDI5YmI1NjUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTg2MTk0LCJpYXQiOjE3Njc5ODI1OTQsImVtYWlsIjoibW9oYW1tZWRAZXF1aXRlY2hmdXR1cmVzLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJtb2hhbW1lZEBlcXVpdGVjaGZ1dHVyZXMuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5hbWUiOiJNb2hhbW1lZCBNb2hhbW1lZCIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiNmY0ZWMzNjEtZTEyOS00OGQ4LTg5NjgtZDc2MDAyOWJiNTY1In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc5ODI1OTR9XSwic2Vzc2lvbl9pZCI6IjBmODVjYjYyLWRiOWUtNDM2OS1hZjJhLWRkY2M0Mjg4YTE1OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.ojNl1qoMhT458_fH9w8-qaDjk0Efp9wpPcA41PxtyfNwyaqfr1CQ7kgc8Vh3S6pYV117CKOfzD6w9QUX_Iou-g"  # Replace with actual token
CHAPTER_ID = "f25afb85-a98c-4db8-bd44-d0bef41f5688"  # Replace with actual chapter ID

headers = {"Authorization": f"Bearer {TOKEN}"}

async def test_chat():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create conversation
        print("=" * 50)
        print("Creating conversation...")
        resp = await client.post(
            f"{API_URL}/conversations",
            headers=headers,
            json={"chapter_id": CHAPTER_ID}
        )
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return
            
        conversation = resp.json()
        conv_id = conversation["id"]
        print(f"Conversation ID: {conv_id}")
        print(f"Initial greeting: {conversation['messages'][0]['content'][:200]}...")
        
        # 2. Send a message and stream response
        print("\n" + "=" * 50)
        print("Sending message: 'What is feature engineering?'")
        print("Streaming response:")
        
        async with client.stream(
            "POST",
            f"{API_URL}/conversations/{conv_id}/messages",
            headers={**headers, "Accept": "text/event-stream"},
            json={"content": "What is feature engineering? Can you explain it simply?"}
        ) as response:
            full_response = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    data = json.loads(line[6:])
                    if "content" in data:
                        print(data["content"], end="", flush=True)
                        full_response += data["content"]
                    elif data.get("done"):
                        print("\n[STREAM COMPLETE]")
        
        # 3. Check if response is Socratic (asks questions, doesn't just answer)
        print("\n" + "=" * 50)
        print("Checking Socratic style...")
        if "?" in full_response:
            print("✅ Response contains questions (Socratic style)")
        else:
            print("⚠️  Response has no questions - may need prompt tuning")
        
        # 4. End conversation
        print("\n" + "=" * 50)
        print("Ending conversation...")
        resp = await client.post(
            f"{API_URL}/conversations/{conv_id}/end",
            headers=headers
        )
        summary = resp.json()
        print(f"Summary: {summary.get('summary', {})}")
        
        print("\n" + "=" * 50)
        print("✅ Chat service test complete!")

if __name__ == "__main__":
    asyncio.run(test_chat())