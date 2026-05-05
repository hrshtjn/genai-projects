import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import "./index.css";

const RUNTIME_URL = "/copilotkit";

export default function App() {
  return (
    <CopilotKit runtimeUrl={RUNTIME_URL} agent="my_agent">
      <div className="app-shell">
        <header className="app-header">
          <h1>AG-UI Chat</h1>
          <span className="badge">Powered by Google ADK</span>
        </header>

        <main className="chat-container">
          <CopilotChat
            labels={{
              title: "ADK Assistant",
              initial:
                "👋 Hi! I'm your AI assistant powered by Google ADK and the AG-UI protocol. Ask me anything!",
              placeholder: "Type a message…",
            }}
            className="copilot-chat"
          />
        </main>
      </div>
    </CopilotKit>
  );
}
