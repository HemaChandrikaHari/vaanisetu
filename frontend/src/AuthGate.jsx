import { useEffect, useState } from "react";
import { FirebaseAuthentication } from "@capacitor-firebase/authentication";
import { Capacitor } from "@capacitor/core";

const isNative = Capacitor.isNativePlatform();

function messageFor(error) {
  const code = error?.code || "";
  if (code.includes("invalid-phone-number")) return "Enter a valid phone number with country code, for example +91XXXXXXXXXX.";
  if (code.includes("too-many-requests")) return "Too many attempts. Please wait before requesting another code.";
  if (code.includes("invalid-verification-code")) return "That OTP is incorrect. Please check it and try again.";
  if (code.includes("credential-already-in-use") || code.includes("email-already-in-use")) return "That email is already linked to another VaaniSetu account. Sign in with the account it belongs to.";
  if (code.includes("provider-already-linked")) return "This account already has an email linked.";
  return error?.message || "Authentication could not be completed. Please try again.";
}

export default function AuthGate({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState("signup");
  const [step, setStep] = useState("details");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("+91");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [verificationId, setVerificationId] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!isNative) { setChecking(false); return undefined; }
    let active = true;
    let authListener;
    FirebaseAuthentication.getCurrentUser()
      .then(({ user: current }) => { if (active) { setUser(current || null); if (current && !current.email) { setMode("signup"); setStep("profile"); } } })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setChecking(false); });
    FirebaseAuthentication.addListener("authStateChange", (event) => {
      if (active) { setUser(event.user || null); if (event.user && !event.user.email) { setMode("signup"); setStep("profile"); } }
    }).then((listener) => { authListener = listener; }).catch(() => {});
    return () => { active = false; authListener?.remove(); };
  }, []);

  async function sendCode(event) {
    event.preventDefault();
    setNotice("");
    if (!/^\+[1-9]\d{7,14}$/.test(phone.trim())) {
      setNotice("Enter your number with country code, e.g. +91XXXXXXXXXX."); return;
    }
    if (mode === "signup" && (!name.trim() || !/^\S+@\S+\.\S+$/.test(email.trim()) || password.length < 8)) {
      setNotice("Enter your name, a valid email and a password of at least 8 characters."); return;
    }
    setBusy(true);
    try {
      await FirebaseAuthentication.setLanguageCode({ languageCode: "en" });
      const codeListener = await FirebaseAuthentication.addListener("phoneCodeSent", (event) => {
        setVerificationId(event.verificationId);
        setStep("otp");
        setNotice("Verification code sent. Check your SMS messages.");
        setBusy(false);
      });
      const completeListener = await FirebaseAuthentication.addListener("phoneVerificationCompleted", (event) => {
        setUser(event.result.user); if (!event.result.user?.email) setMode("signup"); setStep("profile"); setBusy(false);
      });
      const failedListener = await FirebaseAuthentication.addListener("phoneVerificationFailed", (event) => {
        setNotice(messageFor(event)); setBusy(false);
      });
      await FirebaseAuthentication.signInWithPhoneNumber({ phoneNumber: phone.trim() });
      window.setTimeout(() => { codeListener.remove(); completeListener.remove(); failedListener.remove(); }, 180000);
    } catch (error) { setNotice(messageFor(error)); setBusy(false); }
  }

  async function verifyCode(event) {
    event.preventDefault();
    if (!verificationId || !/^\d{6}$/.test(otp.trim())) { setNotice("Enter the 6-digit code sent to your phone."); return; }
    setBusy(true); setNotice("");
    try {
      const result = await FirebaseAuthentication.confirmVerificationCode({ verificationId, verificationCode: otp.trim() });
      setUser(result.user); if (!result.user?.email) setMode("signup"); setStep("profile");
    } catch (error) { setNotice(messageFor(error)); }
    finally { setBusy(false); }
  }

  async function finishProfile(event) {
    event.preventDefault(); setBusy(true); setNotice("");
    try {
      const current = (await FirebaseAuthentication.getCurrentUser()).user;
      if (!current) throw new Error("Your phone verification session expired. Please sign in again.");
      if (mode === "signup") {
        if (!current.email) {
          await FirebaseAuthentication.linkWithEmailAndPassword({ email: email.trim().toLowerCase(), password });
        }
        await FirebaseAuthentication.updateProfile({ displayName: name.trim() });
        await FirebaseAuthentication.sendEmailVerification();
        setNotice("Account created. A verification link has been sent to your email.");
      } else if (!current.email) {
        setNotice("This phone number is verified, but no email is linked to this account. Please use Create account to add one.");
      }
      const refreshed = (await FirebaseAuthentication.getCurrentUser()).user;
      setUser(refreshed || current);
    } catch (error) { setNotice(messageFor(error)); setBusy(false); return; }
    setBusy(false);
  }

  async function signOut() {
    await FirebaseAuthentication.signOut();
    setUser(null); setMode("login"); setStep("details"); setOtp(""); setPassword(""); setNotice("");
  }

  if (checking) return <main className="auth-shell"><div className="auth-card"><div className="auth-brand-mark">వ</div><h1>VaaniSetu</h1><p>Checking your secure sign-in…</p></div></main>;

  if (user?.email) return (
    <div className="app-auth-wrap">
      <div className="account-strip">
        <span className="account-avatar">{(user.displayName || user.phoneNumber || "V").slice(0, 1).toUpperCase()}</span>
        <span className="account-copy"><strong>{user.displayName || "VaaniSetu user"}</strong><small>{user.phoneNumber || user.email || "Signed in"}</small></span>
        <button type="button" className="account-signout" onClick={signOut}>Sign out</button>
      </div>
      {children}
    </div>
  );

  if (!isNative) return <main className="auth-shell"><section className="auth-card"><div className="auth-brand-mark">వ</div><p className="auth-eyebrow">VOICE CONNECTS INDIA</p><h1>Welcome to VaaniSetu</h1><p>Secure phone-number sign-in is available in the Android app. Open the installed APK to create your account or sign in.</p></section></main>;

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-brand-mark">వ</div>
        <p className="auth-eyebrow">VOICE CONNECTS INDIA</p>
        <h1>{step === "otp" ? "Verify your number" : step === "profile" ? "Finish your account" : mode === "signup" ? "Create your account" : "Welcome back"}</h1>
        <p className="auth-subtitle">{step === "otp" ? "Enter the code sent to " + phone + "." : step === "profile" ? "Your phone number is verified. Complete your VaaniSetu profile." : "One account for your language preferences and translated calls."}</p>
        {step === "details" && <form onSubmit={sendCode} className="auth-form">
          <div className="auth-mode-switch"><button type="button" className={mode === "signup" ? "selected" : ""} onClick={() => { setMode("signup"); setNotice(""); }}>Create account</button><button type="button" className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setNotice(""); }}>Sign in</button></div>
          {mode === "signup" && <><label>Full name<input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" /></label><label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" /></label></>}
          <label>Mobile number<input type="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91XXXXXXXXXX" /></label>
          <button className="auth-primary" disabled={busy}>{busy ? "Sending code…" : "Send verification code"}</button>
          <p className="auth-legal">We'll send an SMS verification code. Standard SMS charges may apply.</p>
        </form>}
        {step === "otp" && <form onSubmit={verifyCode} className="auth-form"><label>6-digit verification code<input inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" /></label><button className="auth-primary" disabled={busy}>{busy ? "Verifying…" : "Verify phone number"}</button><button type="button" className="auth-secondary" onClick={() => { setStep("details"); setOtp(""); setNotice(""); }}>Change phone number</button></form>}
        {step === "profile" && <form onSubmit={finishProfile} className="auth-form"><label>Full name<input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" /></label><label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label><label>Create a password<input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" /></label><button className="auth-primary" disabled={busy}>{busy ? "Saving profile…" : "Finish registration"}</button><p className="auth-legal">Your phone number is verified. We'll link your email to this same account and send an email verification link.</p></form>}
        {notice && <div className="auth-notice" role="status">{notice}</div>}
        <p className="auth-footer">By continuing, you agree to use VaaniSetu responsibly. Your account is protected by Firebase Authentication.</p>
      </section>
    </main>
  );
}
