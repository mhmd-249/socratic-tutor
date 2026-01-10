#!/usr/bin/env python3
"""
Interactive Chat with Socratic Tutor

This script lets you have a real conversation with the AI tutor.
Type your messages and see the tutor's responses in real-time.

Usage:
    1. Update TOKEN and CHAPTER_ID below
    2. Run: poetry run python scripts/interactive_chat.py
    3. Chat naturally - type your messages and press Enter
    4. Type 'quit' or 'end' to finish and see the summary
"""

import asyncio
import json
import sys
import httpx

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
API_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjlkZmYwYjAzLTZlYmItNGQxYi05NDI0LTMxMTY2NGEzODYzOCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3FtanB6Z2hhaHBjZG91YWxyZWx2LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI2ZjRlYzM2MS1lMTI5LTQ4ZDgtODk2OC1kNzYwMDI5YmI1NjUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4MDkxMjAwLCJpYXQiOjE3NjgwODc2MDAsImVtYWlsIjoibW9oYW1tZWRAZXF1aXRlY2hmdXR1cmVzLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJtb2hhbW1lZEBlcXVpdGVjaGZ1dHVyZXMuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5hbWUiOiJNb2hhbW1lZCBNb2hhbW1lZCIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiNmY0ZWMzNjEtZTEyOS00OGQ4LTg5NjgtZDc2MDAyOWJiNTY1In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NjgwODc2MDB9XSwic2Vzc2lvbl9pZCI6ImM0MDc3ZjJmLTBiZjMtNDMxNi04MmViLTgzYTVmYTgwYjI3YSIsImlzX2Fub255bW91cyI6ZmFsc2V9.iKICnHegW2QodqWgDxAUas8RZSHRK-tJTuMDHOcJPgB7LkhwF3HV0xUf0ZPf5HUhMG4CZ5HDtdXv2axYV-KHgg"  # Get from browser DevTools -> Application -> Local Storage
CHAPTER_ID = "f25afb85-a98c-4db8-bd44-d0bef41f5688"  # Get from: SELECT id, title FROM chapters LIMIT 5;

# =============================================================================
# MAIN INTERACTIVE CHAT
# =============================================================================

async def stream_response(client: httpx.AsyncClient, conv_id: str, headers: dict, message: str) -> str:
    """Send a message and stream the response."""
    full_response = ""
    
    try:
        async with client.stream(
            "POST",
            f"{API_URL}/conversations/{conv_id}/messages",
            headers={**headers, "Accept": "text/event-stream"},
            json={"message": message},
            timeout=120.0
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                print(f"\n❌ Error: {response.status_code} - {error_text.decode()}")
                return ""
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "content" in data:
                            print(data["content"], end="", flush=True)
                            full_response += data["content"]
                        elif data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
                        
    except httpx.TimeoutException:
        print("\n❌ Request timed out")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return full_response


async def interactive_chat():
    """Run an interactive chat session."""
    
    print("\n" + "=" * 60)
    print("  🎓 SOCRATIC TUTOR - Interactive Chat")
    print("=" * 60)
    print("\nCommands:")
    print("  • Type your message and press Enter to chat")
    print("  • Type 'quit' or 'end' to finish and see summary")
    print("  • Type 'exit' to quit without summary")
    print("-" * 60)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # Create conversation
        print("\n⏳ Starting conversation...")
        resp = await client.post(
            f"{API_URL}/conversations",
            headers=headers,
            json={"chapter_id": CHAPTER_ID}
        )
        
        if resp.status_code not in (200, 201):
            print(f"❌ Failed to create conversation: {resp.status_code}")
            print(f"   {resp.text}")
            return
        
        conversation = resp.json()
        conv_id = conversation["id"]
        
        # Show initial greeting
        initial_message = conversation.get("initial_message") or ""
        if not initial_message and conversation.get("messages"):
            initial_message = conversation["messages"][0].get("content", "")
        
        print(f"\n🤖 Tutor:\n{initial_message}")
        
        # Interactive loop
        message_count = 1
        while True:
            print()
            try:
                user_input = input("👤 You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n⚠️ Interrupted. Ending conversation...")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("\n👋 Exiting without saving summary.")
                return
            
            if user_input.lower() in ('quit', 'end', 'done', 'finish'):
                print("\n⏳ Ending conversation and generating summary...")
                break
            
            # Send message and stream response
            print("\n🤖 Tutor: ", end="", flush=True)
            response = await stream_response(client, conv_id, headers, user_input)
            
            if response:
                message_count += 2
                print()  # New line after streaming
            else:
                print("(No response received)")
        
        # End conversation and get summary
        print("-" * 60)
        resp = await client.post(
            f"{API_URL}/conversations/{conv_id}/end",
            headers=headers,
            timeout=120.0
        )
        
        if resp.status_code != 200:
            print(f"❌ Failed to end conversation: {resp.status_code}")
            print(f"   {resp.text}")
            return
        
        summary = resp.json()
        
        # Display summary
        print("\n" + "=" * 60)
        print("  📊 CONVERSATION SUMMARY")
        print("=" * 60)
        
        print(f"\n📝 Summary:\n   {summary.get('summary', 'N/A')}")
        
        topics = summary.get('topics_covered', [])
        print(f"\n📚 Topics Covered:")
        if topics:
            for t in topics:
                print(f"   • {t}")
        else:
            print("   (none)")
        
        understood = summary.get('concepts_understood', [])
        print(f"\n✅ Concepts Understood:")
        if understood:
            for c in understood:
                if isinstance(c, dict):
                    print(f"   • {c.get('concept', c)} (confidence: {c.get('confidence', '?')})")
                else:
                    print(f"   • {c}")
        else:
            print("   (none)")
        
        struggled = summary.get('concepts_struggled', [])
        print(f"\n⚠️ Concepts Struggled:")
        if struggled:
            for c in struggled:
                if isinstance(c, dict):
                    print(f"   • {c.get('concept', c)} (severity: {c.get('severity', '?')})")
                else:
                    print(f"   • {c}")
        else:
            print("   (none)")
        
        print(f"\n📈 Metrics:")
        print(f"   • Messages exchanged: {message_count}")
        print(f"   • Questions asked: {summary.get('questions_asked', 'N/A')}")
        print(f"   • Engagement score: {summary.get('engagement_score', 'N/A')}")
        
        print("\n" + "=" * 60)
        print(f"💾 Conversation ID: {conv_id}")
        print("\nTo verify in database:")
        print(f"  docker exec -it socratic-tutor-db psql -U postgres -d socratic_tutor \\")
        print(f"    -c \"SELECT * FROM conversation_summaries WHERE conversation_id = '{conv_id}';\"")
        print("=" * 60)


if __name__ == "__main__":
    if TOKEN == "YOUR_TOKEN_HERE":
        print("❌ Please update TOKEN in the script")
        print("   Get it from: Browser DevTools -> Application -> Local Storage -> access_token")
        sys.exit(1)
    
    if CHAPTER_ID == "YOUR_CHAPTER_ID":
        print("❌ Please update CHAPTER_ID in the script")
        print("   Get it from: docker exec -it socratic-tutor-db psql -U postgres -d socratic_tutor -c 'SELECT id, title FROM chapters LIMIT 5;'")
        sys.exit(1)
    
    asyncio.run(interactive_chat())