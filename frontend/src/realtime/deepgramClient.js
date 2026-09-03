/**
 * Direct-to-Deepgram audio plumbing. Nothing here talks to our backend —
 * it only ever uses the short-lived token from POST /voice/session. Business
 * logic, tool calls, and RAG all happen server-side over the separate
 * control-plane WebSocket (see useVoiceSession.js); this file is strictly
 * "microphone in, speech out".
 */

const STT_SAMPLE_RATE = 16000;
const TTS_SAMPLE_RATE = 24000;

/** Downsamples a Float32 audio buffer to 16-bit PCM at the target rate. */
function floatTo16BitPCM(float32Array, inputSampleRate, targetSampleRate) {
  const ratio = inputSampleRate / targetSampleRate;
  const outLength = Math.floor(float32Array.length / ratio);
  const out = new Int16Array(outLength);
  for (let i = 0; i < outLength; i++) {
    const srcIndex = Math.floor(i * ratio);
    const sample = Math.max(-1, Math.min(1, float32Array[srcIndex]));
    out[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return out;
}

/**
 * Captures the microphone and streams 16-bit PCM frames to a callback.
 * Returns a stop() function that releases the mic and audio graph.
 */
export async function startMicCapture(onPCMFrame) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);

  // ScriptProcessorNode is deprecated but universally supported and simple
  // for a bursty PCM-frame use case like this; an AudioWorklet would avoid
  // the deprecation but adds a build-time worklet file for marginal gain here.
  const bufferSize = 4096;
  const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    const pcm = floatTo16BitPCM(input, audioContext.sampleRate, STT_SAMPLE_RATE);
    onPCMFrame(pcm.buffer);
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  return function stop() {
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    audioContext.close();
  };
}

/**
 * Opens a Deepgram streaming STT connection. Deepgram's browser auth
 * convention is passing the token as a websocket subprotocol
 * (["token", <token>]) since browsers can't set custom auth headers on WS.
 */
export function connectSTT(streamConfig, token, { onPartial, onFinal, onSpeechStarted, onError }) {
  const url = new URL(streamConfig.url);
  Object.entries(streamConfig.params || {}).forEach(([key, value]) => url.searchParams.set(key, value));

  const socket = new WebSocket(url.toString(), ["token", token]);
  socket.binaryType = "arraybuffer";

  socket.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }

    if (message.type === "SpeechStarted") {
      onSpeechStarted?.();
      return;
    }

    if (message.type !== "Results") return;
    const transcript = message.channel?.alternatives?.[0]?.transcript || "";
    if (!transcript) return;

    if (message.is_final) {
      onFinal?.(transcript, Boolean(message.speech_final));
    } else {
      onPartial?.(transcript);
    }
  };

  socket.onerror = (event) => onError?.(event);

  return socket;
}

/** Opens a Deepgram streaming TTS connection and plays audio as it arrives. */
export function connectTTS(streamConfig, token, { onAudioStarted, onAudioCompleted, onError }) {
  const url = new URL(streamConfig.url);
  Object.entries(streamConfig.params || {}).forEach(([key, value]) => url.searchParams.set(key, value));

  const socket = new WebSocket(url.toString(), ["token", token]);
  socket.binaryType = "arraybuffer";

  const playback = new PCMPlaybackQueue(TTS_SAMPLE_RATE, onAudioStarted, onAudioCompleted);

  socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      const message = JSON.parse(event.data);
      if (message.type === "Flushed") playback.markUtteranceEnd();
      return;
    }
    playback.enqueue(event.data);
  };

  socket.onerror = (event) => onError?.(event);

  return { socket, playback };
}

/** Schedules incoming 16-bit PCM chunks for gapless, low-latency playback. */
class PCMPlaybackQueue {
  constructor(sampleRate, onStarted, onCompleted) {
    this.sampleRate = sampleRate;
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    this.nextStartTime = 0;
    this.activeSources = [];
    this.onStarted = onStarted;
    this.onCompleted = onCompleted;
    this.started = false;
  }

  enqueue(arrayBuffer) {
    const pcm16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 0x8000;

    const buffer = this.audioContext.createBuffer(1, float32.length, this.sampleRate);
    buffer.copyToChannel(float32, 0);

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);

    const now = this.audioContext.currentTime;
    const startAt = Math.max(now, this.nextStartTime);
    source.start(startAt);
    this.nextStartTime = startAt + buffer.duration;
    this.activeSources.push(source);

    if (!this.started) {
      this.started = true;
      this.onStarted?.();
    }

    source.onended = () => {
      this.activeSources = this.activeSources.filter((s) => s !== source);
    };
  }

  markUtteranceEnd() {
    const remaining = this.nextStartTime - this.audioContext.currentTime;
    const delay = Math.max(remaining, 0) * 1000;
    setTimeout(() => {
      if (this.activeSources.length === 0) this.onCompleted?.();
    }, delay + 50);
  }

  /** Barge-in: immediately stop whatever's currently playing/queued. */
  interrupt() {
    this.activeSources.forEach((source) => {
      try {
        source.onended = null;
        source.stop();
      } catch {
        // already stopped
      }
    });
    this.activeSources = [];
    this.nextStartTime = 0;
    this.started = false;
  }

  close() {
    this.interrupt();
    this.audioContext.close();
  }
}
