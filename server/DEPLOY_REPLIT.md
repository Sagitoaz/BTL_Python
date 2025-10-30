# Deploying the AI Code Completion server to Replit

This document explains how to deploy the FastAPI server on Replit (or any service that exposes a PORT env var). The server talks to an Ollama endpoint which can be local or remote (Ollama Cloud or a hosted Ollama instance).

Required environment variables
- `OLLAMA_URL` - URL of the Ollama server (e.g. `http://127.0.0.1:11434` or `https://ollama.example.com`).
- `OLLAMA_API_KEY` - (optional) Bearer token if your Ollama endpoint uses an API key.
- `API_KEY` - (optional) internal API key used by this FastAPI server for any protected endpoints.

Steps
1. Push the repo to GitHub (or import it directly into Replit).
2. In Replit, create a new Repl from the GitHub repository or upload the workspace.
3. In the Replit project's secrets/environment variables, add `OLLAMA_URL` and, if required, `OLLAMA_API_KEY`.
4. Replit exposes a `PORT` env var automatically. The server's `Procfile` already uses `$PORT`.
5. Start the Repl. Replit will use the `Procfile` to run the uvicorn process.

Notes and caveats
- Replit cannot run large LLM models locally. You must point `OLLAMA_URL` to a reachable Ollama server (self-hosted elsewhere or an Ollama Cloud endpoint).
- If you use Ollama Cloud, set `OLLAMA_API_KEY` and ensure it's saved in Replit secrets.
- For local development you can keep `OLLAMA_URL=http://127.0.0.1:11434` and run a local Ollama instance on another machine accessible from Replit (must be publicly reachable).

Troubleshooting
- If you get connection errors, check that `OLLAMA_URL` is reachable from Replit and that the correct Authorization header is provided (Bearer token).
- Check Replit logs for the uvicorn output.
