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
    const index = Math.min(
      Math.floor(i * ratio),
      input.length - 1,
    );
    const sample = Math.max(-1, Math.min(1, input[index]));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }

  return output.buffer;
}

function createPCMWorklet() {
  const code = `
    class PCMProcessor extends AudioWorkletProcessor {
      process(inputs) {
        const input = inputs[0];
        if (!input || !input[0]) return true;

        const channel = input[0];
        const copy = new Float32Array(channel.length);
        copy.set(channel);

        this.port.postMessage(copy, [copy.buffer]);
        return true;
      }
    }

    registerProcessor("pcm-processor", PCMProcessor);
  `;

  return URL.createObjectURL(
    new Blob([code], { type: "application/javascript" }),
  );
}

async function acquireMicStream() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone access is not supported.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const track = stream.getAudioTracks()[0];

  if (!track || track.readyState !== "live") {
    stream.getTracks().forEach((item) => item.stop());
    throw new Error("Microphone track is not available.");
  }

  return { stream, track };
}

/**
 * Captures microphone audio and streams 16-bit PCM frames via onPCMFrame.
 *
 * If the underlying mic track dies mid-call (device sleep, Bluetooth
 * renegotiation, another app grabbing the device, etc.) this will
 * automatically try to reacquire the microphone and keep the call going
 * instead of silently going dark. Callbacks:
 *   - onRecovering(): a track loss was detected, attempting to reconnect
 *   - onRecovered(): a new track was successfully attached
 *   - onFatalError(err): recovery attempts were exhausted, mic is dead
 */
export async function startMicCapture(onPCMFrame, callbacks = {}) {
  const { onRecovering, onRecovered, onFatalError } = callbacks;

  if (!window.AudioContext && !window.webkitAudioContext) {
    throw new Error("Web Audio API is not supported.");
  }

  console.info("[Microphone] Requesting microphone...");

  let { stream, track } = await acquireMicStream();

  console.info("[Microphone] Track READY", {
    label: track.label,
    state: track.readyState,
    muted: track.muted,
  });

  const AudioContextClass =
    window.AudioContext || window.webkitAudioContext;

  const audioContext = new AudioContextClass();

  console.info("[Microphone] AudioContext", {
    state: audioContext.state,
    sampleRate: audioContext.sampleRate,
  });

  if (audioContext.state !== "running") {
    await audioContext.resume();
  }

  const workletUrl = createPCMWorklet();

  try {
    await audioContext.audioWorklet.addModule(workletUrl);
  } finally {
    URL.revokeObjectURL(workletUrl);
  }

  const processor = new AudioWorkletNode(
    audioContext,
    "pcm-processor",
    {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      channelCount: 1,
    },
  );

  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;

  processor.port.onmessage = (event) => {
    const input = event.data;

    if (!input?.length) return;

    const pcm = floatTo16BitPCM(
      input,
      audioContext.sampleRate,
      STT_SAMPLE_RATE,
    );

    if (pcm.byteLength) {
      onPCMFrame(pcm);
    }
  };

  processor.connect(silentGain);
  silentGain.connect(audioContext.destination);

  let stopped = false;
  let recovering = false;
  let source = null;

  const connectSource = (mediaStream) => {
    if (source) {
      try {
        source.disconnect();
      } catch {}
    }

    source = audioContext.createMediaStreamSource(mediaStream);
    source.connect(processor);
  };

  const attachTrackLifecycle = (mediaTrack) => {
    mediaTrack.onended = () => {
      console.warn("[Microphone] Track ended");
      handleTrackLoss();
    };

    mediaTrack.onmute = () => {
      console.warn("[Microphone] Track muted");
    };

    mediaTrack.onunmute = () => {
      console.info("[Microphone] Track unmuted");
    };
  };

  const handleTrackLoss = async () => {
    if (stopped || recovering) return;

    recovering = true;
    onRecovering?.();

    for (
      let attempt = 1;
      attempt <= MIC_RECOVERY_MAX_ATTEMPTS;
      attempt++
    ) {
      if (stopped) return;

      console.warn(
        `[Microphone] Attempting recovery (${attempt}/${MIC_RECOVERY_MAX_ATTEMPTS})`,
      );

      try {
        await new Promise((resolve) =>
          setTimeout(resolve, MIC_RECOVERY_DELAY_MS),
        );

        if (audioContext.state !== "running") {
          await audioContext.resume();
        }

        const next = await acquireMicStream();

        try {
          stream.getTracks().forEach((item) => item.stop());
        } catch {}

        stream = next.stream;
        track = next.track;

        connectSource(stream);
        attachTrackLifecycle(track);

        console.info("[Microphone] Recovered", {
          label: track.label,
        });

        recovering = false;
        onRecovered?.();
        return;
      } catch (err) {
        console.error("[Microphone] Recovery attempt failed", err);
      }
    }

    recovering = false;
    onFatalError?.(
      new Error(
        "Microphone could not be reconnected after multiple attempts.",
      ),
    );
  };

  audioContext.onstatechange = () => {
    console.info("[Microphone] AudioContext state changed", {
      state: audioContext.state,
    });

    if (
      !stopped &&
      audioContext.state === "suspended"
    ) {
      audioContext.resume().catch(() => {});
    }
  };

  connectSource(stream);
  attachTrackLifecycle(track);

  console.info("[Microphone] AudioWorklet READY");

  return async function stop() {
    if (stopped) return;

    stopped = true;

    processor.port.onmessage = null;

    try {
      source?.disconnect();
    } catch {}

    try {
      processor.disconnect();
    } catch {}

    try {
      silentGain.disconnect();
    } catch {}

    stream.getTracks().forEach((item) => item.stop());

    if (audioContext.state !== "closed") {
      try {
        await audioContext.close();
      } catch {}
    }

    console.info("[Microphone] Stopped");
  };
}

