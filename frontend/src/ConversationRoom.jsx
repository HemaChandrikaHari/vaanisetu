import { useEffect, useRef, useState } from "react";

const ICE_SERVERS = [{ urls: "stun:stun.l.google.com:19302" }];

function websocketUrl(apiBase, roomCode) {
  const url = new URL(apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/api/conversation/ws/${encodeURIComponent(roomCode)}`;
  url.search = "";
  return url.toString();
}

async function authHeaders() {
  const { token } = await FirebaseAuthentication.getIdToken({ forceRefresh: true });
  if (!token) throw new Error("Please sign in again.");
  return { Authorization: `Bearer ${token}` };
}

export default function ConversationRoom({ apiBase }) {
  const [roomCode, setRoomCode] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [status, setStatus] = useState("Not connected");
  const [role, setRole] = useState("");
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState("");
  const [micReady, setMicReady] = useState(false);
  const [consent, setConsent] = useState(false);
  const socketRef = useRef(null);
  const heartbeatRef = useRef(null);
  const peerRef = useRef(null);
  const localStreamRef = useRef(null);
  const remoteAudioRef = useRef(null);
  const pendingIceRef = useRef([]);

  useEffect(() => () => cleanup(false), []);

  function cleanup(sendHangup = true) {
    if (sendHangup && socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "hangup" }));
    }
    window.clearInterval(heartbeatRef.current);
    heartbeatRef.current = null;
    socketRef.current?.close();
    socketRef.current = null;
    peerRef.current?.close();
    peerRef.current = null;
    localStreamRef.current?.getTracks().forEach((track) => track.stop());
    localStreamRef.current = null;
    if (remoteAudioRef.current) remoteAudioRef.current.srcObject = null;
    pendingIceRef.current = [];
    setConnected(false);
    setMicReady(false);
    setRole("");
    setStatus("Not connected");
  }

  async function prepareMicrophone() {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Microphone access requires a supported browser and a secure HTTPS connection.");
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
    localStreamRef.current = stream;
    setMicReady(true);
    return stream;
  }

  async function sendSignal(type, payload) {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type, payload }));
    }
  }

  async function applyPendingIce() {
    const pc = peerRef.current;
    if (!pc?.remoteDescription) return;
    const pending = pendingIceRef.current.splice(0);
    for (const candidate of pending) {
      try { await pc.addIceCandidate(candidate); } catch { /* stale ICE candidate */ }
    }
  }

  async function createPeerConnection() {
    if (peerRef.current) return peerRef.current;
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    peerRef.current = pc;
    for (const track of localStreamRef.current?.getTracks() || []) {
      pc.addTrack(track, localStreamRef.current);
    }
    pc.ontrack = (event) => {
      const audio = remoteAudioRef.current;
      if (audio && event.streams?.[0]) {
        audio.srcObject = event.streams[0];
        audio.play().catch(() => setStatus("Tap Play on the audio control to hear the other participant."));
      }
    };
    pc.onicecandidate = (event) => {
      if (event.candidate) sendSignal("ice", event.candidate.toJSON());
    };
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === "connected") {
        setConnected(true);
        setStatus("Voice connection established");
      } else if (["failed", "disconnected"].includes(pc.connectionState)) {
        setConnected(false);
        setStatus("Connection interrupted. Try leaving and joining again.");
      } else if (pc.connectionState === "connecting") {
        setStatus("Connecting the two phones…");
      }
    };
    return pc;
  }

  async function handleSignal(message) {
    if (message.type === "peer_joined") {
      setStatus("Other participant joined. Connecting audio…");
      const pc = await createPeerConnection();
      if (pc.signalingState === "stable") {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        await sendSignal("offer", pc.localDescription);
      }
    } else if (message.type === "offer") {
      const pc = await createPeerConnection();
      await pc.setRemoteDescription(message.payload);
      await applyPendingIce();
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      await sendSignal("answer", pc.localDescription);
    } else if (message.type === "answer") {
      const pc = await createPeerConnection();
      await pc.setRemoteDescription(message.payload);
      await applyPendingIce();
    } else if (message.type === "ice") {
      const candidate = new RTCIceCandidate(message.payload);
      if (peerRef.current?.remoteDescription) {
        try { await peerRef.current.addIceCandidate(candidate); } catch { /* ignore stale candidate */ }
      } else {
        pendingIceRef.current.push(candidate);
      }
    } else if (message.type === "peer_left" || message.type === "hangup") {
      peerRef.current?.close();
      peerRef.current = null;
      setConnected(false);
      setStatus("The other participant left the room.");
    }
  }

  async function connectToRoom(code) {
    if (!consent) {
      setError("Please confirm that both people agree to this live voice connection.");
      return;
    }
    setBusy(true);
    setError("");
    cleanup(false);
    try {
      const normalized = code.trim().toUpperCase();
      if (!/^[A-HJ-NP-Z2-9]{8}$/.test(normalized)) throw new Error("Enter the 8-character room code.");
      const stream = await prepareMicrophone();
      const ticketResponse = await fetch(apiBase + "/api/conversation/rooms/" + encodeURIComponent(normalized) + "/ticket", {
        method: "POST",
        headers: await authHeaders(),
      });
      const ticketData = await ticketResponse.json().catch(() => ({}));
      if (!ticketResponse.ok || !ticketData.ticket) throw new Error(ticketData.detail || "Could not authorise entry to this room.");
      setRoomCode(normalized);
      setStatus("Authenticating and joining room…");
      const socket = new WebSocket(websocketUrl(apiBase, normalized));
      socketRef.current = socket;
      socket.onopen = () => {
        socket.send(JSON.stringify({ type: "auth", ticket: ticketData.ticket }));
        window.clearInterval(heartbeatRef.current);
        heartbeatRef.current = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "heartbeat" }));
        }, 25000);
      };
      socket.onmessage = async (event) => {
        let message;
        try { message = JSON.parse(event.data); } catch { return; }
        if (message.type === "joined") {
          setRole(message.role);
          setStatus(message.peer_present ? "Both phones joined. Negotiating audio…" : "Room ready. Waiting for the other phone…");
          if (message.peer_present && message.role === "A") {
            await createPeerConnection();
          }
        } else {
          try { await handleSignal(message); } catch (signalError) {
            setError(signalError.message || "Could not establish the voice connection.");
            setStatus("Connection failed");
          }
        }
      };
      socket.onerror = () => setError("Could not reach the signalling server. Confirm the backend is deployed with the latest version.");
      socket.onclose = () => {
        if (socketRef.current === socket) {
          window.clearInterval(heartbeatRef.current);
          setConnected(false);
          setStatus("Disconnected from the room.");
        }
      };
      setStatus("Connecting to room…");
    } catch (connectError) {
      localStreamRef.current?.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
      setMicReady(false);
      setError(connectError.message || "Could not join the room.");
      setStatus("Not connected");
    } finally {
      setBusy(false);
    }
  }

  async function createRoom() {
    setBusy(true);
    setError("");
    try {
      const headers = await authHeaders();
      const response = await fetch(`${apiBase}/api/conversation/rooms`, { method: "POST", headers });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Could not create a room.");
      await connectToRoom(data.room_code);
    } catch (createError) {
      setError(createError.message || "Could not create a room.");
      setBusy(false);
    }
  }

  function leaveRoom() {
    cleanup(true);
    setRoomCode("");
    setJoinCode("");
    setStatus("You left the conversation.");
  }

  function toggleMute() {
    const track = localStreamRef.current?.getAudioTracks()?.[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setMuted(!track.enabled);
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(roomCode);
      setStatus("Room code copied. Share it privately with the other person.");
    } catch {
      setStatus("Share this room code privately with the other person.");
    }
  }

  return <section className="hero conversation-hero">
    <p className="eyebrow">PRIVATE TWO-PHONE VOICE ROOM</p>
    <h1>Talk together.<br /><span>Stay connected.</span></h1>
    <p className="intro">Create a room on one phone and join it from the other. Microphone audio travels directly between devices using encrypted WebRTC. The server only helps the phones find each other.</p>
    <section className="recorder-card">
      <div className="recorder-heading"><div><span className="field-label">LIVE VOICE CONNECTION</span><h2>Two-phone conversation</h2></div><span className={connected ? "mode-label live" : "mode-label"}>{connected ? "CONNECTED" : "₹0 PROTOTYPE"}</span></div>
      {!roomCode && <div className="room-actions">
        <label className="room-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>I have told the other person that live microphone audio will be shared directly with their device, and they agree to participate.</span></label>
        <button className="record-button" type="button" disabled={busy || !consent} onClick={createRoom}>{busy ? "Creating room…" : "Create a room"}</button>
        <div className="room-divider"><span>OR JOIN</span></div>
        <label className="select-label" htmlFor="join-room-code">Enter the other person's room code</label>
        <input id="join-room-code" className="phone-input room-code-input" autoCapitalize="characters" maxLength={8} placeholder="8-character code" value={joinCode} onChange={(event) => setJoinCode(event.target.value.toUpperCase().replace(/[^A-HJ-NP-Z2-9]/g, ""))} />
        <button className="swap-button" type="button" disabled={busy || !consent || joinCode.length !== 8} onClick={() => connectToRoom(joinCode)}>Join room</button>
      </div>}
      {roomCode && <div className="room-live">
        <span className="field-label">ROOM CODE · SHARE PRIVATELY</span>
        <div className="room-code">{roomCode}<button className="swap-button" type="button" onClick={copyCode}>Copy</button></div>
        <div className="call-status-panel"><span className={connected ? "status-dot connected" : "status-dot"} /><div><strong>{status}</strong><p>{role ? `You joined as participant ${role}.` : "Preparing your microphone and secure connection."} {micReady ? "Microphone permission is active." : ""}</p></div></div>
        <audio ref={remoteAudioRef} className="remote-audio" autoPlay playsInline controls />
        <div className="voice-room-controls">
          <button className="swap-button" type="button" onClick={toggleMute} disabled={!micReady}>{muted ? "Unmute microphone" : "Mute microphone"}</button>
          <button className="record-button stop-button" type="button" onClick={leaveRoom}>Leave conversation</button>
        </div>
        <p className="call-footnote">This milestone carries the original voice, not translated voice. No audio is sent to VaaniSetu's server or saved by this app. Both people should agree before starting. Mobile networks and restrictive Wi-Fi may prevent a direct peer connection because this free build does not use a paid TURN relay.</p>
      </div>}
      {error && <div className="notice" role="alert"><span className="notice-icon">!</span><p>{error}</p></div>}
    </section>
  </section>;
}
