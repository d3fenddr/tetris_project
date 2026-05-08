import { AuthSession } from "../api";
import { SoundToggle } from "./SoundToggle";

type Props = {
  session: AuthSession | null;
  authStatus: string;
  soundEnabled: boolean;
  onPlay: () => void;
  onLeaderboard: () => void;
  onAccount: () => void;
  onToggleSound: () => void;
};

export function MainMenu({ session, authStatus, soundEnabled, onPlay, onLeaderboard, onAccount, onToggleSound }: Props) {
  return (
    <section className="menu-screen">
      <div className="menu-stack">
        <p className="season-title">SEASON 2</p>
        <h1>TETRIS</h1>
        <div className="account-pill">
          {session ? `Playing as ${session.user.nickname}` : authStatus || "Choose an account to save scores"}
        </div>
        <button className="menu-button menu-button-primary" onClick={onPlay}>Play</button>
        <button className="menu-button" onClick={onLeaderboard}>Leaderboard</button>
        <button className="menu-button" onClick={onAccount}>Account / Login</button>
        <SoundToggle enabled={soundEnabled} onToggle={onToggleSound} />
      </div>
    </section>
  );
}