export function waitForSocketOpen(
  socket,
  label = "WebSocket",
  timeoutMs = SOCKET_TIMEOUT_MS,
) {
  return new Promise((resolve, reject) => {
    if (!socket) {
      reject(new Error(`${label} was not created`));
      return;
    }

    if (socket.readyState === WebSocket.OPEN) {
      resolve();
      return;
    }

    if (
      socket.readyState === WebSocket.CLOSING ||
      socket.readyState === WebSocket.CLOSED
    ) {
      reject(new Error(`${label} is already closed`));
      return;
    }

    let settled = false;

    const cleanup = () => {
      clearTimeout(timer);
      socket.removeEventListener("open", handleOpen);
      socket.removeEventListener("error", handleError);
      socket.removeEventListener("close", handleClose);
    };

    const resolveOnce = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };

    const rejectOnce = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };

    const handleOpen = () => resolveOnce();

    const handleError = () =>
      rejectOnce(new Error(`${label} failed while connecting`));

    const handleClose = (event) =>
      rejectOnce(
        new Error(
          `${label} closed before opening (code=${event.code}, reason=${event.reason || "none"})`,
        ),
      );

    socket.addEventListener("open", handleOpen);
    socket.addEventListener("error", handleError);
    socket.addEventListener("close", handleClose);

    const timer = setTimeout(() => {
      rejectOnce(new Error(`${label} timed out connecting`));
    }, timeoutMs);
  });
}

export function connectSTT(
  streamConfig,
  token,
  {
    onPartial,
    onFinal,
    onSpeechStarted,
    onError,
    onOpen,
  } = {},
) {
  const url = new URL(streamConfig.url);

  Object.entries(streamConfig.params || {}).forEach(
    ([key, value]) => {
      url.searchParams.set(key, value);
    },
  );

  console.info("[Deepgram STT] Connecting", {
    url: url.toString(),
  });

  const socket = new WebSocket(
    url.toString(),
    ["bearer", token],
  );

  socket.binaryType = "arraybuffer";

  let opened = false;
  let intentionallyClosed = false;
  let errorReported = false;

  const reportError = (event) => {
    if (intentionallyClosed || errorReported) return;

    errorReported = true;

    console.error("[Deepgram STT] WebSocket error", {
      code: event?.code,
      reason: event?.reason,
      wasClean: event?.wasClean,
      opened,
    });

    onError?.(event, opened);
  };

  socket.onopen = () => {
    opened = true;

    console.info("[Deepgram STT] WebSocket OPEN");

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

    const transcript =
      message.channel?.alternatives?.[0]?.transcript || "";

    if (!transcript) return;

    if (message.is_final) {
      onFinal?.(
        transcript,
        Boolean(message.speech_final),
      );
    } else {
      onPartial?.(transcript);
    }
  };

  socket.onerror = (event) => {
    reportError(event);
  };

  socket.onclose = (event) => {
    console.warn("[Deepgram STT] WebSocket CLOSE", {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
      opened,
      intentionallyClosed,
    });

    if (intentionallyClosed) return;

    if (
      !opened ||
      (event.code !== 1000 && event.code !== 1005)
    ) {
      reportError(event);
    }
  };

  socket.closeForCleanup = () => {
    intentionallyClosed = true;

    if (
      socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING
    ) {
      socket.close(1000, "Client cleanup");
    }
  };

  return socket;
}

