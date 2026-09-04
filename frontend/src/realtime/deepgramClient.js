
const STT_SAMPLE_RATE = 16000;
const TTS_SAMPLE_RATE = 24000;
const SOCKET_TIMEOUT_MS = 8000;
const MIC_RECOVERY_MAX_ATTEMPTS = 3;
const MIC_RECOVERY_DELAY_MS = 400;

function floatTo16BitPCM(input, inputSampleRate, targetSampleRate) {
  if (!input?.length) return new ArrayBuffer(0);

  if (inputSampleRate === targetSampleRate) {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const sample = Math.max(-1, Math.min(1, input[i]));
      output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return output.buffer;
  }

  const ratio = inputSampleRate / targetSampleRate;
  const outputLength = Math.floor(input.length / ratio);
  const output = new Int16Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const index = Math.min(Math.floor(i * ratio), input.length - 1);
    const sample = Math.max(-1, Math.min(1, input[index]));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output.buffer;
}

function createPCMWorkletUrl() {
  const code = `
    class PCMProcessor extends AudioWorkletProcessor {
      process(inputs) {
        const channel = inputs[0]?.[0];
        if (!channel) return true;
        const copy = new Float32Array(channel.length);
        copy.set(channel);
        this.port.postMessage(copy, [copy.buffer]);
        return true;
      }
    }
    registerProcessor("pcm-processor", PCMProcessor);
  `;
  return URL.createObjectURL(new Blob([code], { type: "application/javascript" }));
}

async function acquireMicStream() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone access is not supported in this browser.");
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  const track = stream.getAudioTracks()[0];
  if (!track || track.readyState !== "live") {
    stream.getTracks().forEach((t) => t.stop());
    throw new Error("Microphone track is not available.");
  }
  return { stream, track };
}

/**
 * Captures microphone audio via an AudioWorklet and streams 16-bit PCM
 * frames to `onPCMFrame`. If the mic track dies mid-call (device sleep,
 * Bluetooth renegotiation, another app grabbing the device) this
 * automatically tries to reacquire it rather than silently going dark —
 * `callbacks.onRecovering/onRecovered/onFatalError` report progress.
 */
export async function startMicCapture(onPCMFrame, callbacks = {}) {
  const { onRecovering, onRecovered, onFatalError } = callbacks;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) throw new Error("Web Audio API is not supported in this browser.");

  let { stream, track } = await acquireMicStream();
  const audioContext = new AudioContextClass();
  if (audioContext.state !== "running") await audioContext.resume();

  const workletUrl = createPCMWorkletUrl();
  try {
    await audioContext.audioWorklet.addModule(workletUrl);
  } finally {
    URL.revokeObjectURL(workletUrl);
  }

  const processor = new AudioWorkletNode(audioContext, "pcm-processor", {
    numberOfInputs: 1,
    numberOfOutputs: 1,
    channelCount: 1,
  });
  // Route through a silent gain node rather than leaving the worklet
  // unconnected — some browsers throttle/stop processing nodes with no
  // path to the destination.
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;
  processor.connect(silentGain);
  silentGain.connect(audioContext.destination);

  processor.port.onmessage = (event) => {
    const input = event.data;
    if (!input?.length) return;
    const pcm = floatTo16BitPCM(input, audioContext.sampleRate, STT_SAMPLE_RATE);
    if (pcm.byteLength) onPCMFrame(pcm);
  };

  let stopped = false;
  let recovering = false;
  let source = null;

  const connectSource = (mediaStream) => {
    try {
      source?.disconnect();
    } catch {
      /* already disconnected */
    }
    source = audioContext.createMediaStreamSource(mediaStream);
    source.connect(processor);
  };

  const attachTrackLifecycle = (mediaTrack) => {
    mediaTrack.onended = () => handleTrackLoss();
  };

  const handleTrackLoss = async () => {
    if (stopped || recovering) return;
    recovering = true;
    onRecovering?.();

    for (let attempt = 1; attempt <= MIC_RECOVERY_MAX_ATTEMPTS; attempt++) {
      if (stopped) return;
      try {
        await new Promise((resolve) => setTimeout(resolve, MIC_RECOVERY_DELAY_MS));
        if (audioContext.state !== "running") await audioContext.resume();

        const next = await acquireMicStream();
        try {
          stream.getTracks().forEach((t) => t.stop());
        } catch {
          /* already stopped */
        }
        stream = next.stream;
        track = next.track;
        connectSource(stream);
        attachTrackLifecycle(track);

        recovering = false;
        onRecovered?.();
        return;
      } catch (err) {
        console.warn(`[Voice] Mic recovery attempt ${attempt}/${MIC_RECOVERY_MAX_ATTEMPTS} failed`, err);
      }
    }

    recovering = false;
    onFatalError?.(new Error("Microphone could not be reconnected after multiple attempts."));
  };

  audioContext.onstatechange = () => {
    if (!stopped && audioContext.state === "suspended") audioContext.resume().catch(() => {});
  };

  connectSource(stream);
  attachTrackLifecycle(track);

  return async function stop() {
    if (stopped) return;
    stopped = true;
    processor.port.onmessage = null;
    try {
      source?.disconnect();
    } catch {
      /* noop */
    }
    try {
      processor.disconnect();
      silentGain.disconnect();
    } catch {
      /* noop */
    }
    stream.getTracks().forEach((t) => t.stop());
    if (audioContext.state !== "closed") {
      try {
        await audioContext.close();
      } catch {
        /* noop */
      }
    }
  };
}

