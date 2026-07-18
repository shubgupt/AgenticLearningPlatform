    graph TD
    UI[Renderer UI - index.html]
    SVG[SVG Vector Puppeteer - svg_parser.js]
    AudioIO[Browser Web Audio API - Mic and TTS Sync]
    TelemetryJS[Browser Event Listeners - Tab Blur and Latency]

    Gateway[FastAPI App / WebSocket Gateway - main.py]
    Graph[LangGraph State Machine - graph.py]
    State[AgentState Schema - state.py]

    Teaching[Teaching Agent Node - dspy.Module Prompts]
    Evaluator[Evaluator Agent Node - GRPO and RLVR Model]

    MCPServer[FastMCP Tool Server - data_mcp_server]
    SQLite[SQLite Storage Engine - SQLAlchemy ORM]
    Qdrant[Qdrant Vector DB Client - parent-child chunking]

    OTel[OpenTelemetry Trace Collectors]
    Phoenix[Arize Phoenix Server - localhost:6006]
    LangSmith[LangSmith Debugger Workspace]

    UI --- Gateway
    SVG --- UI
    AudioIO --> Gateway
    TelemetryJS --> Gateway

    Gateway --- State
    Gateway --- Graph

    Graph --- Teaching
    Graph --- Evaluator

    Graph --- MCPServer
    
    MCPServer --- SQLite
    MCPServer --- Qdrant

    Graph --> OTel
    Evaluator --> LangSmith
    OTel --> Phoenix