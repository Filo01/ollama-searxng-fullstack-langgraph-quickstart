# Fork Notice

**This is a fork of [google-gemini/gemini-fullstack-langgraph-quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart), updated to use Ollama for LLM and SearxNG for web search instead of Gemini and Google Search API.**

---

# Ollama + SearxNG Fullstack LangGraph Quickstart

This project demonstrates a fullstack application using a React frontend and a LangGraph-powered backend agent. The agent is designed to perform comprehensive research on a user's query by dynamically generating search terms, querying the web using SearxNG, reflecting on the results to identify knowledge gaps, and iteratively refining its search until it can provide a well-supported answer with citations. This application serves as an example of building research-augmented conversational AI using LangGraph and open-source LLMs via Ollama.

## Features

* 💬 Fullstack application with a React frontend and LangGraph backend.
* 🧠 Powered by a LangGraph agent for advanced research and conversational AI.
* 🔍 Dynamic search query generation using Ollama LLMs.
* 🌐 Integrated web research via SearxNG API.
* 🤔 Reflective reasoning to identify knowledge gaps and refine searches.
* 📄 Generates answers with citations from gathered sources.
* 🔄 Hot-reloading for both frontend and backend development during development.

## Project Structure

The project is divided into two main directories:

* `frontend/`: Contains the React application built with Vite.
* `backend/`: Contains the LangGraph/FastAPI application, including the research agent logic.

## Getting Started: Development and Local Testing

Follow these steps to get the application running locally for development and testing.

**1. Prerequisites:**

* Node.js and npm (or yarn/pnpm)
* Python 3.11+
* **Ollama**: The backend agent requires a running Ollama server with your desired model pulled (e.g., `gemma3:4b`, `gemma3:14b`, or `gemma3:27b`). The default model used is Gemma3 (4b/14b/27b). See [Ollama documentation](https://ollama.com/) for installation and model management.
* **SearxNG**: The backend agent requires access to a SearxNG instance for web search. You can run your own or use a public instance (see [SearxNG documentation](https://docs.searxng.org/)).

**2. Install Dependencies:**

**Backend:**

```sh
cd backend
pip install .
```

**Frontend:**

```sh
cd frontend
npm install
```

**3. Run Development Servers:**

**Backend & Frontend:**

```sh
make dev
```

This will run the backend and frontend development servers. Open your browser and navigate to the frontend development server URL (e.g., `http://localhost:5173/app`).

_Alternatively, you can run the backend and frontend development servers separately. For the backend, open a terminal in the `backend/` directory and run `langgraph dev`. The backend API will be available at `http://127.0.0.1:2024`. For the frontend, open a terminal in the `frontend/` directory and run `npm run dev`. The frontend will be available at `http://localhost:5173`._

## How the Backend Agent Works (High-Level)

The core of the backend is a LangGraph agent defined in `backend/src/agent/graph.py`. It follows these steps:

1. **Generate Initial Queries:** Based on your input, it generates a set of initial search queries using an Ollama model.
2. **Web Research:** For each query, it uses SearxNG to find relevant web pages.
3. **Reflection & Knowledge Gap Analysis:** The agent analyzes the search results to determine if the information is sufficient or if there are knowledge gaps. It uses an Ollama model for this reflection process.
4. **Iterative Refinement:** If gaps are found or the information is insufficient, it generates follow-up queries and repeats the web research and reflection steps (up to a configured maximum number of loops).
5. **Finalize Answer:** Once the research is deemed sufficient, the agent synthesizes the gathered information into a coherent answer, including citations from the web sources, using an Ollama model.

## Deployment

In production, the backend server serves the optimized static frontend build. LangGraph requires a Redis instance and a Postgres database. Redis is used as a pub-sub broker to enable streaming real time output from background runs. Postgres is used to store assistants, threads, runs, persist thread state and long term memory, and to manage the state of the background task queue with 'exactly once' semantics.

You will also need a running Ollama server and a SearxNG instance accessible to the backend.

Below is an example of how to build a Docker image that includes the optimized frontend build and the backend server and run it via `docker-compose`.

**1. Build the Docker Image:**

Run the following command from the **project root directory**:

```sh
docker build -t ollama-searxng-langgraph -f Dockerfile .
```

**2. Run the Production Server:**

Set the following environment variables as needed:
- `OLLAMA_MODEL` (e.g., `gemma3:27b` — default is Gemma3, available in 4b/14b/27b sizes)
- `OLLAMA_HOST` (e.g., `http://ollama:11434` if running in Docker Compose or K8s)
- `SEARXNG_URL` (e.g., `http://searxng:8080/search`)

Example with Docker Compose:

```sh
OLLAMA_MODEL=gemma3:27b OLLAMA_HOST=http://ollama:11434 SEARXNG_URL=http://searxng:8080/search docker-compose up
```

Open your browser and navigate to `http://localhost:8123/app/` to see the application. The API will be available at `http://localhost:8123`.

## Technologies Used

* React (with Vite) - For the frontend user interface.
* Tailwind CSS - For styling.
* Shadcn UI - For components.
* LangGraph - For building the backend research agent.
* Ollama - LLM for query generation, reflection, and answer synthesis.
* SearxNG - Web search API for research.

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## About

 Get started with building Fullstack Agents using Ollama, SearxNG, and LangGraph. 