/** Resolves when a socket opens; rejects immediately on error/close, or on timeout. */
export function waitForSocketOpen(socket, label = "WebSocket", timeoutMs = SOCKET_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    if (!socket) return reject(new Error(`${label} was not created`));
    if (socket.readyState === WebSocket.OPEN) return resolve();
    if (socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
      return reject(new Error(`${label} is already closed`));
    }

    let settled = false;
    const finish = (fn, arg) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.removeEventListener("open", handleOpen);
      socket.removeEventListener("error", handleError);
      socket.removeEventListener("close", handleClose);
      fn(arg);
    };
    const handleOpen = () => finish(resolve);
    const handleError = () => finish(reject, new Error(`${label} failed while connecting`));
    const handleClose = (event) =>
      finish(reject, new Error(`${label} closed before opening (code=${event.code})`));

    socket.addEventListener("open", handleOpen);
    socket.addEventListener("error", handleError);
    socket.addEventListener("close", handleClose);
    const timer = setTimeout(() => finish(reject, new Error(`${label} timed out connecting`)), timeoutMs);
  });
}

/** Opens a Deepgram streaming STT connection. */
export function connectSTT(streamConfig, token, { onPartial, onFinal, onSpeechStarted, onError, onOpen } = {}) {
  const url = new URL(streamConfig.url);
  Object.entries(streamConfig.params || {}).forEach(([key, value]) => url.searchParams.set(key, value));

  const socket = new WebSocket(url.toString(), ["bearer", token]);
  socket.binaryType = "arraybuffer";

  let opened = false;
  let intentionallyClosed = false;

  socket.onopen = () => {
    opened = true;
    onOpen?.();
  };

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

  const reportFailure = (event) => {
    if (intentionallyClosed) return;
    console.error("[Voice STT] connection error", { code: event?.code, reason: event?.reason, opened });
    onError?.(event, opened);
  };
  socket.onerror = reportFailure;
  socket.onclose = (event) => {
    if (!intentionallyClosed && (!opened || (event.code !== 1000 && event.code !== 1005))) {
      reportFailure(event);
    }
  };

  socket.closeForCleanup = () => {
    intentionallyClosed = true;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close(1000, "Client cleanup");
    }
  };

  return socket;
}

/** Opens a Deepgram streaming TTS connection and plays audio as it arrives. */
export function connectTTS(streamConfig, token, { onAudioStarted, onAudioCompleted, onError, onOpen } = {}) {
  const url = new URL(streamConfig.url);
  Object.entries(streamConfig.params || {}).forEach(([key, value]) => url.searchParams.set(key, value));

  const socket = new WebSocket(url.toString(), ["bearer", token]);
  socket.binaryType = "arraybuffer";
  const playback = new PCMPlaybackQueue(TTS_SAMPLE_RATE, onAudioStarted, onAudioCompleted);

  let opened = false;
  let intentionallyClosed = false;

  socket.onopen = () => {
    opened = true;
    onOpen?.();
  };

  socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "Flushed") playback.markUtteranceEnd();
      } catch {
        /* ignore malformed control frame */
      }
      return;
    }
    playback.enqueue(event.data);
  };

  const reportFailure = (event) => {
    if (intentionallyClosed) return;
    console.error("[Voice TTS] connection error", { code: event?.code, reason: event?.reason, opened });
    onError?.(event, opened);
  };
  socket.onerror = reportFailure;
  socket.onclose = (event) => {
    if (!intentionallyClosed && (!opened || (event.code !== 1000 && event.code !== 1005))) {
      reportFailure(event);
    }
  };

  socket.closeForCleanup = () => {
    intentionallyClosed = true;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close(1000, "Client cleanup");
    }
  };

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
    if (!arrayBuffer?.byteLength) return;

    const pcm16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 0x8000;

    const buffer = this.audioContext.createBuffer(1, float32.length, this.sampleRate);
    buffer.copyToChannel(float32, 0);

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);

    const startAt = Math.max(this.audioContext.currentTime, this.nextStartTime);
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
    setTimeout(() => {
      if (!this.activeSources.length) this.onCompleted?.();
    }, Math.max(remaining, 0) * 1000 + 50);
  }

  /** Barge-in: immediately stop whatever's currently playing/queued. */
  interrupt() {
    this.activeSources.forEach((source) => {
      try {
        source.onended = null;
        source.stop();
      } catch {
        /* already stopped */
      }
    });
    this.activeSources = [];
    this.nextStartTime = 0;
    this.started = false;
  }

  async close() {
    this.interrupt();
    if (this.audioContext.state !== "closed") {
      try {
        await this.audioContext.close();
      } catch {
        /* noop */
      }
    }
  }
}