export function connectTTS(
  streamConfig,
  token,
  {
    onAudioStarted,
    onAudioCompleted,
    onError,
    onOpen,
  } = {},
) {
  const url = new URL(streamConfig.url);

  Object.entries(streamConfig.params || {}).forEach(
    ([key, value]) => {
      url.searchParams.set(key, value);
    },
  );

  console.info("[Deepgram TTS] Connecting");

  const socket = new WebSocket(
    url.toString(),
    ["bearer", token],
  );

  socket.binaryType = "arraybuffer";

  const playback = new PCMPlaybackQueue(
    TTS_SAMPLE_RATE,
    onAudioStarted,
    onAudioCompleted,
  );

  let opened = false;
  let intentionallyClosed = false;
  let errorReported = false;

  const reportError = (event) => {
    if (intentionallyClosed || errorReported) return;

    errorReported = true;

    console.error("[Deepgram TTS] WebSocket error", {
      code: event?.code,
      reason: event?.reason,
      wasClean: event?.wasClean,
      opened,
    });

    onError?.(event, opened);
  };

  socket.onopen = () => {
    opened = true;

    console.info("[Deepgram TTS] WebSocket OPEN");

    onOpen?.();
  };

  socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      try {
        const message = JSON.parse(event.data);

        if (message.type === "Flushed") {
          playback.markUtteranceEnd();
        }
      } catch {}

      return;
    }

    playback.enqueue(event.data);
  };

  socket.onerror = (event) => {
    reportError(event);
  };

  socket.onclose = (event) => {
    console.warn("[Deepgram TTS] WebSocket CLOSE", {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
      opened,
    });

    if (intentionallyClosed) return;

    if (
      !opened ||
      (event.code !== 1000 && event.code !== 1005)
    ) {
      reportError(event);
    }
  };

  socket.closeForCleanup = () => {
    intentionallyClosed = true;

    if (
      socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING
    ) {
      socket.close(1000, "Client cleanup");
    }
  };

  return {
    socket,
    playback,
  };
}

class PCMPlaybackQueue {
  constructor(
    sampleRate,
    onStarted,
    onCompleted,
  ) {
    this.sampleRate = sampleRate;
    this.audioContext = new (
      window.AudioContext ||
      window.webkitAudioContext
    )();
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

    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 0x8000;
    }

    const buffer =
      this.audioContext.createBuffer(
        1,
        float32.length,
        this.sampleRate,
      );

    buffer.copyToChannel(float32, 0);

    const source =
      this.audioContext.createBufferSource();

    source.buffer = buffer;
    source.connect(
      this.audioContext.destination,
    );

    const startAt = Math.max(
      this.audioContext.currentTime,
      this.nextStartTime,
    );

    source.start(startAt);

    this.nextStartTime =
      startAt + buffer.duration;

    this.activeSources.push(source);

    if (!this.started) {
      this.started = true;
      this.onStarted?.();
    }

    source.onended = () => {
      this.activeSources =
        this.activeSources.filter(
          (item) => item !== source,
        );
    };
  }

  markUtteranceEnd() {
    const remaining =
      this.nextStartTime -
      this.audioContext.currentTime;

    setTimeout(() => {
      if (!this.activeSources.length) {
        this.onCompleted?.();
      }
    }, Math.max(remaining, 0) * 1000 + 50);
  }

  interrupt() {
    this.activeSources.forEach((source) => {
      try {
        source.onended = null;
        source.stop();
      } catch {}
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
      } catch {}
    }
  }
}