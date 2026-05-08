import { FormEvent, useState } from "react";
import { AuthSession } from "../api";

type Props = {
  session: AuthSession | null;
  telegramAvailable: boolean;
  authStatus: string;
  onTelegram: () => void;
  onLogin: (nickname: string, password: string) => Promise<void>;
  onLogout: () => void;
  onBack: () => void;
};

export function AccountScreen({ session, telegramAvailable, authStatus, onTelegram, onLogin, onLogout, onBack }: Props) {
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onLogin(nickname, password);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="menu-screen">
      <div className="account-panel">
        <h1>Account</h1>
        {session && (
          <div className="account-current">
            <span>Current account</span>
            <strong>{session.user.nickname}</strong>
            <button className="small-button" onClick={onLogout}>Switch / Logout</button>
          </div>
        )}

        <button className="menu-button menu-button-primary" onClick={onTelegram} disabled={!telegramAvailable || busy}>
          Continue with Telegram
        </button>
        <p className="muted">{authStatus}</p>

        <form className="login-form" onSubmit={submit}>
          <label>
            Nickname
            <input value={nickname} onChange={(event) => setNickname(event.target.value)} autoComplete="username" />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          <button className="menu-button" disabled={busy || nickname.length < 3 || password.length < 6}>
            Login with Existing Account
          </button>
        </form>

        <button className="menu-button menu-button-secondary" onClick={onBack}>Back</button>
      </div>
    </section>
  );
}
