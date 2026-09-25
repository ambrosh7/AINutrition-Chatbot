import { AppHeader } from "./components/AppHeader";
import { ChatWindow } from "./components/ChatWindow";
import "./styles.css";

export default function App() {
  return (
    <div className="app">
      <AppHeader />
      <main className="app-main">
        <ChatWindow />
      </main>
    </div>
  );
}
