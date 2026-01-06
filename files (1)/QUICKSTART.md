# Quick Start Checklist

## Before You Begin

### 1. Accounts & API Keys (Get these first)
- [ ] Supabase account (free tier works) - https://supabase.com
- [ ] Anthropic API key - https://console.anthropic.com
- [ ] OpenAI API key (for embeddings) - https://platform.openai.com
- [ ] Vercel account (free tier) - https://vercel.com
- [ ] Railway account (free tier) - https://railway.app

### 2. Local Setup
- [ ] Docker Desktop installed and running
- [ ] Node.js 20+ installed
- [ ] Python 3.12 installed
- [ ] Poetry installed (`pip install poetry`)
- [ ] Claude Code installed and authenticated

### 3. Prepare Your Book
- [ ] Have your PDF book file ready
- [ ] Know the chapter structure (titles, page numbers)
- [ ] Identify any prerequisite relationships between chapters

---

## Starting the Project

### Step 1: Create Project Folder
```bash
mkdir socratic-tutor
cd socratic-tutor
```

### Step 2: Copy the Setup Files
Copy these files into your project folder:
- `CLAUDE.md` → `socratic-tutor/CLAUDE.md`
- `.claude/commands/` → `socratic-tutor/.claude/commands/`

### Step 3: Start Claude Code
```bash
claude
```

### Step 4: Verify Claude Code has Context
In Claude Code, type:
```
Summarize what you know about this project from CLAUDE.md
```
It should describe the AI Socratic Tutor project.

### Step 5: Begin Phase 0
Copy the "Prompt 0.1: Initialize Project Structure" from IMPLEMENTATION_GUIDE.md

---

## During Development

### Save Your Progress
After completing each phase:
```bash
!git add -A
!git commit -m "feat: complete phase X"
```

### If You Need to Stop
Claude Code sessions can be resumed. Your project files persist.

### If You Hit Errors
1. Copy the full error message
2. Ask Claude to debug
3. Don't skip fixing errors before moving on

### Test Frequently
```bash
# Backend tests
!cd backend && pytest

# Frontend dev server
!cd frontend && npm run dev
```

---

## Phase Completion Checklist

### Phase 0: Setup ✓
- [ ] Project structure created
- [ ] Docker compose works (`docker compose up`)
- [ ] Backend runs (`make backend`)
- [ ] Frontend runs (`make frontend`)

### Phase 1: Auth ✓
- [ ] Can sign up new user
- [ ] Can log in
- [ ] Protected routes work
- [ ] User created in database

### Phase 2: RAG ✓
- [ ] Book PDF ingested
- [ ] Chapters created in database
- [ ] Chunks with embeddings stored
- [ ] Retrieval returns relevant chunks

### Phase 3: Chat ✓
- [ ] Can start conversation
- [ ] Messages stream correctly
- [ ] RAG context included in responses
- [ ] Socratic style working

### Phase 4: Learning Profile ✓
- [ ] Summary generated after conversation
- [ ] Profile updated with mastery scores
- [ ] Gaps identified correctly
- [ ] Recommendations make sense
- [ ] Cross-conversation memory works

### Phase 5: Frontend ✓
- [ ] Dashboard shows chapter cards
- [ ] Cards show mastery status
- [ ] Chat interface works smoothly
- [ ] Profile page shows progress

### Phase 6: Deploy ✓
- [ ] Backend deployed to Railway
- [ ] Frontend deployed to Vercel
- [ ] Database connected
- [ ] End-to-end flow works in production

---

## Troubleshooting Common Issues

### "Docker containers won't start"
```bash
docker compose down -v  # Remove volumes
docker compose up --build  # Rebuild
```

### "Database connection refused"
- Check PostgreSQL container is running
- Check DATABASE_URL in .env
- Wait a few seconds for DB to initialize

### "Supabase auth not working"
- Verify SUPABASE_URL and keys are correct
- Check Supabase dashboard for auth settings
- Ensure redirect URLs are configured

### "Embeddings failing"
- Check OPENAI_API_KEY is set
- Verify you have API credits
- Check rate limits

### "Claude API errors"
- Verify ANTHROPIC_API_KEY is set
- Check you have API credits
- Look at response for specific error

---

## Getting Help

### In Claude Code
- Use `/help` to see all commands
- Use `/bug` to report issues
- Ask Claude to explain any code it generates

### Documentation
- Anthropic: https://docs.anthropic.com
- FastAPI: https://fastapi.tiangolo.com
- Next.js: https://nextjs.org/docs
- Supabase: https://supabase.com/docs
