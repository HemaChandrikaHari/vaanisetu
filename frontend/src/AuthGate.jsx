import { useEffect, useState } from "react";
import { FirebaseAuthentication } from "@capacitor-firebase/authentication";
import { Capacitor } from "@capacitor/core";

const isNative = Capacitor.isNativePlatform();

function messageFor(error) {
  const code = error?.code || "";
  if (code.includes("invalid-email")) return "Enter a valid email address.";
  if (code.includes("weak-password")) return "Choose a password with at least 8 characters.";
  if (code.includes("email-already-in-use")) return "An account already exists with this email. Please sign in instead.";
  if (code.includes("invalid-credential") || code.includes("wrong-password") || code.includes("user-not-found")) return "The email or password is incorrect.";
  if (code.includes("too-many-requests")) return "Too many attempts. Please wait before trying again.";
  return error?.message || "Authentication could not be completed. Please try again.";
}

function savedPhone(uid) {
  try { return localStorage.getItem("vaanisetu_phone_" + uid) || ""; } catch { return ""; }
}

export default function AuthGate({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState("signup");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("+91");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!isNative) { setChecking(false); return undefined; }
    let active = true;
    let authListener;
    FirebaseAuthentication.getCurrentUser()
      .then(({ user: current }) => { if (active) setUser(current || null); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setChecking(false); });
    FirebaseAuthentication.addListener("authStateChange", (event) => {
      if (active) setUser(event.user || null);
    }).then((listener) => { authListener = listener; }).catch(() => {});
    return () => { active = false; authListener?.remove(); };
  }, []);

  async function register(event) {
    event.preventDefault();
    setNotice("");
    const normalizedEmail = email.trim().toLowerCase();
    if (!name.trim() || !/^\S+@\S+\.\S+$/.test(normalizedEmail) || password.length < 8) {
      setNotice("Enter your name, a valid Gmail/email address and a password of at least 8 characters.");
      return;
    }
    if (!/^\+[1-9]\d{7,14}$/.test(phone.trim())) {
      setNotice("Enter your mobile number with country code, for example +91XXXXXXXXXX.");
      return;
    }
    setBusy(true);
    try {
      const result = await FirebaseAuthentication.createUserWithEmailAndPassword({ email: normalizedEmail, password });
      if (!result.user) throw new Error("Firebase did not return a new user account.");
      await FirebaseAuthentication.updateProfile({ displayName: name.trim() });
      try { localStorage.setItem("vaanisetu_phone_" + result.user.uid, phone.trim()); } catch {}
      await FirebaseAuthentication.sendEmailVerification();
      const refreshed = (await FirebaseAuthentication.getCurrentUser()).user || result.user;
      setUser(refreshed);
      setNotice("Verification email sent. Open the link in your inbox, then return here and tap “I've verified my email”.");
    } catch (error) {
      setNotice(messageFor(error));
    } finally {
      setBusy(false);
    }
  }

  async function signIn(event) {
    event.preventDefault();
    setNotice("");
    if (!/^\S+@\S+\.\S+$/.test(email.trim()) || !password) {
      setNotice("Enter the email address and password linked to your VaaniSetu account.");
      return;
    }
    setBusy(true);
    try {
      const result = await FirebaseAuthentication.signInWithEmailAndPassword({ email: email.trim().toLowerCase(), password });
      setUser(result.user || null);
      if (result.user && !result.user.emailVerified) setNotice("Your email is not verified yet. Open the verification link in your inbox.");
    } catch (error) {
      setNotice(messageFor(error));
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    setBusy(true); setNotice("");
    try {
      await FirebaseAuthentication.sendEmailVerification();
      setNotice("A new verification link has been sent. Check your inbox and spam folder.");
    } catch (error) { setNotice(messageFor(error)); }
    finally { setBusy(false); }
  }

  async function checkVerification() {
    setBusy(true); setNotice("");
    try {
      await FirebaseAuthentication.reload();
      const refreshed = (await FirebaseAuthentication.getCurrentUser()).user;
      setUser(refreshed || null);
      if (!refreshed?.emailVerified) setNotice("We haven't detected verification yet. Open the latest email link, then try again.");
    } catch (error) { setNotice(messageFor(error)); }
    finally { setBusy(false); }
  }

  async function signOut() {
    await FirebaseAuthentication.signOut();
    setUser(null); setMode("login"); setPassword(""); setNotice("");
  }

  if (checking) return <main className="auth-shell"><div className="auth-card"><div className="auth-brand-mark">VS</div><h1>VaaniSetu</h1><p>Checking your secure sign-in…</p></div></main>;

  if (user?.email && user.emailVerified) {
    const contactPhone = user.phoneNumber || savedPhone(user.uid);
    return <div className="app-auth-wrap"><div className="account-strip"><span className="account-avatar">{(user.displayName || user.email || "V").slice(0, 1).toUpperCase()}</span><span className="account-copy"><strong>{user.displayName || "VaaniSetu user"}</strong><small>{contactPhone || user.email}</small></span><button type="button" className="account-signout" onClick={signOut}>Sign out</button></div>{children}</div>;
  }

  if (!isNative) return <main className="auth-shell"><section className="auth-card"><div className="auth-brand-mark">VS</div><p className="auth-eyebrow">VOICE CONNECTS INDIA</p><h1>Welcome to VaaniSetu</h1><p>Email verification and secure sign-in are available in the Android app. Open the installed APK to create your account or sign in.</p></section></main>;

  if (user && !user.emailVerified) return <main className="auth-shell"><section className="auth-card"><div className="auth-brand-mark">VS</div><p className="auth-eyebrow">ONE MORE STEP</p><h1>Verify your email</h1><p className="auth-subtitle">We've sent a verification link to <strong>{user.email}</strong>. Open that email and tap the link. Then return to VaaniSetu.</p>{notice && <div className="auth-notice" role="status">{notice}</div>}<div className="auth-form"><button className="auth-primary" disabled={busy} onClick={checkVerification}>{busy ? "Checking…" : "I've verified my email"}</button><button type="button" className="auth-secondary" disabled={busy} onClick={resendVerification}>Resend verification email</button><button type="button" className="auth-secondary" onClick={signOut}>Sign out</button></div><p className="auth-footer">If you don't see the email, check your spam or promotions folder. Your mobile number is contact information and is not SMS-verified.</p></section></main>;

  return <main className="auth-shell"><section className="auth-card"><div className="auth-brand-mark">VS</div><p className="auth-eyebrow">VOICE CONNECTS INDIA</p><h1>{mode === "signup" ? "Create your account" : "Welcome back"}</h1><p className="auth-subtitle">Use your email to secure your VaaniSetu account. No SMS OTP is needed.</p><div className="auth-mode-switch"><button type="button" className={mode === "signup" ? "selected" : ""} onClick={() => { setMode("signup"); setNotice(""); }}>Create account</button><button type="button" className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setNotice(""); }}>Sign in</button></div>{mode === "signup" ? <form onSubmit={register} className="auth-form"><label>Full name<input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" /></label><label>Mobile number<input type="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91XXXXXXXXXX" /></label><label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@gmail.com" /></label><label>Create a password<input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" /></label><button className="auth-primary" disabled={busy}>{busy ? "Creating account…" : "Create account & send email link"}</button><p className="auth-legal">We'll email you a verification link. Your mobile number is saved as contact information; no SMS will be sent.</p></form> : <form onSubmit={signIn} className="auth-form"><label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@gmail.com" /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" /></label><button className="auth-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in with email"}</button></form>}{notice && <div className="auth-notice" role="status">{notice}</div>}<p className="auth-footer">By continuing, you agree to use VaaniSetu responsibly. Your account is protected by Firebase Authentication.</p></section></main>;
}

